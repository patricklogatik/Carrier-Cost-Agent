"""Unauthorized surcharge detection rule."""

from decimal import Decimal

from sqlalchemy import select

from src.core.logging import get_logger
from src.models.anomaly import AnomalyType
from src.models.contract import Contract, ContractTerm, ParsingStatus, TermType
from src.services.anomaly.detector import DetectedAnomaly, DetectionContext

logger = get_logger(__name__)


class UnauthorizedSurchargeRule:
    """Detect surcharges not defined in the active contract."""

    name = "unauthorized_surcharge_detection"
    enabled = True

    # Known surcharge types to check
    SURCHARGE_TYPES = [
        "fuel",
        "fuel_surcharge",
        "residential",
        "residential_delivery",
        "signature",
        "adult_signature",
        "direct_signature",
        "saturday",
        "saturday_delivery",
        "oversize",
        "additional_handling",
        "address_correction",
        "delivery_area",
        "extended_area",
        "peak",
        "peak_surcharge",
        "demand",
        "demand_surcharge",
    ]

    async def detect(self, context: DetectionContext) -> DetectedAnomaly | None:
        """Detect if a surcharge is not authorized by the contract.

        Checks if:
        1. The invoice line is a surcharge (not base rate)
        2. The surcharge type exists in the contract's surcharge terms

        Args:
            context: Detection context with line and shipment data.

        Returns:
            DetectedAnomaly if unauthorized surcharge found, None otherwise.
        """
        line = context.line
        db = context.db

        # Check if this is a surcharge
        charge_type_lower = (line.charge_type or "").lower().replace(" ", "_")

        is_surcharge = False
        for surcharge in self.SURCHARGE_TYPES:
            if surcharge in charge_type_lower:
                is_surcharge = True
                break

        # Also check description
        if not is_surcharge:
            desc_lower = (line.charge_description or "").lower()
            for surcharge in self.SURCHARGE_TYPES:
                if surcharge.replace("_", " ") in desc_lower:
                    is_surcharge = True
                    break

        if not is_surcharge:
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

        # Look for matching surcharge term
        surcharge_result = await db.execute(
            select(ContractTerm)
            .where(ContractTerm.contract_id == contract.contract_id)
            .where(ContractTerm.term_type == TermType.SURCHARGE)
        )
        surcharges = surcharge_result.scalars().all()

        # Check if this surcharge type is in contract
        surcharge_found = False
        matching_term = None

        for term in surcharges:
            term_type_lower = (term.service_level or "").lower().replace(" ", "_")
            if term_type_lower in charge_type_lower or charge_type_lower in term_type_lower:
                surcharge_found = True
                matching_term = term
                break

            # Check conditions
            if term.conditions:
                conditions_str = str(term.conditions).lower()
                if any(s in conditions_str for s in [charge_type_lower, line.charge_type]):
                    surcharge_found = True
                    matching_term = term
                    break

        if surcharge_found:
            # Surcharge is authorized - check if amount exceeds cap
            if matching_term and matching_term.rate:
                # Check if actual exceeds contracted cap
                if line.amount > matching_term.rate:
                    variance = line.amount - matching_term.rate
                    confidence = matching_term.confidence_score or Decimal("0.7")

                    description = (
                        f"Surcharge exceeds contracted cap. "
                        f"Charged: ${line.amount:.2f}, "
                        f"Cap: ${matching_term.rate:.2f}"
                    )

                    evidence = (
                        f"Invoice Line: {line.line_id}\n"
                        f"  - Charge Type: {line.charge_type}\n"
                        f"  - Amount: ${line.amount:.2f}\n"
                        f"\n"
                        f"Contract Term: {matching_term.term_id}\n"
                        f"  - Surcharge Cap: ${matching_term.rate:.2f}\n"
                        f"  - Source Page: {matching_term.source_page or 'N/A'}"
                    )

                    logger.info(
                        "Surcharge exceeds cap",
                        line_id=line.line_id,
                        charged=float(line.amount),
                        cap=float(matching_term.rate),
                    )

                    return DetectedAnomaly(
                        anomaly_type=AnomalyType.UNAUTHORIZED_SURCHARGE,
                        expected_amount=matching_term.rate,
                        actual_amount=line.amount,
                        variance=variance,
                        confidence_score=confidence,
                        detection_rule=self.name,
                        description=description,
                        evidence=evidence,
                        contract_reference=f"{contract.contract_number}, Page {matching_term.source_page or '?'}",
                        contract_term_id=matching_term.term_id,
                    )

            # Surcharge is valid and within limits
            return None

        # Surcharge not found in contract - unauthorized
        confidence = Decimal("0.75")

        description = (
            f"Surcharge '{line.charge_type}' not found in contract. "
            f"This surcharge may not be authorized."
        )

        # List authorized surcharges
        authorized_list = [
            term.service_level for term in surcharges if term.service_level
        ]

        evidence = (
            f"Invoice Line: {line.line_id}\n"
            f"  - Charge Type: {line.charge_type}\n"
            f"  - Description: {line.charge_description or 'N/A'}\n"
            f"  - Amount: ${line.amount:.2f}\n"
            f"\n"
            f"Contract: {contract.contract_number}\n"
            f"  - Authorized Surcharges: {', '.join(authorized_list) or 'None found'}\n"
            f"\n"
            f"The charged surcharge does not appear in the contract's "
            f"list of authorized surcharges."
        )

        logger.info(
            "Unauthorized surcharge detected",
            line_id=line.line_id,
            charge_type=line.charge_type,
            amount=float(line.amount),
        )

        return DetectedAnomaly(
            anomaly_type=AnomalyType.UNAUTHORIZED_SURCHARGE,
            expected_amount=Decimal("0"),  # Should not have been charged
            actual_amount=line.amount,
            variance=line.amount,
            confidence_score=confidence,
            detection_rule=self.name,
            description=description,
            evidence=evidence,
            contract_reference=contract.contract_number,
        )
