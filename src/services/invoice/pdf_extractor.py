"""PDF text extraction service."""

import io
from dataclasses import dataclass
from pathlib import Path

import pdfplumber
from PIL import Image

from src.core.config import settings
from src.core.logging import get_logger

logger = get_logger(__name__)


@dataclass
class ExtractionResult:
    """Result of PDF text extraction."""

    text: str
    pages: list[str]
    tables: list[list[list[str]]]
    page_count: int
    is_scanned: bool
    confidence: float


class PDFExtractor:
    """Extract text and tables from PDF documents."""

    def __init__(self) -> None:
        """Initialize the PDF extractor."""
        self.ocr_provider = settings.ocr_provider

    def extract(self, pdf_content: bytes) -> ExtractionResult:
        """Extract text from a PDF.

        Args:
            pdf_content: Raw PDF bytes.

        Returns:
            ExtractionResult with extracted text and metadata.
        """
        pages: list[str] = []
        tables: list[list[list[str]]] = []
        all_text: list[str] = []
        is_scanned = False

        with pdfplumber.open(io.BytesIO(pdf_content)) as pdf:
            page_count = len(pdf.pages)

            for page_num, page in enumerate(pdf.pages, 1):
                # Extract text
                page_text = page.extract_text() or ""

                # Check if page appears to be scanned (very little text)
                if len(page_text.strip()) < 50:
                    is_scanned = True
                    # TODO: Apply OCR for scanned pages
                    if self.ocr_provider == "tesseract":
                        page_text = self._ocr_page(page)

                pages.append(page_text)
                all_text.append(f"--- Page {page_num} ---\n{page_text}")

                # Extract tables
                page_tables = page.extract_tables() or []
                for table in page_tables:
                    if table:
                        # Convert None values to empty strings
                        cleaned_table = [
                            [str(cell) if cell else "" for cell in row]
                            for row in table
                        ]
                        tables.append(cleaned_table)

        full_text = "\n\n".join(all_text)

        # Calculate extraction confidence
        confidence = 1.0 if not is_scanned else 0.8

        logger.info(
            "PDF extraction complete",
            page_count=page_count,
            text_length=len(full_text),
            table_count=len(tables),
            is_scanned=is_scanned,
        )

        return ExtractionResult(
            text=full_text,
            pages=pages,
            tables=tables,
            page_count=page_count,
            is_scanned=is_scanned,
            confidence=confidence,
        )

    def _ocr_page(self, page) -> str:
        """Apply OCR to a scanned page.

        Args:
            page: pdfplumber page object.

        Returns:
            OCR'd text from the page.
        """
        try:
            import pytesseract

            # Convert page to image
            img = page.to_image(resolution=300)
            pil_image = img.original

            # Apply OCR
            text = pytesseract.image_to_string(pil_image)
            return text

        except Exception as e:
            logger.warning("OCR failed", error=str(e))
            return ""

    def extract_from_file(self, file_path: str | Path) -> ExtractionResult:
        """Extract text from a PDF file.

        Args:
            file_path: Path to the PDF file.

        Returns:
            ExtractionResult with extracted text and metadata.
        """
        path = Path(file_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF file not found: {file_path}")

        with open(path, "rb") as f:
            content = f.read()

        return self.extract(content)
