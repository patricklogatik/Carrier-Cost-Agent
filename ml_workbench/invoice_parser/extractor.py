"""PDF text and table extraction for invoice processing."""

from typing import Any, Dict, List, Optional

import pdfplumber
import structlog

logger = structlog.get_logger(__name__)


class PDFExtractor:
    """Extract text and tables from PDF documents."""

    def extract(self, pdf_path: str) -> Dict[str, Any]:
        """Extract all content from a PDF file.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Dict with extracted text, tables, and metadata.
        """
        result = {
            "text": "",
            "tables": [],
            "page_count": 0,
            "pages": [],
        }

        try:
            with pdfplumber.open(pdf_path) as pdf:
                result["page_count"] = len(pdf.pages)

                for i, page in enumerate(pdf.pages):
                    page_data = self._extract_page(page, i + 1)
                    result["pages"].append(page_data)
                    result["text"] += page_data["text"] + "\n\n"
                    result["tables"].extend(page_data["tables"])

        except Exception as e:
            logger.error("PDF extraction failed", path=pdf_path, error=str(e))
            result["error"] = str(e)

        return result

    def _extract_page(self, page, page_num: int) -> Dict[str, Any]:
        """Extract content from a single page.

        Args:
            page: pdfplumber page object.
            page_num: Page number (1-indexed).

        Returns:
            Dict with page text and tables.
        """
        page_data = {
            "page_number": page_num,
            "text": "",
            "tables": [],
        }

        # Extract text
        text = page.extract_text()
        if text:
            page_data["text"] = text

        # Extract tables
        tables = page.extract_tables()
        for table in tables:
            if table:
                page_data["tables"].append({
                    "page": page_num,
                    "rows": table,
                    "row_count": len(table),
                })

        return page_data

    def extract_text_only(self, pdf_path: str) -> str:
        """Extract only text from a PDF.

        Args:
            pdf_path: Path to the PDF file.

        Returns:
            Extracted text as a single string.
        """
        result = self.extract(pdf_path)
        return result.get("text", "")


# Export
__all__ = ["PDFExtractor"]
