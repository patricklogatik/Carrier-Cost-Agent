"""Late delivery charge detection rule for Celonis ML Workbench."""

from decimal import Decimal
from typing import Optional

import structlog

from ml_workbench.anomaly_detection.rules.base import (
    AnomalyRule,
    DetectedAnomaly,
    DetectionContext,
)

logger = structlog.get_logger(__name__)


class LateDeliveryDetectionRule(AnomalyRule):
    """Detect late delivery charges applied to on-time shipments.

    Checks if:
    1. The invoice line contains a late delivery surcharge
    2. The shipment was actually delivered on time (actual <= expected)
    """

    name = "late_delivery_detection"
    enabled = True

    # Keywords that indicate late delivery charges
    LATE_CHARGE_KEYWORDS = [
        "late",
        "delay",
        "delayed",
        "service failure",
        "guarantee",
    ]

    def detect(self, context: DetectionContext) -> Optional[DetectedAnomaly]:
        """Detect if a late delivery charge was applied to an on-time shipment.

        Args:
            context: Detection context with line and shipment data.

        Returns:
            DetectedAnomaly if false late charge found, None otherwise.
        """
        line = context.line
        shipment = context.shipment

        # Check if this is a late delivery charge
        is_late_charge = False
        charge_type = (line.get("charge_type") or "").lower()
        charge_desc = (line.get("charge_description") or "").lower()

        for keyword in self.LATE_CHARGE_KEYWORDS:
            if keyword in charge_type or keyword in charge_desc:
                is_late_charge = True
                break

        if not is_late_charge:
            return None

        # Need shipment data to verify delivery timing
        if not shipment:
            logger.debug(
                "No shipment data for late charge verification",
                line_id=line.get("line_id"),
            )
            return None

        # Need both expected and actual delivery dates
        expected_delivery = shipment.get("expected_delivery")
        actual_delivery = shipment.get("actual_delivery")

        if not expected_delivery or not actual_delivery:
            logger.debug(
                "Missing delivery dates",
                line_id=line.get("line_id"),
                expected=expected_delivery,
                actual=actual_delivery,
            )
            return None

        # Check if delivery was on time
        was_on_time = actual_delivery <= expected_delivery

        if not was_on_time:
            # Shipment was actually late, charge may be valid
            return None

        # Shipment was on time but late fee was charged
        confidence = Decimal("0.95")  # High confidence when delivery dates are verified
        amount = Decimal(str(line.get("amount", 0)))

        description = (
            f"Late delivery charge applied but shipment was delivered on time. "
            f"Expected: {expected_delivery}, Actual: {actual_delivery}"
        )

        # Calculate days early
        days_early = (expected_delivery - actual_delivery).days if hasattr(
            expected_delivery - actual_delivery, "days"
        ) else 0

        evidence = (
            f"Invoice Line: {line.get('line_id')}\n"
            f"  - Charge Type: {line.get('charge_type')}\n"
            f"  - Description: {line.get('charge_description') or 'N/A'}\n"
            f"  - Amount: ${amount:.2f}\n"
            f"\n"
            f"Shipment: {shipment.get('shipment_id')}\n"
            f"  - PRO: {shipment.get('pro_number') or 'N/A'}\n"
            f"  - Tracking: {shipment.get('tracking_number') or 'N/A'}\n"
            f"  - Service Level: {shipment.get('service_level') or 'N/A'}\n"
            f"  - Expected Delivery: {expected_delivery}\n"
            f"  - Actual Delivery: {actual_delivery}\n"
            f"  - Days Early: {days_early}"
        )

        logger.info(
            "False late delivery charge detected",
            line_id=line.get("line_id"),
            expected=str(expected_delivery),
            actual=str(actual_delivery),
            amount=float(amount),
        )

        return DetectedAnomaly(
            anomaly_type="late_delivery",
            expected_amount=Decimal("0"),
            actual_amount=amount,
            variance=amount,
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
        )
