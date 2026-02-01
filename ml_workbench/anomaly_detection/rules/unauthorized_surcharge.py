"""Unauthorized surcharge detection rule for Celonis ML Workbench."""

from decimal import Decimal
from typing import Optional

import structlog

from ml_workbench.anomaly_detection.rules.base import (
    AnomalyRule,
    DetectedAnomaly,
    DetectionContext,
)

logger = structlog.get_logger(__name__)


class UnauthorizedSurchargeRule(AnomalyRule):
    """Detect surcharges that are not defined in the active contract.

    Checks if:
    1. The surcharge type exists in contract terms
    2. The surcharge amount doesn't exceed contracted cap
    """

    name = "unauthorized_surcharge_detection"
    enabled = True

    # Common surcharge types to check
    KNOWN_SURCHARGE_TYPES = [
        "fuel_surcharge",
        "fuel",
        "residential_delivery",
        "residential",
        "signature_required",
        "signature",
        "saturday_delivery",
        "saturday",
        "address_correction",
        "delivery_area_surcharge",
        "extended_area",
        "oversize",
        "additional_handling",
        "peak_surcharge",
        "demand_surcharge",
        "declared_value",
    ]

    def detect(self, context: DetectionContext) -> Optional[DetectedAnomaly]:
        """Detect if a surcharge is not authorized by the contract.

        Args:
            context: Detection context with line and contract data.

        Returns:
            DetectedAnomaly if unauthorized surcharge found, None otherwise.
        """
        line = context.line
        terms = context.contract_terms

        # Get charge type
        charge_type = line.get("charge_type", "").lower()

        # Skip non-surcharge items (base freight, etc.)
        if charge_type in ["freight", "base_rate", "transportation"]:
            return None

        # Normalize the charge type for matching
        normalized_type = self._normalize_surcharge_type(charge_type)
        if not normalized_type:
            return None

        # Filter contract terms for surcharge terms
        if terms.empty:
            # No contract terms available - flag as potentially unauthorized
            return self._create_no_contract_anomaly(line, charge_type)

        surcharge_terms = terms[terms["term_type"] == "surcharge"]

        if surcharge_terms.empty:
            # No surcharge terms in contract - flag as potentially unauthorized
            return self._create_no_contract_anomaly(line, charge_type)

        # Look for matching surcharge term
        matching_term = None
        for _, term in surcharge_terms.iterrows():
            term_type = self._normalize_surcharge_type(
                term.get("surcharge_type", "") or term.get("service_level", "")
            )
            if term_type == normalized_type:
                matching_term = term.to_dict()
                break

        if not matching_term:
            # Surcharge not found in contract
            return self._create_unauthorized_anomaly(line, charge_type)

        # Check if surcharge exceeds contracted cap
        amount = Decimal(str(line.get("amount", 0)))
        contracted_rate = matching_term.get("rate")

        if contracted_rate:
            contracted_rate = Decimal(str(contracted_rate))
            rate_type = matching_term.get("rate_type", "flat")

            # For percentage surcharges, we'd need the base rate to calculate
            # For now, just check flat caps
            if rate_type == "flat" and amount > contracted_rate:
                return self._create_overage_anomaly(
                    line, charge_type, amount, contracted_rate, matching_term
                )

        return None

    def _normalize_surcharge_type(self, charge_type: str) -> Optional[str]:
        """Normalize surcharge type for matching."""
        charge_lower = charge_type.lower().replace("_", " ").replace("-", " ")

        for known_type in self.KNOWN_SURCHARGE_TYPES:
            known_lower = known_type.lower().replace("_", " ")
            if known_lower in charge_lower or charge_lower in known_lower:
                return known_type

        return None

    def _create_no_contract_anomaly(
        self, line: dict, charge_type: str
    ) -> DetectedAnomaly:
        """Create anomaly when no contract terms are available."""
        amount = Decimal(str(line.get("amount", 0)))

        return DetectedAnomaly(
            anomaly_type="unauthorized_surcharge",
            expected_amount=Decimal("0"),
            actual_amount=amount,
            variance=amount,
            confidence_score=Decimal("0.6"),  # Lower confidence without contract
            detection_rule=self.name,
            description=f"Surcharge '{charge_type}' charged but no contract terms available for validation",
            evidence=f"Invoice Line: {line.get('line_id')}\n"
            f"  - Charge Type: {charge_type}\n"
            f"  - Amount: ${amount:.2f}\n\n"
            f"No contract surcharge terms available for validation.",
        )

    def _create_unauthorized_anomaly(
        self, line: dict, charge_type: str
    ) -> DetectedAnomaly:
        """Create anomaly for surcharge not in contract."""
        amount = Decimal(str(line.get("amount", 0)))

        logger.info(
            "Unauthorized surcharge detected",
            line_id=line.get("line_id"),
            charge_type=charge_type,
            amount=float(amount),
        )

        return DetectedAnomaly(
            anomaly_type="unauthorized_surcharge",
            expected_amount=Decimal("0"),
            actual_amount=amount,
            variance=amount,
            confidence_score=Decimal("0.75"),
            detection_rule=self.name,
            description=f"Surcharge '{charge_type}' is not defined in the active contract",
            evidence=f"Invoice Line: {line.get('line_id')}\n"
            f"  - Charge Type: {charge_type}\n"
            f"  - Description: {line.get('charge_description') or 'N/A'}\n"
            f"  - Amount: ${amount:.2f}\n\n"
            f"This surcharge type was not found in the contract surcharge terms.",
        )

    def _create_overage_anomaly(
        self,
        line: dict,
        charge_type: str,
        actual: Decimal,
        contracted: Decimal,
        term: dict,
    ) -> DetectedAnomaly:
        """Create anomaly for surcharge exceeding contracted cap."""
        variance = actual - contracted

        logger.info(
            "Surcharge overage detected",
            line_id=line.get("line_id"),
            charge_type=charge_type,
            actual=float(actual),
            contracted=float(contracted),
        )

        return DetectedAnomaly(
            anomaly_type="unauthorized_surcharge",
            expected_amount=contracted,
            actual_amount=actual,
            variance=variance,
            confidence_score=Decimal(str(term.get("confidence_score", 0.8))),
            detection_rule=self.name,
            description=f"Surcharge '{charge_type}' exceeds contracted cap. "
            f"Charged: ${actual:.2f}, Cap: ${contracted:.2f}",
            evidence=f"Invoice Line: {line.get('line_id')}\n"
            f"  - Charge Type: {charge_type}\n"
            f"  - Charged Amount: ${actual:.2f}\n\n"
            f"Contract Term: {term.get('term_id')}\n"
            f"  - Contracted Cap: ${contracted:.2f}\n"
            f"  - Source Page: {term.get('source_page') or 'N/A'}",
            contract_term_id=term.get("term_id"),
            contract_reference=f"Page {term.get('source_page') or '?'}",
        )
