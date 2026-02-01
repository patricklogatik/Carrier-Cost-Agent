"""Duplicate charge detection rule for Celonis ML Workbench."""

from datetime import datetime, timedelta
from decimal import Decimal
from typing import Optional

import pandas as pd
import structlog

from ml_workbench.anomaly_detection.rules.base import (
    AnomalyRule,
    DetectedAnomaly,
    DetectionContext,
)

logger = structlog.get_logger(__name__)


class DuplicateDetectionRule(AnomalyRule):
    """Detect duplicate charges across invoices.

    Checks for:
    1. Same PRO number billed multiple times
    2. Same tracking number with same charge type
    3. Same shipment_id with identical amount
    """

    name = "duplicate_detection"
    enabled = True

    # Look back window in days
    LOOKBACK_DAYS = 90

    def detect(self, context: DetectionContext) -> Optional[DetectedAnomaly]:
        """Detect if this line is a duplicate charge.

        Args:
            context: Detection context with line and historical data.

        Returns:
            DetectedAnomaly if duplicate found, None otherwise.
        """
        line = context.line
        historical = context.historical_lines

        if historical.empty:
            return None

        # Calculate lookback date
        lookback_date = datetime.now() - timedelta(days=self.LOOKBACK_DAYS)

        # Filter historical lines by date
        if "created_at" in historical.columns:
            historical = historical[
                pd.to_datetime(historical["created_at"]) >= lookback_date
            ]

        # Filter by carrier
        if "carrier_id" in historical.columns:
            historical = historical[historical["carrier_id"] == context.carrier_id]

        # Exclude current line
        line_id = line.get("line_id")
        historical = historical[historical["line_id"] != line_id]

        if historical.empty:
            return None

        # Check for duplicates
        duplicate = None
        match_details = []
        confidence = Decimal("0.7")

        # Check PRO number match
        pro_number = line.get("pro_number")
        if pro_number:
            pro_matches = historical[historical["pro_number"] == pro_number]
            if not pro_matches.empty:
                duplicate = pro_matches.iloc[0].to_dict()
                confidence = Decimal("0.95")
                match_details.append(f"PRO: {pro_number}")

        # Check tracking number + charge type match
        tracking = line.get("tracking_number")
        charge_type = line.get("charge_type")
        if tracking and not duplicate:
            tracking_matches = historical[
                (historical["tracking_number"] == tracking)
                & (historical["charge_type"] == charge_type)
            ]
            if not tracking_matches.empty:
                duplicate = tracking_matches.iloc[0].to_dict()
                confidence = max(confidence, Decimal("0.9"))
                match_details.append(f"Tracking: {tracking}")

        # Check shipment_id + amount match
        shipment_id = line.get("shipment_id")
        amount = line.get("amount")
        if shipment_id and not duplicate:
            shipment_matches = historical[
                (historical["shipment_id"] == shipment_id)
                & (historical["amount"] == amount)
                & (historical["charge_type"] == charge_type)
            ]
            if not shipment_matches.empty:
                duplicate = shipment_matches.iloc[0].to_dict()
                confidence = max(confidence, Decimal("0.85"))
                match_details.append("Same shipment and amount")

        if not duplicate:
            return None

        # Build description and evidence
        description = (
            f"Potential duplicate charge. "
            f"Original on invoice line {duplicate.get('line_id')}"
        )
        if match_details:
            description += f" (matched on: {', '.join(match_details)})"

        evidence = (
            f"Current line: {line_id}\n"
            f"  - Invoice: {context.invoice.get('invoice_number')}\n"
            f"  - Amount: ${amount}\n"
            f"  - Charge type: {charge_type}\n"
            f"\n"
            f"Potential duplicate: {duplicate.get('line_id')}\n"
            f"  - Invoice: {duplicate.get('invoice_id')}\n"
            f"  - Amount: ${duplicate.get('amount')}\n"
            f"  - Charge type: {duplicate.get('charge_type')}"
        )

        logger.info(
            "Duplicate detected",
            line_id=line_id,
            duplicate_of=duplicate.get("line_id"),
            confidence=float(confidence),
        )

        return DetectedAnomaly(
            anomaly_type="duplicate",
            expected_amount=Decimal("0"),
            actual_amount=Decimal(str(amount)) if amount else Decimal("0"),
            variance=Decimal(str(amount)) if amount else Decimal("0"),
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
            duplicate_of_line_id=duplicate.get("line_id"),
        )
