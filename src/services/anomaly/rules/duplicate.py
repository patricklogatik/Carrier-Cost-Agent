"""Duplicate charge detection rule."""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import and_, or_, select

from src.core.logging import get_logger
from src.models.anomaly import AnomalyType
from src.models.invoice import Invoice, InvoiceLine
from src.services.anomaly.detector import DetectedAnomaly, DetectionContext

logger = get_logger(__name__)


class DuplicateDetectionRule:
    """Detect duplicate charges across invoices."""

    name = "duplicate_detection"
    enabled = True

    # Look back window in days
    LOOKBACK_DAYS = 90

    async def detect(self, context: DetectionContext) -> DetectedAnomaly | None:
        """Detect if this line is a duplicate charge.

        Checks for:
        1. Same PRO number billed multiple times
        2. Same tracking number with same charge type
        3. Same shipment_id with identical amount

        Args:
            context: Detection context with line and shipment data.

        Returns:
            DetectedAnomaly if duplicate found, None otherwise.
        """
        line = context.line
        db = context.db

        # Calculate lookback date
        lookback_date = datetime.now(timezone.utc) - timedelta(days=self.LOOKBACK_DAYS)

        # Build query for potential duplicates
        query = (
            select(InvoiceLine)
            .join(Invoice, InvoiceLine.invoice_id == Invoice.invoice_id)
            .where(InvoiceLine.line_id != line.line_id)  # Exclude self
            .where(Invoice.created_at >= lookback_date)
            .where(Invoice.carrier_id == context.carrier_id)
        )

        # Check based on identifiers
        conditions = []

        # Same PRO number
        if line.pro_number:
            conditions.append(InvoiceLine.pro_number == line.pro_number)

        # Same tracking number with same charge type
        if line.tracking_number:
            conditions.append(
                and_(
                    InvoiceLine.tracking_number == line.tracking_number,
                    InvoiceLine.charge_type == line.charge_type,
                )
            )

        # Same shipment with identical amount
        if line.shipment_id:
            conditions.append(
                and_(
                    InvoiceLine.shipment_id == line.shipment_id,
                    InvoiceLine.amount == line.amount,
                    InvoiceLine.charge_type == line.charge_type,
                )
            )

        if not conditions:
            return None

        query = query.where(or_(*conditions))
        result = await db.execute(query.limit(1))
        duplicate = result.scalar_one_or_none()

        if not duplicate:
            return None

        # Determine match type and confidence
        confidence = Decimal("0.7")
        match_details = []

        if line.pro_number and duplicate.pro_number == line.pro_number:
            confidence = Decimal("0.95")
            match_details.append(f"PRO: {line.pro_number}")

        if line.tracking_number and duplicate.tracking_number == line.tracking_number:
            if duplicate.charge_type == line.charge_type:
                confidence = max(confidence, Decimal("0.9"))
                match_details.append(f"Tracking: {line.tracking_number}")

        if line.shipment_id and duplicate.shipment_id == line.shipment_id:
            if duplicate.amount == line.amount:
                confidence = max(confidence, Decimal("0.85"))
                match_details.append("Same shipment and amount")

        description = f"Potential duplicate charge. Original on invoice line {duplicate.line_id}"
        if match_details:
            description += f" (matched on: {', '.join(match_details)})"

        evidence = (
            f"Current line: {line.line_id}\n"
            f"  - Invoice: {context.invoice.invoice_number}\n"
            f"  - Amount: ${line.amount}\n"
            f"  - Charge type: {line.charge_type}\n"
            f"\n"
            f"Potential duplicate: {duplicate.line_id}\n"
            f"  - Invoice: {duplicate.invoice_id}\n"
            f"  - Amount: ${duplicate.amount}\n"
            f"  - Charge type: {duplicate.charge_type}"
        )

        logger.info(
            "Duplicate detected",
            line_id=line.line_id,
            duplicate_of=duplicate.line_id,
            confidence=float(confidence),
        )

        return DetectedAnomaly(
            anomaly_type=AnomalyType.DUPLICATE,
            expected_amount=Decimal("0"),  # Duplicate should not be charged
            actual_amount=line.amount,
            variance=line.amount,  # Full amount is the variance
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
            duplicate_of_line_id=duplicate.line_id,
        )
