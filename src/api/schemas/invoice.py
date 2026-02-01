"""Invoice-related schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.models.invoice import ProcessingStatus, SourceType


class InvoiceLineResponse(BaseModel):
    """Invoice line item response."""

    line_id: str
    line_number: int
    pro_number: str | None = None
    tracking_number: str | None = None
    reference_number: str | None = None
    service_level: str | None = None
    charge_type: str
    charge_description: str | None = None
    amount: Decimal
    weight: Decimal | None = None
    billed_weight: Decimal | None = None
    zone: str | None = None
    origin_zip: str | None = None
    destination_zip: str | None = None
    ship_date: date | None = None
    delivery_date: date | None = None
    shipment_id: str | None = None
    anomaly_count: int = 0

    class Config:
        from_attributes = True


class InvoiceResponse(BaseModel):
    """Invoice summary response."""

    invoice_id: str
    carrier_id: str
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    total_amount: Decimal
    currency: str = "USD"
    source_type: SourceType
    processing_status: ProcessingStatus
    line_count: int = 0
    anomaly_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class InvoiceDetail(InvoiceResponse):
    """Detailed invoice response with line items."""

    source_document_url: str | None = None
    account_number: str | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None
    processing_error: str | None = None
    lines: list[InvoiceLineResponse] = []


class InvoiceCreate(BaseModel):
    """Invoice creation request (for API/EDI ingestion)."""

    carrier_id: str
    invoice_number: str
    invoice_date: date
    due_date: date | None = None
    total_amount: Decimal
    currency: str = "USD"
    source_type: SourceType = SourceType.API
    account_number: str | None = None
    billing_period_start: date | None = None
    billing_period_end: date | None = None


class InvoiceUploadResponse(BaseModel):
    """Response after uploading an invoice PDF."""

    invoice_id: str
    status: ProcessingStatus
    filename: str
    uploaded_at: datetime
    message: str = "Invoice uploaded successfully and queued for processing"


class InvoiceListParams(BaseModel):
    """Invoice list query parameters."""

    carrier_id: str | None = None
    status: ProcessingStatus | None = None
    date_from: date | None = None
    date_to: date | None = None
    sort_by: str = Field(default="invoice_date", pattern="^(invoice_date|total_amount|created_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
