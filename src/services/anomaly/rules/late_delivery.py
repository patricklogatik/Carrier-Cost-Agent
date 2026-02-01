"""Late delivery charge detection rule."""

from decimal import Decimal

from src.core.logging import get_logger
from src.models.anomaly import AnomalyType
from src.services.anomaly.detector import DetectedAnomaly, DetectionContext

logger = get_logger(__name__)


class LateDeliveryDetectionRule:
    """Detect late delivery charges applied to on-time shipments."""

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

    async def detect(self, context: DetectionContext) -> DetectedAnomaly | None:
        """Detect if a late delivery charge was applied to an on-time shipment.

        Checks if:
        1. The invoice line contains a late delivery surcharge
        2. The shipment was actually delivered on time (actual <= expected)

        Args:
            context: Detection context with line and shipment data.

        Returns:
            DetectedAnomaly if false late charge found, None otherwise.
        """
        line = context.line
        shipment = line.shipment

        # Check if this is a late delivery charge
        is_late_charge = False
        charge_lower = (line.charge_type or "").lower()
        desc_lower = (line.charge_description or "").lower()

        for keyword in self.LATE_CHARGE_KEYWORDS:
            if keyword in charge_lower or keyword in desc_lower:
                is_late_charge = True
                break

        if not is_late_charge:
            return None

        # Need shipment data to verify delivery timing
        if not shipment:
            logger.debug("No shipment data for late charge verification", line_id=line.line_id)
            return None

        # Need both expected and actual delivery dates
        if not shipment.expected_delivery or not shipment.actual_delivery:
            logger.debug(
                "Missing delivery dates",
                line_id=line.line_id,
                expected=shipment.expected_delivery,
                actual=shipment.actual_delivery,
            )
            return None

        # Check if delivery was on time
        was_on_time = shipment.actual_delivery <= shipment.expected_delivery

        if not was_on_time:
            # Shipment was actually late, charge may be valid
            return None

        # Shipment was on time but late fee was charged
        confidence = Decimal("0.95")  # High confidence when delivery dates are verified

        description = (
            f"Late delivery charge applied but shipment was delivered on time. "
            f"Expected: {shipment.expected_delivery}, "
            f"Actual: {shipment.actual_delivery}"
        )

        evidence = (
            f"Invoice Line: {line.line_id}\n"
            f"  - Charge Type: {line.charge_type}\n"
            f"  - Description: {line.charge_description or 'N/A'}\n"
            f"  - Amount: ${line.amount:.2f}\n"
            f"\n"
            f"Shipment: {shipment.shipment_id}\n"
            f"  - PRO: {shipment.pro_number or 'N/A'}\n"
            f"  - Tracking: {shipment.tracking_number or 'N/A'}\n"
            f"  - Service Level: {shipment.service_level or 'N/A'}\n"
            f"  - Expected Delivery: {shipment.expected_delivery}\n"
            f"  - Actual Delivery: {shipment.actual_delivery}\n"
            f"  - Days Early: {(shipment.expected_delivery - shipment.actual_delivery).days}"
        )

        logger.info(
            "False late delivery charge detected",
            line_id=line.line_id,
            expected=str(shipment.expected_delivery),
            actual=str(shipment.actual_delivery),
            amount=float(line.amount),
        )

        return DetectedAnomaly(
            anomaly_type=AnomalyType.LATE_DELIVERY,
            expected_amount=Decimal("0"),  # Should not have been charged
            actual_amount=line.amount,
            variance=line.amount,  # Full amount is the variance
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
        )
