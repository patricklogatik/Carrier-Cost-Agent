"""Anomaly Detection Engine for Celonis ML Workbench.

This module provides the main anomaly detection service that runs
detection rules against invoice data stored in Celonis Data Pool.
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import structlog

from config.celonis_config import get_data_pool, get_table
from ml_workbench.anomaly_detection.rules.base import (
    AnomalyRule,
    DetectedAnomaly,
    DetectionContext,
)
from ml_workbench.anomaly_detection.rules.duplicate import DuplicateDetectionRule
from ml_workbench.anomaly_detection.rules.late_delivery import LateDeliveryDetectionRule
from ml_workbench.anomaly_detection.rules.rate_error import RateErrorDetectionRule
from ml_workbench.anomaly_detection.rules.unauthorized_surcharge import (
    UnauthorizedSurchargeRule,
)

logger = structlog.get_logger(__name__)


@dataclass
class AnomalyDetector:
    """Run anomaly detection rules against invoice data.

    Uses Celonis Data Pool for data access and stores results back
    to the anomaly table.

    Attributes:
        data_pool: Celonis Data Pool connection.
        rules: List of registered detection rules.
        confidence_threshold: Minimum confidence to record anomaly.
    """

    data_pool: Any = None
    rules: List[AnomalyRule] = field(default_factory=list)
    confidence_threshold: Decimal = Decimal("0.5")

    def __post_init__(self):
        """Initialize with default rules if none provided."""
        if not self.rules:
            self.register_default_rules()

    def register_default_rules(self):
        """Register the standard anomaly detection rules."""
        self.rules = [
            DuplicateDetectionRule(),
            RateErrorDetectionRule(),
            LateDeliveryDetectionRule(),
            UnauthorizedSurchargeRule(),
        ]
        logger.info(
            "Registered default rules",
            rules=[r.name for r in self.rules],
        )

    def register_rule(self, rule: AnomalyRule):
        """Register an additional detection rule.

        Args:
            rule: AnomalyRule instance to register.
        """
        self.rules.append(rule)
        logger.info("Registered rule", rule=rule.name)

    def detect_anomalies(self, invoice_id: str) -> List[DetectedAnomaly]:
        """Run all enabled rules against an invoice.

        Fetches invoice data from Celonis Data Pool and runs each
        registered rule against each line item.

        Args:
            invoice_id: UUID of the invoice to analyze.

        Returns:
            List of detected anomalies.
        """
        logger.info("Starting anomaly detection", invoice_id=invoice_id)

        # Fetch invoice data
        invoice = self._fetch_invoice(invoice_id)
        if invoice is None:
            logger.warning("Invoice not found", invoice_id=invoice_id)
            return []

        # Fetch invoice lines
        lines = self._fetch_invoice_lines(invoice_id)
        if lines.empty:
            logger.warning("No invoice lines found", invoice_id=invoice_id)
            return []

        # Fetch historical lines for duplicate detection
        carrier_id = invoice.get("carrier_id")
        historical_lines = self._fetch_historical_lines(carrier_id)

        # Fetch contract terms
        contract_terms = self._fetch_contract_terms(carrier_id)

        # Run detection on each line
        anomalies = []
        for _, line_row in lines.iterrows():
            line = line_row.to_dict()

            # Fetch matched shipment if available
            shipment = None
            if line.get("shipment_id"):
                shipment = self._fetch_shipment(line["shipment_id"])

            # Build detection context
            context = DetectionContext(
                line=line,
                invoice=invoice,
                shipment=shipment,
                contract_terms=contract_terms,
                carrier_id=carrier_id,
                historical_lines=historical_lines,
            )

            # Run each rule
            for rule in self.rules:
                if not rule.enabled:
                    continue

                try:
                    anomaly = rule.detect(context)
                    if anomaly and anomaly.confidence_score >= self.confidence_threshold:
                        anomalies.append(anomaly)
                        logger.info(
                            "Anomaly detected",
                            rule=rule.name,
                            line_id=line.get("line_id"),
                            type=anomaly.anomaly_type,
                            confidence=float(anomaly.confidence_score),
                        )
                except Exception as e:
                    logger.error(
                        "Rule execution failed",
                        rule=rule.name,
                        line_id=line.get("line_id"),
                        error=str(e),
                    )

        logger.info(
            "Anomaly detection completed",
            invoice_id=invoice_id,
            anomalies_found=len(anomalies),
        )

        return anomalies

    def save_anomalies(
        self, anomalies: List[DetectedAnomaly], invoice_id: str
    ) -> List[str]:
        """Save detected anomalies to the Celonis Data Pool.

        Args:
            anomalies: List of detected anomalies.
            invoice_id: ID of the source invoice.

        Returns:
            List of created anomaly IDs.
        """
        if not anomalies:
            return []

        # Get invoice lines for mapping
        lines = self._fetch_invoice_lines(invoice_id)
        line_ids = lines["line_id"].tolist() if not lines.empty else []

        # Build anomaly records
        records = []
        created_ids = []

        for i, anomaly in enumerate(anomalies):
            anomaly_id = str(uuid4())
            created_ids.append(anomaly_id)

            # Get line_id (use index to match if not available)
            line_id = line_ids[i] if i < len(line_ids) else None

            records.append({
                "anomaly_id": anomaly_id,
                "line_id": line_id,
                "contract_term_id": anomaly.contract_term_id,
                "anomaly_type": anomaly.anomaly_type,
                "expected_amount": float(anomaly.expected_amount),
                "actual_amount": float(anomaly.actual_amount),
                "variance": float(anomaly.variance),
                "confidence_score": float(anomaly.confidence_score),
                "detection_rule": anomaly.detection_rule,
                "duplicate_of_line_id": anomaly.duplicate_of_line_id,
                "contract_reference": anomaly.contract_reference,
                "status": "detected",
                "created_at": datetime.now(),
            })

        # Save to Data Pool
        df = pd.DataFrame(records)
        anomaly_table = get_table("anomaly")
        anomaly_table.upsert(df, keys=["anomaly_id"])

        logger.info("Anomalies saved", count=len(records))
        return created_ids

    def _fetch_invoice(self, invoice_id: str) -> Optional[Dict[str, Any]]:
        """Fetch invoice from Data Pool."""
        table = get_table("invoice", self.data_pool)
        df = table.get_data_frame(filter=f"invoice_id = '{invoice_id}'")
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def _fetch_invoice_lines(self, invoice_id: str) -> pd.DataFrame:
        """Fetch invoice lines from Data Pool."""
        table = get_table("invoice_line", self.data_pool)
        return table.get_data_frame(filter=f"invoice_id = '{invoice_id}'")

    def _fetch_shipment(self, shipment_id: str) -> Optional[Dict[str, Any]]:
        """Fetch shipment from Data Pool."""
        table = get_table("shipment", self.data_pool)
        df = table.get_data_frame(filter=f"shipment_id = '{shipment_id}'")
        if df.empty:
            return None
        return df.iloc[0].to_dict()

    def _fetch_historical_lines(
        self, carrier_id: str, lookback_days: int = 90
    ) -> pd.DataFrame:
        """Fetch historical invoice lines for duplicate detection."""
        lookback_date = datetime.now() - timedelta(days=lookback_days)

        # Join invoice_line with invoice to filter by carrier and date
        table = get_table("invoice_line", self.data_pool)

        # Note: Actual PyCelonis filtering may vary based on table structure
        # This is a simplified example
        try:
            df = table.get_data_frame()
            # Filter would be applied in actual Celonis environment
            return df
        except Exception as e:
            logger.warning("Failed to fetch historical lines", error=str(e))
            return pd.DataFrame()

    def _fetch_contract_terms(self, carrier_id: str) -> pd.DataFrame:
        """Fetch active contract terms for the carrier."""
        try:
            # Fetch active contract
            contract_table = get_table("contract", self.data_pool)
            contracts = contract_table.get_data_frame(
                filter=f"carrier_id = '{carrier_id}' AND is_active = true"
            )

            if contracts.empty:
                return pd.DataFrame()

            # Get most recent contract
            contract_id = contracts.iloc[0]["contract_id"]

            # Fetch terms
            term_table = get_table("contract_term", self.data_pool)
            terms = term_table.get_data_frame(
                filter=f"contract_id = '{contract_id}'"
            )

            return terms
        except Exception as e:
            logger.warning("Failed to fetch contract terms", error=str(e))
            return pd.DataFrame()


# Export for convenience
__all__ = ["AnomalyDetector", "DetectedAnomaly", "DetectionContext"]
