"""Invoice data ingestion to Celonis Data Pool.

This module provides connectors for pushing invoice data
from various sources to the Celonis Data Pool.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table
from ml_workbench.invoice_parser import PDFExtractor, FedExInvoiceParser

logger = structlog.get_logger(__name__)


class InvoiceConnector:
    """Push invoice data to Celonis Data Pool.

    Supports ingestion from:
    - PDF files (with automatic parsing)
    - CSV/Excel files (batch import)
    - Direct API calls (structured data)
    """

    def __init__(self, data_pool=None):
        """Initialize the invoice connector.

        Args:
            data_pool: Optional Celonis Data Pool connection.
        """
        if data_pool is None:
            celonis = get_celonis_connection()
            data_pool = get_data_pool(celonis)

        self.data_pool = data_pool
        self.invoice_table = get_table("invoice", data_pool)
        self.line_table = get_table("invoice_line", data_pool)

    def ingest_pdf(
        self,
        pdf_path: str,
        carrier_id: str,
        store_original: bool = True,
    ) -> Dict[str, Any]:
        """Ingest an invoice from a PDF file.

        Args:
            pdf_path: Path to the PDF file.
            carrier_id: UUID of the carrier.
            store_original: Whether to store the original PDF path.

        Returns:
            Dict with ingestion results.
        """
        logger.info("Ingesting PDF invoice", pdf_path=pdf_path)

        # Extract text from PDF
        extractor = PDFExtractor()
        extracted = extractor.extract(pdf_path)

        if not extracted.get("text"):
            return {
                "status": "failed",
                "error": "Failed to extract text from PDF",
            }

        # Parse extracted text
        parser = FedExInvoiceParser()
        parsed = parser.parse(extracted["text"])

        if not parsed.get("invoice_number"):
            return {
                "status": "failed",
                "error": "Failed to parse invoice data",
            }

        # Create invoice record
        invoice_id = str(uuid4())
        invoice_data = {
            "invoice_id": invoice_id,
            "carrier_id": carrier_id,
            "invoice_number": parsed.get("invoice_number"),
            "invoice_date": parsed.get("invoice_date"),
            "due_date": parsed.get("due_date"),
            "total_amount": parsed.get("total_amount"),
            "currency": parsed.get("currency", "USD"),
            "source_type": "pdf",
            "source_document_path": pdf_path if store_original else None,
            "processing_status": "completed",
            "raw_text": extracted.get("text", "")[:65000],
            "created_at": datetime.now(),
        }

        # Create line records
        lines = []
        for i, line_data in enumerate(parsed.get("lines", [])):
            line_id = str(uuid4())
            lines.append({
                "line_id": line_id,
                "invoice_id": invoice_id,
                "line_number": i + 1,
                "pro_number": line_data.get("pro_number"),
                "tracking_number": line_data.get("tracking_number"),
                "charge_type": line_data.get("charge_type", "freight"),
                "charge_description": line_data.get("description"),
                "amount": line_data.get("amount"),
                "weight": line_data.get("weight"),
                "zone": line_data.get("zone"),
                "service_level": line_data.get("service_level"),
                "created_at": datetime.now(),
            })

        # Save to Data Pool
        invoice_df = pd.DataFrame([invoice_data])
        self.invoice_table.upsert(invoice_df, keys=["invoice_id"])

        if lines:
            lines_df = pd.DataFrame(lines)
            self.line_table.upsert(lines_df, keys=["line_id"])

        logger.info(
            "Invoice ingested",
            invoice_id=invoice_id,
            lines=len(lines),
        )

        return {
            "status": "success",
            "invoice_id": invoice_id,
            "invoice_number": parsed.get("invoice_number"),
            "lines_created": len(lines),
            "total_amount": parsed.get("total_amount"),
        }

    def ingest_batch(
        self,
        data: List[Dict[str, Any]],
        carrier_id: str,
        update_existing: bool = True,
    ) -> Dict[str, Any]:
        """Ingest multiple invoices from structured data.

        Args:
            data: List of invoice dictionaries with lines.
            carrier_id: UUID of the carrier.
            update_existing: Whether to update existing invoices.

        Returns:
            Dict with batch results.
        """
        logger.info("Starting batch ingestion", count=len(data))

        results = {
            "total": len(data),
            "created": 0,
            "updated": 0,
            "errors": 0,
            "error_details": [],
        }

        for i, invoice_data in enumerate(data):
            try:
                result = self._ingest_single(invoice_data, carrier_id, update_existing)

                if result.get("status") == "created":
                    results["created"] += 1
                elif result.get("status") == "updated":
                    results["updated"] += 1

            except Exception as e:
                results["errors"] += 1
                results["error_details"].append({
                    "index": i,
                    "error": str(e),
                })
                logger.warning("Failed to ingest invoice", index=i, error=str(e))

        logger.info("Batch ingestion complete", results=results)
        return results

    def _ingest_single(
        self,
        data: Dict[str, Any],
        carrier_id: str,
        update_existing: bool,
    ) -> Dict[str, Any]:
        """Ingest a single invoice from structured data."""
        invoice_number = data.get("invoice_number")

        # Check for existing
        existing = self.invoice_table.get_data_frame(
            filter=f"invoice_number = '{invoice_number}' AND carrier_id = '{carrier_id}'"
        )

        if not existing.empty:
            if not update_existing:
                return {"status": "skipped", "reason": "exists"}

            invoice_id = existing.iloc[0]["invoice_id"]
            status = "updated"
        else:
            invoice_id = str(uuid4())
            status = "created"

        # Build invoice record
        invoice_record = {
            "invoice_id": invoice_id,
            "carrier_id": carrier_id,
            "invoice_number": invoice_number,
            "invoice_date": data.get("invoice_date"),
            "due_date": data.get("due_date"),
            "total_amount": data.get("total_amount"),
            "currency": data.get("currency", "USD"),
            "source_type": data.get("source_type", "api"),
            "processing_status": "completed",
            "created_at": datetime.now(),
        }

        # Build line records
        lines = []
        for i, line_data in enumerate(data.get("lines", [])):
            line_id = str(uuid4())
            lines.append({
                "line_id": line_id,
                "invoice_id": invoice_id,
                "line_number": i + 1,
                **line_data,
                "created_at": datetime.now(),
            })

        # Save to Data Pool
        invoice_df = pd.DataFrame([invoice_record])
        self.invoice_table.upsert(invoice_df, keys=["invoice_id"])

        if lines:
            lines_df = pd.DataFrame(lines)
            self.line_table.upsert(lines_df, keys=["line_id"])

        return {"status": status, "invoice_id": invoice_id}

    def ingest_csv(
        self,
        csv_path: str,
        carrier_id: str,
        mapping: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        """Ingest invoices from a CSV file.

        Args:
            csv_path: Path to the CSV file.
            carrier_id: UUID of the carrier.
            mapping: Column name mapping (csv_col -> our_field).

        Returns:
            Dict with ingestion results.
        """
        logger.info("Ingesting from CSV", csv_path=csv_path)

        df = pd.read_csv(csv_path)

        # Apply column mapping
        if mapping:
            df = df.rename(columns=mapping)

        # Convert to list of dicts
        data = df.to_dict("records")

        return self.ingest_batch(data, carrier_id)


# Export
__all__ = ["InvoiceConnector"]
