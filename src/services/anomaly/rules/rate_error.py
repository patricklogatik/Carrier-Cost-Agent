"""Rate error detection rule."""

from decimal import Decimal

from sqlalchemy import select

from src.core.logging import get_logger
from src.models.anomaly import AnomalyType
from src.models.contract import Contract, ContractTerm, ParsingStatus, TermType
from src.services.anomaly.detector import DetectedAnomaly, DetectionContext

logger = get_logger(__name__)


class RateErrorDetectionRule:
    """Detect rate discrepancies between invoice and contract."""

    name = "rate_error_detection"
    enabled = True

    # Minimum variance to flag (in dollars)
    MIN_VARIANCE = Decimal("0.01")

    async def detect(self, context: DetectionContext) -> DetectedAnomaly | None:
        """Detect if the invoice rate differs from contract rate.

        Compares the invoice base rate against the contracted rate for
        the same service level, zone, and weight range.

        Args:
            context: Detection context with line and shipment data.

        Returns:
            DetectedAnomaly if rate error found, None otherwise.
        """
        line = context.line
        db = context.db

        # Need service level to look up rate
        if not line.service_level:
            return None

        # Only check base rate charges
        if line.charge_type not in ["freight", "base_rate", "transportation"]:
            return None

        # Get ship date for contract validity
        ship_date = line.ship_date
        if not ship_date and line.shipment:
            ship_date = line.shipment.ship_date

        if not ship_date:
            return None

        # Find active contract
        contract_result = await db.execute(
            select(Contract)
            .where(Contract.carrier_id == context.carrier_id)
            .where(Contract.is_active == True)
            .where(Contract.effective_date <= ship_date)
            .where(Contract.expiration_date >= ship_date)
            .where(Contract.parsing_status == ParsingStatus.COMPLETED)
            .order_by(Contract.version.desc())
            .limit(1)
        )
        contract = contract_result.scalar_one_or_none()

        if not contract:
            logger.debug("No active contract found", carrier_id=context.carrier_id)
            return None

        # Look up rate term
        term_query = (
            select(ContractTerm)
            .where(ContractTerm.contract_id == contract.contract_id)
            .where(ContractTerm.term_type == TermType.RATE)
            .where(ContractTerm.service_level == line.service_level)
        )

        # Add zone filter if available
        if line.zone:
            term_query = term_query.where(ContractTerm.zone == line.zone)

        # Add weight filter if available
        weight = line.billed_weight or line.weight
        if weight:
            term_query = term_query.where(ContractTerm.weight_min <= weight)
            term_query = term_query.where(ContractTerm.weight_max >= weight)

        term_result = await db.execute(term_query.limit(1))
        term = term_result.scalar_one_or_none()

        if not term or not term.rate:
            logger.debug(
                "No matching rate term found",
                service_level=line.service_level,
                zone=line.zone,
            )
            return None

        # Calculate expected amount
        expected_amount = term.rate

        # If rate is per pound and we have weight, multiply
        if term.rate_type == "per_lb" and weight:
            expected_amount = term.rate * weight

        # Calculate variance
        variance = line.amount - expected_amount

        # Check if variance exceeds threshold
        if abs(variance) < self.MIN_VARIANCE:
            return None

        # Determine confidence based on term confidence
        confidence = term.confidence_score or Decimal("0.7")

        # Adjust confidence if term was validated
        if term.validated:
            confidence = min(Decimal("1.0"), confidence + Decimal("0.2"))

        description = (
            f"Invoice rate differs from contract. "
            f"Charged: ${line.amount:.2f}, "
            f"Expected: ${expected_amount:.2f}, "
            f"Variance: ${variance:.2f}"
        )

        evidence = (
            f"Invoice Line: {line.line_id}\n"
            f"  - Service Level: {line.service_level}\n"
            f"  - Zone: {line.zone or 'N/A'}\n"
            f"  - Weight: {weight or 'N/A'} lbs\n"
            f"  - Charged Amount: ${line.amount:.2f}\n"
            f"\n"
            f"Contract Term: {term.term_id}\n"
            f"  - Contract: {contract.contract_number}\n"
            f"  - Rate: ${term.rate:.4f} ({term.rate_type or 'flat'})\n"
            f"  - Source Page: {term.source_page or 'N/A'}\n"
        )

        if term.source_text:
            evidence += f"\nContract Text:\n\"{term.source_text[:500]}...\""

        logger.info(
            "Rate error detected",
            line_id=line.line_id,
            charged=float(line.amount),
            expected=float(expected_amount),
            variance=float(variance),
        )

        return DetectedAnomaly(
            anomaly_type=AnomalyType.RATE_ERROR,
            expected_amount=expected_amount,
            actual_amount=line.amount,
            variance=variance,
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
            contract_reference=f"{contract.contract_number}, Page {term.source_page or '?'}",
            contract_term_id=term.term_id,
        )
