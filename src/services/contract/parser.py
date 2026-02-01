"""Contract parsing service using GenAI."""

from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any
from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.logging import get_logger
from src.models.contract import Contract, ContractTerm, ParsingStatus, TermType
from src.services.invoice.pdf_extractor import PDFExtractor

logger = get_logger(__name__)


@dataclass
class ExtractedTerm:
    """A term extracted from the contract."""

    term_type: TermType
    service_level: str | None = None
    zone: str | None = None
    weight_min: Decimal | None = None
    weight_max: Decimal | None = None
    rate: Decimal | None = None
    rate_type: str | None = None
    conditions: dict[str, Any] | None = None
    source_page: int | None = None
    source_text: str | None = None
    confidence_score: Decimal = Decimal("0.8")


@dataclass
class ParseResult:
    """Result of contract parsing."""

    terms: list[ExtractedTerm] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    success: bool = True


class ContractParser:
    """Parse carrier contracts using GenAI."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the parser.

        Args:
            db: Database session.
        """
        self.db = db
        self.pdf_extractor = PDFExtractor()

    async def parse_contract(self, contract_id: str, pdf_content: bytes) -> ParseResult:
        """Parse a contract PDF and extract terms.

        Args:
            contract_id: The contract ID to update.
            pdf_content: Raw PDF bytes.

        Returns:
            ParseResult with extracted terms.
        """
        # Get contract record
        result = await self.db.execute(
            select(Contract).where(Contract.contract_id == contract_id)
        )
        contract = result.scalar_one_or_none()

        if not contract:
            return ParseResult(success=False, errors=["Contract not found"])

        # Update status to processing
        contract.parsing_status = ParsingStatus.PROCESSING
        await self.db.commit()

        try:
            # Extract text from PDF
            extraction = self.pdf_extractor.extract(pdf_content)

            # Parse terms from extracted text
            # TODO: Replace with GenAI-powered parsing using Claude/GPT-4
            parse_result = await self._parse_with_rules(extraction.text, extraction.tables)

            # Save extracted terms
            for extracted in parse_result.terms:
                term = ContractTerm(
                    term_id=str(uuid4()),
                    contract_id=contract_id,
                    term_type=extracted.term_type,
                    service_level=extracted.service_level,
                    zone=extracted.zone,
                    weight_min=extracted.weight_min,
                    weight_max=extracted.weight_max,
                    rate=extracted.rate,
                    rate_type=extracted.rate_type,
                    conditions=extracted.conditions,
                    source_page=extracted.source_page,
                    source_text=extracted.source_text,
                    confidence_score=extracted.confidence_score,
                    validated=False,
                )
                self.db.add(term)

            # Update contract status
            contract.parsing_status = ParsingStatus.COMPLETED
            await self.db.commit()

            logger.info(
                "Contract parsing complete",
                contract_id=contract_id,
                terms_extracted=len(parse_result.terms),
            )

            return parse_result

        except Exception as e:
            logger.error(
                "Contract parsing failed",
                contract_id=contract_id,
                error=str(e),
            )
            contract.parsing_status = ParsingStatus.FAILED
            contract.parsing_error = str(e)
            await self.db.commit()

            return ParseResult(success=False, errors=[str(e)])

    async def _parse_with_rules(
        self, text: str, tables: list[list[list[str]]]
    ) -> ParseResult:
        """Parse contract using rule-based extraction.

        This is a placeholder for GenAI-powered parsing.

        Args:
            text: Extracted text from PDF.
            tables: Extracted tables from PDF.

        Returns:
            ParseResult with extracted terms.
        """
        terms: list[ExtractedTerm] = []

        # Extract rate tables
        for table in tables:
            extracted = self._parse_rate_table(table)
            terms.extend(extracted)

        # Extract surcharges from text
        surcharges = self._extract_surcharges(text)
        terms.extend(surcharges)

        # Extract SLA terms
        slas = self._extract_sla_terms(text)
        terms.extend(slas)

        return ParseResult(terms=terms)

    def _parse_rate_table(self, table: list[list[str]]) -> list[ExtractedTerm]:
        """Parse a rate table from the contract.

        Args:
            table: A table extracted from the PDF.

        Returns:
            List of extracted rate terms.
        """
        terms: list[ExtractedTerm] = []

        if not table or len(table) < 2:
            return terms

        # Try to identify header row
        header = [str(cell).lower().strip() for cell in table[0]]

        # Look for rate-related columns
        rate_keywords = ["rate", "price", "cost", "charge"]
        zone_keywords = ["zone", "zn"]
        weight_keywords = ["weight", "wt", "lbs"]
        service_keywords = ["service", "level", "type"]

        col_map: dict[str, int] = {}

        for i, col in enumerate(header):
            for keyword in rate_keywords:
                if keyword in col:
                    col_map["rate"] = i
                    break
            for keyword in zone_keywords:
                if keyword in col:
                    col_map["zone"] = i
                    break
            for keyword in weight_keywords:
                if keyword in col:
                    col_map["weight"] = i
                    break
            for keyword in service_keywords:
                if keyword in col:
                    col_map["service"] = i
                    break

        if "rate" not in col_map:
            return terms

        # Parse data rows
        for row in table[1:]:
            if len(row) <= max(col_map.values()):
                continue

            try:
                rate_str = row[col_map["rate"]].replace("$", "").replace(",", "").strip()
                if not rate_str:
                    continue

                rate = Decimal(rate_str)

                term = ExtractedTerm(
                    term_type=TermType.RATE,
                    rate=rate,
                    rate_type="flat",
                    confidence_score=Decimal("0.7"),
                )

                if "zone" in col_map:
                    term.zone = row[col_map["zone"]].strip() or None

                if "service" in col_map:
                    term.service_level = row[col_map["service"]].strip() or None

                if "weight" in col_map:
                    weight_str = row[col_map["weight"]].strip()
                    if "-" in weight_str:
                        parts = weight_str.split("-")
                        if len(parts) == 2:
                            term.weight_min = Decimal(parts[0].strip())
                            term.weight_max = Decimal(parts[1].strip().replace("+", ""))

                terms.append(term)

            except (ValueError, IndexError) as e:
                logger.debug("Could not parse rate row", error=str(e))
                continue

        return terms

    def _extract_surcharges(self, text: str) -> list[ExtractedTerm]:
        """Extract surcharge definitions from contract text.

        Args:
            text: Full contract text.

        Returns:
            List of extracted surcharge terms.
        """
        terms: list[ExtractedTerm] = []

        # Common surcharge patterns to look for
        surcharge_patterns = {
            "Fuel Surcharge": r"fuel\s+surcharge[:\s]+(\d+\.?\d*)[%]?",
            "Residential Delivery": r"residential\s+(?:delivery\s+)?(?:fee|surcharge)[:\s]+\$?(\d+\.?\d*)",
            "Signature Required": r"(?:signature|adult\s+signature)[:\s]+\$?(\d+\.?\d*)",
            "Saturday Delivery": r"saturday\s+(?:delivery\s+)?(?:fee|surcharge)[:\s]+\$?(\d+\.?\d*)",
            "Address Correction": r"address\s+correction[:\s]+\$?(\d+\.?\d*)",
        }

        import re

        text_lower = text.lower()

        for surcharge_name, pattern in surcharge_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                try:
                    rate = Decimal(match.group(1))

                    # Determine rate type
                    rate_type = "flat"
                    if "%" in match.group(0):
                        rate_type = "percentage"

                    # Find source text context
                    start = max(0, match.start() - 50)
                    end = min(len(text), match.end() + 50)
                    source_text = text[start:end].strip()

                    terms.append(ExtractedTerm(
                        term_type=TermType.SURCHARGE,
                        service_level=surcharge_name,
                        rate=rate,
                        rate_type=rate_type,
                        source_text=source_text,
                        confidence_score=Decimal("0.65"),
                    ))

                except ValueError:
                    continue

        return terms

    def _extract_sla_terms(self, text: str) -> list[ExtractedTerm]:
        """Extract SLA terms from contract text.

        Args:
            text: Full contract text.

        Returns:
            List of extracted SLA terms.
        """
        terms: list[ExtractedTerm] = []

        # Common service level patterns
        sla_patterns = {
            "Priority Overnight": r"priority\s+overnight.*?(\d+)\s*(?:business\s+)?day",
            "Standard Overnight": r"standard\s+overnight.*?(\d+)\s*(?:business\s+)?day",
            "2Day": r"2\s*day.*?(\d+)\s*(?:business\s+)?day",
            "Ground": r"fedex\s+ground.*?(\d+)-?(\d+)?\s*(?:business\s+)?day",
        }

        import re

        text_lower = text.lower()

        for service_name, pattern in sla_patterns.items():
            match = re.search(pattern, text_lower)
            if match:
                try:
                    days = int(match.group(1))

                    terms.append(ExtractedTerm(
                        term_type=TermType.SLA,
                        service_level=service_name,
                        conditions={
                            "delivery_days": days,
                            "guarantee": "service_guarantee",
                        },
                        source_text=text[match.start():match.end()],
                        confidence_score=Decimal("0.6"),
                    ))

                except ValueError:
                    continue

        return terms
