"""Tests for invoice field parser."""

from decimal import Decimal

import pytest

from src.services.invoice.field_parser import FedExInvoiceParser


class TestFedExInvoiceParser:
    """Tests for FedEx invoice parser."""

    @pytest.fixture
    def parser(self) -> FedExInvoiceParser:
        """Create parser instance."""
        return FedExInvoiceParser()

    def test_parse_empty_text(self, parser: FedExInvoiceParser):
        """Test parsing empty text."""
        result = parser.parse("")
        assert result.invoice_number is None
        assert result.total_amount == Decimal("0")
        assert len(result.line_items) == 0
        assert result.confidence < 0.5

    def test_extract_invoice_number(self, parser: FedExInvoiceParser):
        """Test invoice number extraction."""
        text = "Invoice Number: 1234567890"
        result = parser.parse(text)
        assert result.invoice_number == "1234567890"

    def test_extract_invoice_number_with_hash(self, parser: FedExInvoiceParser):
        """Test invoice number extraction with hash symbol."""
        text = "Invoice #: 9876543210"
        result = parser.parse(text)
        assert result.invoice_number == "9876543210"

    def test_extract_total_amount(self, parser: FedExInvoiceParser):
        """Test total amount extraction."""
        text = "Total Amount Due: $1,234.56"
        result = parser.parse(text)
        assert result.total_amount == Decimal("1234.56")

    def test_extract_total_amount_without_dollar(self, parser: FedExInvoiceParser):
        """Test total amount extraction without dollar sign."""
        text = "Balance Due: 500.00"
        result = parser.parse(text)
        assert result.total_amount == Decimal("500.00")

    def test_extract_date(self, parser: FedExInvoiceParser):
        """Test date extraction."""
        text = "Invoice Date: 01/15/2026"
        result = parser.parse(text)
        assert result.invoice_date is not None
        assert result.invoice_date.year == 2026
        assert result.invoice_date.month == 1
        assert result.invoice_date.day == 15

    def test_extract_account_number(self, parser: FedExInvoiceParser):
        """Test account number extraction."""
        text = "Account #: 123456789"
        result = parser.parse(text)
        assert result.account_number == "123456789"

    def test_service_level_normalization(self, parser: FedExInvoiceParser):
        """Test service level normalization."""
        assert parser._normalize_service_level("FXG") == "FedEx Ground"
        assert parser._normalize_service_level("GROUND") == "FedEx Ground"
        assert parser._normalize_service_level("HOME") == "FedEx Home Delivery"
        assert parser._normalize_service_level("2DAY") == "FedEx 2Day"
        assert parser._normalize_service_level("Custom Service") == "Custom Service"

    def test_determine_charge_type(self, parser: FedExInvoiceParser):
        """Test charge type determination."""
        assert parser._determine_charge_type("Fuel Surcharge") == "fuel"
        assert parser._determine_charge_type("Residential Delivery") == "residential"
        assert parser._determine_charge_type("Signature Required") == "signature"
        assert parser._determine_charge_type("Address Correction Fee") == "address_correction"
        assert parser._determine_charge_type("Base Transportation") == "freight"

    def test_parse_amount(self, parser: FedExInvoiceParser):
        """Test amount parsing."""
        assert parser._parse_amount("$1,234.56") == Decimal("1234.56")
        assert parser._parse_amount("500.00") == Decimal("500.00")
        assert parser._parse_amount("(100.00)") == Decimal("-100.00")
        assert parser._parse_amount("") == Decimal("0")
        assert parser._parse_amount(None) == Decimal("0")

    def test_extract_zip(self, parser: FedExInvoiceParser):
        """Test ZIP code extraction."""
        assert parser._extract_zip("New York, NY 10001") == "10001"
        assert parser._extract_zip("90210-1234") == "90210"
        assert parser._extract_zip("No ZIP here") is None

    def test_parse_tables(self, parser: FedExInvoiceParser):
        """Test table parsing."""
        tables = [
            [
                ["Tracking #", "Service", "Zone", "Weight", "Amount"],
                ["794644790292", "Ground", "2", "5.5", "$75.00"],
                ["794644790293", "Ground", "3", "8.0", "$95.00"],
            ]
        ]

        result = parser.parse("", tables)
        assert len(result.line_items) == 2
        assert result.line_items[0].tracking_number == "794644790292"
        assert result.line_items[0].amount == Decimal("75.00")
        assert result.line_items[1].tracking_number == "794644790293"
        assert result.line_items[1].amount == Decimal("95.00")

    def test_confidence_scoring(self, parser: FedExInvoiceParser):
        """Test confidence score calculation."""
        # Full invoice data should have high confidence
        text = """
        Invoice Number: 1234567890
        Invoice Date: 01/15/2026
        Total Amount Due: $150.00
        """
        tables = [
            [
                ["Tracking #", "Amount"],
                ["794644790292", "$75.00"],
            ]
        ]

        result = parser.parse(text, tables)
        assert result.confidence > 0.7

        # Minimal data should have low confidence
        result_minimal = parser.parse("Some random text")
        assert result_minimal.confidence < 0.5
