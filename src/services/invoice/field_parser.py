"""Invoice field parsing for FedEx invoices."""

import re
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ParsedLineItem:
    """Parsed invoice line item."""

    line_number: int
    tracking_number: str | None = None
    pro_number: str | None = None
    reference_number: str | None = None
    service_level: str | None = None
    charge_type: str = "freight"
    charge_description: str | None = None
    amount: Decimal = Decimal("0")
    weight: Decimal | None = None
    billed_weight: Decimal | None = None
    zone: str | None = None
    origin_zip: str | None = None
    destination_zip: str | None = None
    ship_date: date | None = None
    delivery_date: date | None = None
    confidence: float = 0.0


@dataclass
class ParsedInvoice:
    """Parsed invoice data."""

    invoice_number: str | None = None
    invoice_date: date | None = None
    due_date: date | None = None
    total_amount: Decimal = Decimal("0")
    account_number: str | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    line_items: list[ParsedLineItem] = field(default_factory=list)
    raw_text: str = ""
    confidence: float = 0.0


class FedExInvoiceParser:
    """Parse FedEx invoice text into structured data."""

    # Common FedEx service level mappings
    SERVICE_LEVELS = {
        "FXG": "FedEx Ground",
        "GROUND": "FedEx Ground",
        "HOME": "FedEx Home Delivery",
        "HOME DELIVERY": "FedEx Home Delivery",
        "EXPRESS": "FedEx Express",
        "2DAY": "FedEx 2Day",
        "PRIORITY": "FedEx Priority Overnight",
        "STANDARD": "FedEx Standard Overnight",
        "FIRST": "FedEx First Overnight",
        "INTL": "FedEx International",
        "FREIGHT": "FedEx Freight",
    }

    # Charge type patterns
    CHARGE_TYPES = {
        "fuel": ["fuel surcharge", "fuel", "fsc"],
        "residential": ["residential", "resi", "residential delivery"],
        "signature": ["signature", "direct signature", "adult signature"],
        "address_correction": ["address correction", "addr corr"],
        "saturday": ["saturday", "sat delivery"],
        "oversize": ["oversize", "additional handling"],
        "late_delivery": ["late fee", "late delivery"],
        "dim_weight": ["dimensional", "dim weight"],
    }

    def parse(self, text: str, tables: list[list[list[str]]] | None = None) -> ParsedInvoice:
        """Parse invoice text into structured data.

        Args:
            text: Extracted text from invoice PDF.
            tables: Optional extracted tables.

        Returns:
            ParsedInvoice with extracted fields.
        """
        result = ParsedInvoice(raw_text=text)

        # Extract header fields
        result.invoice_number = self._extract_invoice_number(text)
        result.invoice_date = self._extract_date(text, ["invoice date", "inv date", "date:"])
        result.due_date = self._extract_date(text, ["due date", "payment due"])
        result.total_amount = self._extract_total_amount(text)
        result.account_number = self._extract_account_number(text)

        # Extract line items from tables first
        if tables:
            result.line_items = self._parse_tables(tables)

        # If no tables, try to parse from text
        if not result.line_items:
            result.line_items = self._parse_line_items_from_text(text)

        # Calculate confidence based on what was extracted
        result.confidence = self._calculate_confidence(result)

        logger.info(
            "Invoice parsed",
            invoice_number=result.invoice_number,
            total_amount=str(result.total_amount),
            line_count=len(result.line_items),
            confidence=result.confidence,
        )

        return result

    def _extract_invoice_number(self, text: str) -> str | None:
        """Extract invoice number from text."""
        patterns = [
            r"invoice\s*#?\s*:?\s*(\d{8,15})",
            r"invoice\s+number\s*:?\s*(\d{8,15})",
            r"inv\s*#?\s*:?\s*(\d{8,15})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _extract_date(self, text: str, keywords: list[str]) -> date | None:
        """Extract a date from text near given keywords."""
        date_patterns = [
            r"(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            r"(\w+\s+\d{1,2},?\s+\d{4})",
            r"(\d{4}[/-]\d{2}[/-]\d{2})",
        ]

        for keyword in keywords:
            # Find text around keyword
            pattern = rf"{keyword}\s*:?\s*(.{{0,30}})"
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                context = match.group(1)
                for date_pattern in date_patterns:
                    date_match = re.search(date_pattern, context)
                    if date_match:
                        return self._parse_date_string(date_match.group(1))
        return None

    def _parse_date_string(self, date_str: str) -> date | None:
        """Parse a date string into a date object."""
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%m/%d/%y",
            "%Y-%m-%d",
            "%B %d, %Y",
            "%b %d, %Y",
        ]
        for fmt in formats:
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        return None

    def _extract_total_amount(self, text: str) -> Decimal:
        """Extract total amount from text."""
        patterns = [
            r"total\s+(?:amount\s+)?(?:due\s+)?:?\s*\$?\s*([\d,]+\.?\d*)",
            r"amount\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
            r"balance\s+due\s*:?\s*\$?\s*([\d,]+\.?\d*)",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    return Decimal(amount_str)
                except:
                    pass
        return Decimal("0")

    def _extract_account_number(self, text: str) -> str | None:
        """Extract FedEx account number from text."""
        patterns = [
            r"account\s*#?\s*:?\s*(\d{9})",
            r"acct\s*#?\s*:?\s*(\d{9})",
            r"(?:fedex\s+)?account\s*:?\s*(\d{9})",
        ]
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1)
        return None

    def _parse_tables(self, tables: list[list[list[str]]]) -> list[ParsedLineItem]:
        """Parse line items from extracted tables."""
        items: list[ParsedLineItem] = []
        line_num = 0

        for table in tables:
            if not table or len(table) < 2:
                continue

            # Try to identify header row
            header = [str(cell).lower().strip() for cell in table[0]]

            # Map column indices
            col_map = self._map_columns(header)
            if not col_map:
                continue

            # Parse data rows
            for row in table[1:]:
                if len(row) < len(header):
                    continue

                line_num += 1
                item = self._parse_table_row(row, col_map, line_num)
                if item and item.amount != Decimal("0"):
                    items.append(item)

        return items

    def _map_columns(self, header: list[str]) -> dict[str, int] | None:
        """Map column names to indices."""
        mapping: dict[str, int] = {}

        column_patterns = {
            "tracking": ["tracking", "track #", "tracking #", "tracking number"],
            "pro_number": ["pro", "pro #", "pro number", "bill of lading"],
            "service": ["service", "service level", "service type"],
            "amount": ["amount", "charge", "total", "charges", "amt"],
            "weight": ["weight", "wt", "actual wt"],
            "zone": ["zone", "zn"],
            "origin": ["origin", "ship from", "from zip"],
            "destination": ["dest", "destination", "ship to", "to zip"],
            "ship_date": ["ship date", "shipped", "ship dt"],
            "description": ["description", "desc", "details"],
        }

        for i, col in enumerate(header):
            for field_name, patterns in column_patterns.items():
                if any(p in col for p in patterns):
                    mapping[field_name] = i
                    break

        # Require at least amount column
        return mapping if "amount" in mapping else None

    def _parse_table_row(
        self, row: list[str], col_map: dict[str, int], line_num: int
    ) -> ParsedLineItem | None:
        """Parse a single table row into a line item."""
        try:
            item = ParsedLineItem(line_number=line_num)

            if "tracking" in col_map:
                item.tracking_number = self._clean_string(row[col_map["tracking"]])
            if "pro_number" in col_map:
                item.pro_number = self._clean_string(row[col_map["pro_number"]])
            if "service" in col_map:
                item.service_level = self._normalize_service_level(row[col_map["service"]])
            if "amount" in col_map:
                item.amount = self._parse_amount(row[col_map["amount"]])
            if "weight" in col_map:
                item.weight = self._parse_decimal(row[col_map["weight"]])
            if "zone" in col_map:
                item.zone = self._clean_string(row[col_map["zone"]])
            if "origin" in col_map:
                item.origin_zip = self._extract_zip(row[col_map["origin"]])
            if "destination" in col_map:
                item.destination_zip = self._extract_zip(row[col_map["destination"]])
            if "description" in col_map:
                item.charge_description = self._clean_string(row[col_map["description"]])
                item.charge_type = self._determine_charge_type(item.charge_description or "")

            item.confidence = 0.9 if item.tracking_number or item.pro_number else 0.7

            return item

        except Exception as e:
            logger.warning("Error parsing table row", error=str(e))
            return None

    def _parse_line_items_from_text(self, text: str) -> list[ParsedLineItem]:
        """Parse line items directly from text when no tables are available."""
        items: list[ParsedLineItem] = []

        # Pattern to find tracking numbers with amounts
        pattern = r"(\d{12,22})\s+.*?\$?\s*([\d,]+\.?\d{2})"

        matches = re.findall(pattern, text)
        for i, (tracking, amount_str) in enumerate(matches, 1):
            item = ParsedLineItem(
                line_number=i,
                tracking_number=tracking,
                amount=self._parse_amount(amount_str),
                confidence=0.6,
            )
            items.append(item)

        return items

    def _clean_string(self, value: str | None) -> str | None:
        """Clean and normalize a string value."""
        if not value:
            return None
        cleaned = str(value).strip()
        return cleaned if cleaned else None

    def _parse_amount(self, value: str | None) -> Decimal:
        """Parse an amount string to Decimal."""
        if not value:
            return Decimal("0")
        try:
            cleaned = str(value).replace("$", "").replace(",", "").strip()
            # Handle negative amounts
            if cleaned.startswith("(") and cleaned.endswith(")"):
                cleaned = "-" + cleaned[1:-1]
            return Decimal(cleaned)
        except:
            return Decimal("0")

    def _parse_decimal(self, value: str | None) -> Decimal | None:
        """Parse a decimal string."""
        if not value:
            return None
        try:
            cleaned = str(value).replace(",", "").strip()
            return Decimal(cleaned)
        except:
            return None

    def _extract_zip(self, value: str | None) -> str | None:
        """Extract ZIP code from a string."""
        if not value:
            return None
        match = re.search(r"\b(\d{5})(?:-\d{4})?\b", str(value))
        return match.group(1) if match else None

    def _normalize_service_level(self, value: str | None) -> str | None:
        """Normalize service level to standard name."""
        if not value:
            return None
        upper = str(value).upper().strip()
        for key, name in self.SERVICE_LEVELS.items():
            if key in upper:
                return name
        return value

    def _determine_charge_type(self, description: str) -> str:
        """Determine charge type from description."""
        lower = description.lower()
        for charge_type, keywords in self.CHARGE_TYPES.items():
            if any(kw in lower for kw in keywords):
                return charge_type
        return "freight"

    def _calculate_confidence(self, invoice: ParsedInvoice) -> float:
        """Calculate overall parsing confidence."""
        scores = []

        # Invoice number found
        if invoice.invoice_number:
            scores.append(1.0)
        else:
            scores.append(0.0)

        # Date found
        if invoice.invoice_date:
            scores.append(1.0)
        else:
            scores.append(0.3)

        # Total amount found
        if invoice.total_amount > 0:
            scores.append(1.0)
        else:
            scores.append(0.2)

        # Line items found
        if invoice.line_items:
            line_confidence = sum(li.confidence for li in invoice.line_items) / len(invoice.line_items)
            scores.append(line_confidence)
        else:
            scores.append(0.2)

        return sum(scores) / len(scores) if scores else 0.0
