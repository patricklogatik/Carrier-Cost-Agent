"""Contract-related schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.models.contract import ParsingStatus, TermType


class ContractTermResponse(BaseModel):
    """Contract term response."""

    term_id: str
    term_type: TermType
    service_level: str | None = None
    zone: str | None = None
    weight_min: Decimal | None = None
    weight_max: Decimal | None = None
    rate: Decimal | None = None
    rate_type: str | None = None
    conditions: dict[str, Any] | None = None
    source_page: int | None = None
    source_text: str | None = None
    confidence_score: Decimal | None = None
    validated: bool = False
    validated_by: str | None = None
    validated_at: datetime | None = None

    class Config:
        from_attributes = True


class ContractResponse(BaseModel):
    """Contract summary response."""

    contract_id: str
    carrier_id: str
    contract_number: str
    effective_date: date
    expiration_date: date
    parsing_status: ParsingStatus
    version: int
    is_active: bool
    term_count: int = 0
    validated_term_count: int = 0
    created_at: datetime

    class Config:
        from_attributes = True


class ContractDetail(ContractResponse):
    """Detailed contract response."""

    source_document_url: str | None = None
    parsing_error: str | None = None
    terms: list[ContractTermResponse] = []


class ContractCreate(BaseModel):
    """Contract creation request (metadata only, PDF uploaded separately)."""

    carrier_id: str
    contract_number: str
    effective_date: date
    expiration_date: date


class ContractUploadResponse(BaseModel):
    """Response after uploading a contract PDF."""

    contract_id: str
    status: ParsingStatus
    filename: str
    uploaded_at: datetime
    message: str = "Contract uploaded successfully and queued for parsing"


class ContractTermValidation(BaseModel):
    """Request to validate/update a contract term."""

    validated: bool
    rate: Decimal | None = None
    rate_type: str | None = None
    conditions: dict[str, Any] | None = None
    service_level: str | None = None
    zone: str | None = None
    weight_min: Decimal | None = None
    weight_max: Decimal | None = None


class ContractLookupRequest(BaseModel):
    """Request to look up applicable contract terms."""

    carrier_id: str
    service_level: str
    zone: str | None = None
    weight: Decimal | None = None
    ship_date: date | None = None


class RateLookupResult(BaseModel):
    """Rate lookup result."""

    amount: Decimal
    rate_type: str | None = None
    term_id: str
    source_text: str | None = None
    confidence_score: Decimal | None = None


class SurchargeLookupResult(BaseModel):
    """Surcharge lookup result."""

    surcharge_type: str
    amount: Decimal | None = None
    rate: Decimal | None = None
    rate_type: str | None = None
    conditions: dict[str, Any] | None = None
    term_id: str


class SLALookupResult(BaseModel):
    """SLA lookup result."""

    delivery_days: int | None = None
    guarantee: str | None = None
    conditions: dict[str, Any] | None = None
    term_id: str


class ContractLookupResponse(BaseModel):
    """Response from contract term lookup."""

    base_rate: RateLookupResult | None = None
    surcharges: list[SurchargeLookupResult] = []
    sla: SLALookupResult | None = None
    contract_id: str | None = None
    contract_number: str | None = None
