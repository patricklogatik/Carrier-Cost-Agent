"""Invoice-shipment matching service."""

from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.logging import get_logger
from src.models.invoice import InvoiceLine
from src.models.shipment import Shipment

logger = get_logger(__name__)


@dataclass
class MatchResult:
    """Result of matching an invoice line to a shipment."""

    line_id: str
    shipment_id: str | None
    match_type: str  # exact_pro, exact_tracking, fuzzy_reference, unmatched
    confidence: float
    match_details: str


class InvoiceShipmentMatcher:
    """Match invoice line items to shipment records."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the matcher.

        Args:
            db: Database session.
        """
        self.db = db

    async def match_invoice_lines(
        self, invoice_id: str, carrier_id: str
    ) -> list[MatchResult]:
        """Match all lines in an invoice to shipments.

        Args:
            invoice_id: The invoice to process.
            carrier_id: The carrier ID for shipment lookup.

        Returns:
            List of match results for each line.
        """
        # Get unmatched lines
        result = await self.db.execute(
            select(InvoiceLine)
            .where(InvoiceLine.invoice_id == invoice_id)
            .where(InvoiceLine.shipment_id == None)
        )
        lines = result.scalars().all()

        results: list[MatchResult] = []
        matched_count = 0

        for line in lines:
            match_result = await self._match_line(line, carrier_id)
            results.append(match_result)

            if match_result.shipment_id:
                # Update the line with matched shipment
                line.shipment_id = match_result.shipment_id
                matched_count += 1

        await self.db.commit()

        logger.info(
            "Invoice matching complete",
            invoice_id=invoice_id,
            total_lines=len(lines),
            matched=matched_count,
            unmatched=len(lines) - matched_count,
        )

        return results

    async def _match_line(
        self, line: InvoiceLine, carrier_id: str
    ) -> MatchResult:
        """Match a single invoice line to a shipment.

        Args:
            line: The invoice line to match.
            carrier_id: The carrier ID for shipment lookup.

        Returns:
            MatchResult with match details.
        """
        # Try exact match on PRO number
        if line.pro_number:
            shipment = await self._find_by_pro_number(line.pro_number, carrier_id)
            if shipment:
                return MatchResult(
                    line_id=line.line_id,
                    shipment_id=shipment.shipment_id,
                    match_type="exact_pro",
                    confidence=1.0,
                    match_details=f"Matched on PRO number: {line.pro_number}",
                )

        # Try exact match on tracking number
        if line.tracking_number:
            shipment = await self._find_by_tracking(line.tracking_number, carrier_id)
            if shipment:
                return MatchResult(
                    line_id=line.line_id,
                    shipment_id=shipment.shipment_id,
                    match_type="exact_tracking",
                    confidence=1.0,
                    match_details=f"Matched on tracking number: {line.tracking_number}",
                )

        # Try fuzzy match on reference number
        if line.reference_number:
            shipment = await self._find_by_reference(line.reference_number, carrier_id)
            if shipment:
                return MatchResult(
                    line_id=line.line_id,
                    shipment_id=shipment.shipment_id,
                    match_type="fuzzy_reference",
                    confidence=0.8,
                    match_details=f"Matched on reference: {line.reference_number}",
                )

        # Try composite match using multiple fields
        if line.origin_zip and line.destination_zip and line.ship_date:
            shipment = await self._find_by_composite(
                carrier_id=carrier_id,
                origin_zip=line.origin_zip,
                destination_zip=line.destination_zip,
                ship_date=line.ship_date,
                weight=line.weight,
            )
            if shipment:
                return MatchResult(
                    line_id=line.line_id,
                    shipment_id=shipment.shipment_id,
                    match_type="composite",
                    confidence=0.6,
                    match_details="Matched on origin/dest/date/weight",
                )

        # No match found
        return MatchResult(
            line_id=line.line_id,
            shipment_id=None,
            match_type="unmatched",
            confidence=0.0,
            match_details="No matching shipment found",
        )

    async def _find_by_pro_number(
        self, pro_number: str, carrier_id: str
    ) -> Shipment | None:
        """Find shipment by PRO number."""
        result = await self.db.execute(
            select(Shipment)
            .where(Shipment.carrier_id == carrier_id)
            .where(Shipment.pro_number == pro_number)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_by_tracking(
        self, tracking_number: str, carrier_id: str
    ) -> Shipment | None:
        """Find shipment by tracking number."""
        result = await self.db.execute(
            select(Shipment)
            .where(Shipment.carrier_id == carrier_id)
            .where(Shipment.tracking_number == tracking_number)
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_by_reference(
        self, reference: str, carrier_id: str
    ) -> Shipment | None:
        """Find shipment by reference number."""
        result = await self.db.execute(
            select(Shipment)
            .where(Shipment.carrier_id == carrier_id)
            .where(
                or_(
                    Shipment.reference_number == reference,
                    Shipment.order_number == reference,
                )
            )
            .limit(1)
        )
        return result.scalar_one_or_none()

    async def _find_by_composite(
        self,
        carrier_id: str,
        origin_zip: str,
        destination_zip: str,
        ship_date,
        weight: Decimal | None,
    ) -> Shipment | None:
        """Find shipment by composite fields."""
        query = (
            select(Shipment)
            .where(Shipment.carrier_id == carrier_id)
            .where(Shipment.origin_zip == origin_zip)
            .where(Shipment.destination_zip == destination_zip)
            .where(Shipment.ship_date == ship_date)
        )

        # Add weight tolerance if available
        if weight:
            tolerance = Decimal("0.5")  # 0.5 lb tolerance
            query = query.where(Shipment.weight >= weight - tolerance)
            query = query.where(Shipment.weight <= weight + tolerance)

        result = await self.db.execute(query.limit(1))
        return result.scalar_one_or_none()
