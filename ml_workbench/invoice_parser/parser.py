"""FedEx invoice parsing for text extraction."""

import re
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional

import structlog

logger = structlog.get_logger(__name__)


class FedExInvoiceParser:
    """Parse FedEx invoice text to extract structured data."""

    def parse(self, text: str) -> Dict[str, Any]:
        """Parse invoice text and extract structured fields.

        Args:
            text: Raw text extracted from invoice PDF.

        Returns:
            Dict with extracted invoice data.
        """
        result = {
            "invoice_number": None,
            "invoice_date": None,
            "due_date": None,
            "total_amount": None,
            "currency": "USD",
            "account_number": None,
            "lines": [],
            "confidence": {},
        }

        if not text:
            return result

        # Extract header fields
        result["invoice_number"] = self._extract_invoice_number(text)
        result["invoice_date"] = self._extract_date(text, "invoice")
        result["due_date"] = self._extract_date(text, "due")
        result["total_amount"] = self._extract_total(text)
        result["account_number"] = self._extract_account_number(text)

        # Extract line items
        result["lines"] = self._extract_lines(text)

        # Calculate confidence scores
        result["confidence"] = self._calculate_confidence(result)

        return result

    def _extract_invoice_number(self, text: str) -> Optional[str]:
        """Extract invoice number from text."""
        patterns = [
            r"Invoice\s*(?:Number|No\.?|#)[\s:]*([A-Z0-9-]+)",
            r"Invoice[\s:]+([0-9-]+)",
            r"INV[\s#-]*([0-9]+)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_date(self, text: str, date_type: str) -> Optional[str]:
        """Extract date from text.

        Args:
            text: Text to search.
            date_type: Type of date ("invoice" or "due").

        Returns:
            Date string in YYYY-MM-DD format or None.
        """
        if date_type == "invoice":
            patterns = [
                r"Invoice\s*Date[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"Date[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"(\w+\s+\d{1,2},?\s+\d{4})",
            ]
        else:  # due date
            patterns = [
                r"Due\s*Date[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
                r"Payment\s*Due[\s:]*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})",
            ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                date_str = match.group(1).strip()
                return self._parse_date(date_str)

        return None

    def _parse_date(self, date_str: str) -> Optional[str]:
        """Parse date string to standard format."""
        formats = [
            "%m/%d/%Y",
            "%m-%d-%Y",
            "%m/%d/%y",
            "%m-%d-%y",
            "%B %d, %Y",
            "%b %d, %Y",
            "%B %d %Y",
        ]

        for fmt in formats:
            try:
                dt = datetime.strptime(date_str, fmt)
                return dt.strftime("%Y-%m-%d")
            except ValueError:
                continue

        return None

    def _extract_total(self, text: str) -> Optional[float]:
        """Extract total amount from text."""
        patterns = [
            r"Total\s*(?:Amount|Due)?[\s:]*\$?([\d,]+\.?\d*)",
            r"Amount\s*Due[\s:]*\$?([\d,]+\.?\d*)",
            r"Grand\s*Total[\s:]*\$?([\d,]+\.?\d*)",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                amount_str = match.group(1).replace(",", "")
                try:
                    return float(amount_str)
                except ValueError:
                    continue

        return None

    def _extract_account_number(self, text: str) -> Optional[str]:
        """Extract FedEx account number."""
        patterns = [
            r"Account\s*(?:Number|No\.?|#)?[\s:]*(\d{9})",
            r"Acct[\s#:]*(\d{9})",
        ]

        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE)
            if match:
                return match.group(1).strip()

        return None

    def _extract_lines(self, text: str) -> List[Dict[str, Any]]:
        """Extract line items from text."""
        lines = []

        # Look for tracking number patterns
        tracking_pattern = r"(\d{12,22})"
        tracking_matches = re.findall(tracking_pattern, text)

        # Look for PRO number patterns (FedEx Freight)
        pro_pattern = r"(?:PRO|Pro)\s*#?\s*(\d{10,})"
        pro_matches = re.findall(pro_pattern, text, re.IGNORECASE)

        # Look for amount patterns
        amount_pattern = r"\$?([\d,]+\.\d{2})"
        amounts = re.findall(amount_pattern, text)

        # Build line items from tracking numbers
        for tracking in tracking_matches[:20]:  # Limit to 20 lines
            line = {
                "tracking_number": tracking,
                "charge_type": "freight",
                "amount": None,
            }

            # Try to find associated amount
            # (simplified - in production would use more sophisticated matching)
            if amounts:
                try:
                    line["amount"] = float(amounts.pop(0).replace(",", ""))
                except (ValueError, IndexError):
                    pass

            lines.append(line)

        # Also extract from PRO numbers
        for pro in pro_matches:
            if not any(l.get("pro_number") == pro for l in lines):
                line = {
                    "pro_number": pro,
                    "charge_type": "freight",
                    "amount": None,
                }
                if amounts:
                    try:
                        line["amount"] = float(amounts.pop(0).replace(",", ""))
                    except (ValueError, IndexError):
                        pass
                lines.append(line)

        return lines

    def _calculate_confidence(self, result: Dict) -> Dict[str, float]:
        """Calculate confidence scores for extracted fields."""
        confidence = {}

        # Invoice number confidence
        if result.get("invoice_number"):
            confidence["invoice_number"] = 0.9
        else:
            confidence["invoice_number"] = 0.0

        # Date confidence
        if result.get("invoice_date"):
            confidence["invoice_date"] = 0.85
        else:
            confidence["invoice_date"] = 0.0

        # Total confidence
        if result.get("total_amount"):
            confidence["total_amount"] = 0.8
        else:
            confidence["total_amount"] = 0.0

        # Lines confidence
        if result.get("lines"):
            confidence["lines"] = 0.7
        else:
            confidence["lines"] = 0.0

        # Overall confidence
        scores = [v for v in confidence.values() if v > 0]
        confidence["overall"] = sum(scores) / len(scores) if scores else 0.0

        return confidence


# Export
__all__ = ["FedExInvoiceParser"]
