"""Rate error detection rule for Celonis ML Workbench."""

from decimal import Decimal
from typing import Optional

import structlog

from ml_workbench.anomaly_detection.rules.base import (
    AnomalyRule,
    DetectedAnomaly,
    DetectionContext,
)

logger = structlog.get_logger(__name__)


class RateErrorDetectionRule(AnomalyRule):
    """Detect rate discrepancies between invoice and contract.

    Compares the invoice base rate against the contracted rate for
    the same service level, zone, and weight range.
    """

    name = "rate_error_detection"
    enabled = True

    # Minimum variance to flag (in dollars)
    MIN_VARIANCE = Decimal("0.01")

    # Charge types that represent base rates
    BASE_RATE_CHARGE_TYPES = ["freight", "base_rate", "transportation"]

    def detect(self, context: DetectionContext) -> Optional[DetectedAnomaly]:
        """Detect if the invoice rate differs from contract rate.

        Args:
            context: Detection context with line and contract data.

        Returns:
            DetectedAnomaly if rate error found, None otherwise.
        """
        line = context.line
        terms = context.contract_terms

        # Need service level to look up rate
        service_level = line.get("service_level")
        if not service_level:
            return None

        # Only check base rate charges
        charge_type = line.get("charge_type", "").lower()
        if charge_type not in self.BASE_RATE_CHARGE_TYPES:
            return None

        # Filter contract terms for matching rate
        if terms.empty:
            logger.debug("No contract terms available")
            return None

        # Filter for rate terms matching service level
        rate_terms = terms[
            (terms["term_type"] == "rate")
            & (terms["service_level"] == service_level)
        ]

        # Add zone filter if available
        zone = line.get("zone")
        if zone and "zone" in rate_terms.columns:
            zone_matched = rate_terms[rate_terms["zone"] == zone]
            if not zone_matched.empty:
                rate_terms = zone_matched

        # Add weight filter if available
        weight = line.get("billed_weight") or line.get("weight")
        if weight and "weight_min" in rate_terms.columns:
            weight_matched = rate_terms[
                (rate_terms["weight_min"] <= weight)
                & (rate_terms["weight_max"] >= weight)
            ]
            if not weight_matched.empty:
                rate_terms = weight_matched

        if rate_terms.empty:
            logger.debug(
                "No matching rate term found",
                service_level=service_level,
                zone=zone,
            )
            return None

        # Get best matching term
        term = rate_terms.iloc[0].to_dict()
        rate = term.get("rate")

        if not rate:
            return None

        rate = Decimal(str(rate))

        # Calculate expected amount
        expected_amount = rate
        rate_type = term.get("rate_type", "flat")

        # If rate is per pound and we have weight, multiply
        if rate_type == "per_lb" and weight:
            expected_amount = rate * Decimal(str(weight))

        # Get actual amount
        actual_amount = Decimal(str(line.get("amount", 0)))

        # Calculate variance
        variance = actual_amount - expected_amount

        # Check if variance exceeds threshold
        if abs(variance) < self.MIN_VARIANCE:
            return None

        # Determine confidence based on term confidence
        confidence = Decimal(str(term.get("confidence_score", 0.7)))

        # Adjust confidence if term was validated
        if term.get("validated"):
            confidence = min(Decimal("1.0"), confidence + Decimal("0.2"))

        description = (
            f"Invoice rate differs from contract. "
            f"Charged: ${actual_amount:.2f}, "
            f"Expected: ${expected_amount:.2f}, "
            f"Variance: ${variance:.2f}"
        )

        contract_number = term.get("contract_number", "Unknown")
        source_page = term.get("source_page", "?")

        evidence = (
            f"Invoice Line: {line.get('line_id')}\n"
            f"  - Service Level: {service_level}\n"
            f"  - Zone: {zone or 'N/A'}\n"
            f"  - Weight: {weight or 'N/A'} lbs\n"
            f"  - Charged Amount: ${actual_amount:.2f}\n"
            f"\n"
            f"Contract Term: {term.get('term_id')}\n"
            f"  - Contract: {contract_number}\n"
            f"  - Rate: ${rate:.4f} ({rate_type})\n"
            f"  - Source Page: {source_page}\n"
        )

        source_text = term.get("source_text")
        if source_text:
            evidence += f'\nContract Text:\n"{source_text[:500]}..."'

        logger.info(
            "Rate error detected",
            line_id=line.get("line_id"),
            charged=float(actual_amount),
            expected=float(expected_amount),
            variance=float(variance),
        )

        return DetectedAnomaly(
            anomaly_type="rate_error",
            expected_amount=expected_amount,
            actual_amount=actual_amount,
            variance=variance,
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
            contract_reference=f"{contract_number}, Page {source_page}",
            contract_term_id=term.get("term_id"),
        )
