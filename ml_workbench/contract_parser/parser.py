"""Contract Parser using Celonis native LLM.

This module provides GenAI-powered extraction of contract terms
from carrier contract PDFs using Celonis' native LLM integration.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import pdfplumber
import structlog

# Note: pycelonis_llm is available in Celonis ML Workbench (Sept 2025 release)
# For local development, this import may need to be mocked
try:
    from pycelonis_llm import CelonisLLM
except ImportError:
    CelonisLLM = None  # Will use fallback parsing

from config.celonis_config import get_table
from config.settings import settings

logger = structlog.get_logger(__name__)


@dataclass
class ExtractedTerm:
    """Represents a single extracted contract term."""

    term_type: str  # rate, surcharge, discount, sla, exception
    service_level: Optional[str] = None
    zone: Optional[str] = None
    weight_min: Optional[float] = None
    weight_max: Optional[float] = None
    rate: Optional[float] = None
    rate_type: Optional[str] = None  # flat, per_lb, percentage
    surcharge_type: Optional[str] = None
    conditions: Optional[Dict[str, Any]] = None
    source_page: Optional[int] = None
    source_text: Optional[str] = None
    confidence_score: float = 0.8


class ContractParser:
    """Parse carrier contracts using Celonis native LLM.

    Extracts structured terms from contract PDFs including:
    - Rate tables
    - Surcharge definitions
    - SLA terms
    - Discount structures
    """

    def __init__(self, data_pool=None):
        """Initialize the contract parser.

        Args:
            data_pool: Optional Celonis Data Pool connection.
        """
        self.data_pool = data_pool

        # Initialize LLM if available
        self.llm = None
        if CelonisLLM:
            try:
                self.llm = CelonisLLM(
                    model=settings.llm_model_contract_parsing
                )
                logger.info("Initialized Celonis LLM for contract parsing")
            except Exception as e:
                logger.warning(f"Failed to initialize Celonis LLM: {e}")

    def parse_contract(
        self,
        pdf_path: str,
        contract_id: str,
        carrier_id: str,
    ) -> List[ExtractedTerm]:
        """Parse a contract PDF and extract structured terms.

        Args:
            pdf_path: Path to the contract PDF file.
            contract_id: ID of the contract record.
            carrier_id: ID of the carrier.

        Returns:
            List of extracted contract terms.
        """
        logger.info("Parsing contract", pdf_path=pdf_path, contract_id=contract_id)

        # Extract text from PDF
        pages_text = self._extract_pdf_text(pdf_path)

        if not pages_text:
            logger.warning("No text extracted from PDF")
            return []

        # Extract terms using GenAI
        all_terms = []

        for page_num, page_text in enumerate(pages_text, start=1):
            if self.llm:
                terms = self._extract_terms_with_llm(page_text, page_num)
            else:
                terms = self._extract_terms_with_rules(page_text, page_num)

            all_terms.extend(terms)

        logger.info(
            "Contract parsing complete",
            contract_id=contract_id,
            terms_extracted=len(all_terms),
        )

        return all_terms

    def save_terms(
        self,
        terms: List[ExtractedTerm],
        contract_id: str,
    ) -> List[str]:
        """Save extracted terms to Celonis Data Pool.

        Args:
            terms: List of extracted terms.
            contract_id: ID of the parent contract.

        Returns:
            List of created term IDs.
        """
        if not terms:
            return []

        records = []
        term_ids = []

        for term in terms:
            term_id = str(uuid4())
            term_ids.append(term_id)

            records.append({
                "term_id": term_id,
                "contract_id": contract_id,
                "term_type": term.term_type,
                "service_level": term.service_level,
                "zone": term.zone,
                "weight_min": term.weight_min,
                "weight_max": term.weight_max,
                "rate": term.rate,
                "rate_type": term.rate_type,
                "conditions": json.dumps(term.conditions) if term.conditions else None,
                "source_page": term.source_page,
                "source_text": term.source_text,
                "confidence_score": term.confidence_score,
                "validated": False,
                "created_at": datetime.now(),
            })

        # Save to Data Pool
        df = pd.DataFrame(records)
        term_table = get_table("contract_term", self.data_pool)
        term_table.upsert(df, keys=["term_id"])

        logger.info("Saved contract terms", count=len(records))
        return term_ids

    def _extract_pdf_text(self, pdf_path: str) -> List[str]:
        """Extract text from each page of a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            List of text strings, one per page.
        """
        pages = []

        try:
            with pdfplumber.open(pdf_path) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ""
                    pages.append(text)

                    # Also try to extract tables
                    tables = page.extract_tables()
                    for table in tables:
                        table_text = self._table_to_text(table)
                        pages[-1] += "\n\n" + table_text

        except Exception as e:
            logger.error("Failed to extract PDF text", error=str(e))

        return pages

    def _table_to_text(self, table: List[List[str]]) -> str:
        """Convert a table to text format.

        Args:
            table: Table data as list of rows.

        Returns:
            Text representation of the table.
        """
        if not table:
            return ""

        lines = []
        for row in table:
            if row:
                cells = [str(cell) if cell else "" for cell in row]
                lines.append(" | ".join(cells))

        return "\n".join(lines)

    def _extract_terms_with_llm(
        self, page_text: str, page_num: int
    ) -> List[ExtractedTerm]:
        """Extract terms using Celonis LLM.

        Args:
            page_text: Text content of the page.
            page_num: Page number for reference.

        Returns:
            List of extracted terms.
        """
        if not page_text.strip():
            return []

        prompt = self._build_extraction_prompt(page_text)

        try:
            response = self.llm.generate(prompt)
            terms = self._parse_llm_response(response, page_num)
            return terms
        except Exception as e:
            logger.warning(
                "LLM extraction failed, falling back to rules",
                page=page_num,
                error=str(e),
            )
            return self._extract_terms_with_rules(page_text, page_num)

    def _build_extraction_prompt(self, text: str) -> str:
        """Build the extraction prompt for the LLM.

        Args:
            text: Page text to analyze.

        Returns:
            Formatted prompt string.
        """
        return f"""Analyze this carrier contract page and extract structured pricing terms.

