"""Anomaly-related schemas."""

from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from src.models.anomaly import AnomalyStatus, AnomalyType


class InvoiceLineContext(BaseModel):
    """Invoice line context for anomaly."""

    line_id: str
    invoice_id: str
    invoice_number: str
    pro_number: str | None = None
    tracking_number: str | None = None
    charge_type: str
    amount: Decimal


class ShipmentContext(BaseModel):
    """Shipment context for anomaly."""

    shipment_id: str
    pro_number: str | None = None
    tracking_number: str | None = None
    service_level: str | None = None
    ship_date: str | None = None
    expected_delivery: str | None = None
    actual_delivery: str | None = None


class ContractTermContext(BaseModel):
    """Contract term context for anomaly."""

    term_id: str
    contract_id: str
    contract_number: str
    term_type: str
    rate: Decimal | None = None
    source_text: str | None = None
    source_page: int | None = None


class AnomalyResponse(BaseModel):
    """Anomaly summary response."""

    anomaly_id: str
    line_id: str
    anomaly_type: AnomalyType
    expected_amount: Decimal | None = None
    actual_amount: Decimal
    variance: Decimal
    confidence_score: Decimal
    detection_rule: str
    status: AnomalyStatus
    description: str | None = None
    created_at: datetime

    # Summary fields
    invoice_number: str | None = None
    pro_number: str | None = None
    has_claim: bool = False

    class Config:
        from_attributes = True


class AnomalyDetail(AnomalyResponse):
    """Detailed anomaly response with context."""

    contract_reference: str | None = None
    contract_term_id: str | None = None
    evidence: str | None = None
    resolution_notes: str | None = None
    resolved_by: str | None = None
    duplicate_of_line_id: str | None = None

    # Related entities
    invoice_line: InvoiceLineContext | None = None
    shipment: ShipmentContext | None = None
    contract_term: ContractTermContext | None = None


class AnomalyStatusUpdate(BaseModel):
    """Request to update anomaly status."""

    status: AnomalyStatus
    resolution_notes: str | None = None


class AnomalyListParams(BaseModel):
    """Anomaly list query parameters."""

    status: AnomalyStatus | None = None
    anomaly_type: AnomalyType | None = None
    date_from: str | None = None
    date_to: str | None = None
    confidence_min: Decimal | None = Field(default=None, ge=0, le=1)
    invoice_id: str | None = None
    sort_by: str = Field(
        default="variance",
        pattern="^(variance|confidence_score|created_at)$",
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
