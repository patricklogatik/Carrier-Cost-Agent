"""Anomaly detection engine."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Protocol
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.logging import get_logger
from src.models.anomaly import Anomaly, AnomalyStatus, AnomalyType
from src.models.invoice import Invoice, InvoiceLine

logger = get_logger(__name__)


@dataclass
class DetectionContext:
    """Context for anomaly detection."""

    invoice: Invoice
    line: InvoiceLine
    carrier_id: str
    db: AsyncSession


@dataclass
class DetectedAnomaly:
    """A detected anomaly before persisting."""

    anomaly_type: AnomalyType
    expected_amount: Decimal | None
    actual_amount: Decimal
    variance: Decimal
    confidence_score: Decimal
    detection_rule: str
    description: str
    evidence: str | None = None
    contract_reference: str | None = None
    contract_term_id: str | None = None
    duplicate_of_line_id: str | None = None


class DetectionRule(Protocol):
    """Protocol for detection rules."""

    name: str
    enabled: bool

    async def detect(self, context: DetectionContext) -> DetectedAnomaly | None:
        """Run the detection rule.

        Args:
            context: Detection context with invoice, line, and shipment data.

        Returns:
            DetectedAnomaly if anomaly found, None otherwise.
        """
        ...


class AnomalyDetector:
    """Run anomaly detection rules against invoice line items."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the detector.

        Args:
            db: Database session.
        """
        self.db = db
        self.rules: list[DetectionRule] = []

    def register_rule(self, rule: DetectionRule) -> None:
        """Register a detection rule.

        Args:
            rule: The detection rule to register.
        """
        self.rules.append(rule)
        logger.info("Registered detection rule", rule=rule.name)

    async def detect_anomalies(self, invoice_id: str) -> list[Anomaly]:
        """Run all detection rules against an invoice.

        Args:
            invoice_id: The invoice to analyze.

        Returns:
            List of detected anomalies.
        """
        # Load invoice with lines
        result = await self.db.execute(
            select(Invoice)
            .options(
                selectinload(Invoice.lines).selectinload(InvoiceLine.shipment)
            )
            .where(Invoice.invoice_id == invoice_id)
        )
        invoice = result.scalar_one_or_none()

        if not invoice:
            logger.warning("Invoice not found for anomaly detection", invoice_id=invoice_id)
            return []

        anomalies: list[Anomaly] = []

        for line in invoice.lines:
            context = DetectionContext(
                invoice=invoice,
                line=line,
                carrier_id=invoice.carrier_id,
                db=self.db,
            )

            for rule in self.rules:
                if not rule.enabled:
                    continue

                try:
                    detected = await rule.detect(context)
                    if detected:
                        # Check if anomaly already exists
                        existing = await self._check_existing(
                            line.line_id,
                            detected.anomaly_type,
                            detected.detection_rule,
                        )
                        if not existing:
                            anomaly = self._create_anomaly(line.line_id, detected)
                            self.db.add(anomaly)
                            anomalies.append(anomaly)
                except Exception as e:
                    logger.error(
                        "Detection rule failed",
                        rule=rule.name,
                        line_id=line.line_id,
                        error=str(e),
                    )

        await self.db.commit()

        logger.info(
            "Anomaly detection complete",
            invoice_id=invoice_id,
            lines_processed=len(invoice.lines),
            anomalies_found=len(anomalies),
        )

        return anomalies

    async def _check_existing(
        self, line_id: str, anomaly_type: AnomalyType, detection_rule: str
    ) -> bool:
        """Check if anomaly already exists."""
        result = await self.db.execute(
            select(Anomaly)
            .where(Anomaly.line_id == line_id)
            .where(Anomaly.anomaly_type == anomaly_type)
            .where(Anomaly.detection_rule == detection_rule)
            .limit(1)
        )
        return result.scalar_one_or_none() is not None

    def _create_anomaly(self, line_id: str, detected: DetectedAnomaly) -> Anomaly:
        """Create an Anomaly from detected data."""
        return Anomaly(
            anomaly_id=str(uuid4()),
            line_id=line_id,
            anomaly_type=detected.anomaly_type,
            expected_amount=detected.expected_amount,
            actual_amount=detected.actual_amount,
            variance=detected.variance,
            confidence_score=detected.confidence_score,
            detection_rule=detected.detection_rule,
            status=AnomalyStatus.DETECTED,
            description=detected.description,
            evidence=detected.evidence,
            contract_reference=detected.contract_reference,
            contract_term_id=detected.contract_term_id,
            duplicate_of_line_id=detected.duplicate_of_line_id,
        )