Extract the following types of information if present:

1. RATE TABLES - Shipping rates by service level, zone, and weight
   Format: service_level, zone, weight_min, weight_max, rate, rate_type (flat/per_lb)

2. SURCHARGE DEFINITIONS - Additional fees and their conditions
   Format: surcharge_type, rate, rate_type (flat/percentage), conditions

3. SLA TERMS - Delivery timeframes and guarantees
   Format: service_level, delivery_days, guarantee_type

4. DISCOUNT STRUCTURES - Volume discounts or special pricing
   Format: discount_type, threshold, discount_rate

Return the extracted data as JSON with this structure:
{{
  "rate_tables": [
    {{"service_level": "...", "zone": "...", "weight_min": ..., "weight_max": ..., "rate": ..., "rate_type": "..."}}
  ],
  "surcharges": [
    {{"surcharge_type": "...", "rate": ..., "rate_type": "...", "conditions": "..."}}
  ],
  "sla_terms": [
    {{"service_level": "...", "delivery_days": ..., "guarantee": "..."}}
  ],
  "discounts": [
    {{"discount_type": "...", "threshold": ..., "discount_rate": ...}}
  ]
}}

Contract text:
{text[:8000]}

Return ONLY the JSON, no other text."""

    def _parse_llm_response(
        self, response: str, page_num: int
    ) -> List[ExtractedTerm]:
        """Parse the LLM response into ExtractedTerm objects.

        Args:
            response: LLM response text.
            page_num: Page number for reference.

        Returns:
            List of extracted terms.
        """
        terms = []

        try:
            # Clean and parse JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            # Parse rate tables
            for rate in data.get("rate_tables", []):
                terms.append(ExtractedTerm(
                    term_type="rate",
                    service_level=rate.get("service_level"),
                    zone=rate.get("zone"),
                    weight_min=rate.get("weight_min"),
                    weight_max=rate.get("weight_max"),
                    rate=rate.get("rate"),
                    rate_type=rate.get("rate_type", "flat"),
                    source_page=page_num,
                    confidence_score=0.85,
                ))

            # Parse surcharges
            for surcharge in data.get("surcharges", []):
                terms.append(ExtractedTerm(
                    term_type="surcharge",
                    surcharge_type=surcharge.get("surcharge_type"),
                    rate=surcharge.get("rate"),
                    rate_type=surcharge.get("rate_type", "flat"),
                    conditions={"description": surcharge.get("conditions")},
                    source_page=page_num,
                    confidence_score=0.8,
                ))

            # Parse SLA terms
            for sla in data.get("sla_terms", []):
                terms.append(ExtractedTerm(
                    term_type="sla",
                    service_level=sla.get("service_level"),
                    conditions={
                        "delivery_days": sla.get("delivery_days"),
                        "guarantee": sla.get("guarantee"),
                    },
                    source_page=page_num,
                    confidence_score=0.9,
                ))

            # Parse discounts
            for discount in data.get("discounts", []):
                terms.append(ExtractedTerm(
                    term_type="discount",
                    conditions={
                        "discount_type": discount.get("discount_type"),
                        "threshold": discount.get("threshold"),
                        "discount_rate": discount.get("discount_rate"),
                    },
                    source_page=page_num,
                    confidence_score=0.75,
                ))

        except json.JSONDecodeError as e:
            logger.warning("Failed to parse LLM response", error=str(e))
        except Exception as e:
            logger.warning("Error processing LLM response", error=str(e))

        return terms

    def _extract_terms_with_rules(
        self, page_text: str, page_num: int
    ) -> List[ExtractedTerm]:
        """Fallback: Extract terms using rule-based parsing.

        Args:
            page_text: Text content of the page.
            page_num: Page number for reference.

        Returns:
            List of extracted terms (may be empty if rules don't match).
        """
        # This is a simplified rule-based fallback
        # In production, this would have more sophisticated regex patterns

        terms = []
        import re

        # Look for rate patterns like "$12.50" or "12.50/lb"
        rate_pattern = r'\$?(\d+\.?\d*)\s*(?:per\s*(?:lb|pound)|/lb)?'
        matches = re.findall(rate_pattern, page_text)

        # Look for zone patterns
        zone_pattern = r'Zone\s*(\d+)'
        zone_matches = re.findall(zone_pattern, page_text, re.IGNORECASE)

        # Look for surcharge patterns
        surcharge_keywords = [
            "fuel surcharge", "residential", "signature",
            "saturday", "address correction", "peak"
        ]

        for keyword in surcharge_keywords:
            if keyword.lower() in page_text.lower():
                # Try to find associated rate
                pattern = rf'{keyword}[:\s]*\$?(\d+\.?\d*)%?'
                match = re.search(pattern, page_text, re.IGNORECASE)
                if match:
                    rate_val = float(match.group(1))
                    rate_type = "percentage" if "%" in match.group(0) else "flat"
                    terms.append(ExtractedTerm(
                        term_type="surcharge",
                        surcharge_type=keyword.replace(" ", "_").lower(),
                        rate=rate_val,
                        rate_type=rate_type,
                        source_page=page_num,
                        source_text=match.group(0)[:200],
                        confidence_score=0.6,
                    ))

        return terms


# Export
__all__ = ["ContractParser", "ExtractedTerm"]
