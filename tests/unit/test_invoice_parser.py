"""Tests for invoice parsing components."""

import pytest

from ml_workbench.invoice_parser import FedExInvoiceParser, PDFExtractor


class TestFedExInvoiceParser:
    """Tests for FedEx invoice parser."""

    @pytest.fixture
    def parser(self) -> FedExInvoiceParser:
        """Create parser instance."""
        return FedExInvoiceParser()

    def test_parse_empty_text(self, parser: FedExInvoiceParser):
        """Test parsing empty text returns empty result."""
        result = parser.parse("")
        assert result["invoice_number"] is None
        assert result["total_amount"] is None
        assert result["lines"] == []

    def test_extract_invoice_number(self, parser: FedExInvoiceParser):
        """Test invoice number extraction."""
        text = "Invoice Number: 1234567890"
        result = parser.parse(text)
        assert result["invoice_number"] == "1234567890"

    def test_extract_invoice_number_with_hash(self, parser: FedExInvoiceParser):
        """Test invoice number extraction with hash symbol."""
        text = "Invoice #: 9876543210"
        result = parser.parse(text)
        assert result["invoice_number"] == "9876543210"

    def test_extract_total_amount(self, parser: FedExInvoiceParser):
        """Test total amount extraction."""
        text = "Total Amount Due: $1,234.56"
        result = parser.parse(text)
        assert result["total_amount"] == 1234.56

    def test_extract_total_amount_without_dollar(self, parser: FedExInvoiceParser):
        """Test total amount extraction without dollar sign."""
        text = "Grand Total: 500.00"
        result = parser.parse(text)
        assert result["total_amount"] == 500.00

    def test_extract_invoice_date(self, parser: FedExInvoiceParser):
        """Test date extraction."""
        text = "Invoice Date: 01/15/2026"
        result = parser.parse(text)
        assert result["invoice_date"] == "2026-01-15"

    def test_extract_due_date(self, parser: FedExInvoiceParser):
        """Test due date extraction."""
        text = "Due Date: 02/15/2026"
        result = parser.parse(text)
        assert result["due_date"] == "2026-02-15"

    def test_extract_account_number(self, parser: FedExInvoiceParser):
        """Test account number extraction."""
        text = "Account #: 123456789"
        result = parser.parse(text)
        assert result["account_number"] == "123456789"

    def test_extract_tracking_numbers(self, parser: FedExInvoiceParser):
        """Test tracking number extraction."""
        text = """
        Shipments:
        794644790292  Ground  $75.00
        794644790293  Ground  $95.00
        """
        result = parser.parse(text)
        assert len(result["lines"]) >= 2
        tracking_numbers = [l.get("tracking_number") for l in result["lines"]]
        assert "794644790292" in tracking_numbers
        assert "794644790293" in tracking_numbers

    def test_confidence_calculation(self, parser: FedExInvoiceParser):
        """Test confidence score calculation."""
        # Complete data should have high confidence
        text = """
        Invoice Number: 1234567890
        Invoice Date: 01/15/2026
        Total Amount Due: $150.00
        794644790292  Ground  $75.00
        """
        result = parser.parse(text)
        assert result["confidence"]["overall"] > 0.6

    def test_confidence_empty_data(self, parser: FedExInvoiceParser):
        """Test confidence score with minimal data."""
        text = "Random text with no invoice data"
        result = parser.parse(text)
        assert result["confidence"]["overall"] == 0.0

    def test_parse_full_invoice(self, sample_invoice_text: str, parser: FedExInvoiceParser):
        """Test parsing a complete invoice."""
        result = parser.parse(sample_invoice_text)

        assert result["invoice_number"] == "INV-2026-001234"
        assert result["invoice_date"] == "2026-01-15"
        assert result["due_date"] == "2026-02-15"
        assert result["account_number"] == "123456789"
        assert result["total_amount"] == 1234.56
        assert len(result["lines"]) > 0


class TestPDFExtractor:
    """Tests for PDF extractor (mocked without actual PDF)."""

    def test_extractor_initialization(self):
        """Test extractor can be initialized."""
        extractor = PDFExtractor()
        assert extractor is not None

    def test_extract_nonexistent_file(self):
        """Test extracting from nonexistent file returns error."""
        extractor = PDFExtractor()
        result = extractor.extract("/nonexistent/file.pdf")
        assert "error" in result
        assert result["text"] == ""
