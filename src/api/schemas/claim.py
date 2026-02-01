"""Claim-related schemas."""

from datetime import datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field

from src.models.claim import ClaimOutcome, ClaimStatus, MessageDirection, MessageType


class ClaimMessageResponse(BaseModel):
    """Claim message response."""

    message_id: str
    claim_id: str
    direction: MessageDirection
    message_type: MessageType
    content: str
    attachments: dict[str, Any] | None = None
    sender: str | None = None
    timestamp: datetime
    is_auto_generated: bool = False

    class Config:
        from_attributes = True


class ClaimResponse(BaseModel):
    """Claim summary response."""

    claim_id: str
    anomaly_id: str
    claim_number: str | None = None
    status: ClaimStatus
    requested_credit: Decimal
    outcome: ClaimOutcome | None = None
    credit_amount: Decimal | None = None
    submitted_date: datetime | None = None
    resolution_date: datetime | None = None
    created_at: datetime

    # Summary fields
    anomaly_type: str | None = None
    invoice_number: str | None = None
    variance: Decimal | None = None
    message_count: int = 0

    class Config:
        from_attributes = True


class ClaimDetail(ClaimResponse):
    """Detailed claim response."""

    claim_text: str
    claim_subject: str | None = None
    contract_citation: str | None = None
    evidence_references: dict[str, Any] | None = None
    carrier_reference: str | None = None
    resolution_notes: str | None = None
    approved_by: str | None = None
    approved_at: datetime | None = None
    rejection_reason: str | None = None
    created_by: str | None = None
    submitted_by: str | None = None

    # Related data
    messages: list[ClaimMessageResponse] = []


class ClaimCreate(BaseModel):
    """Request to create a claim from an anomaly."""

    anomaly_id: str
    claim_text: str | None = Field(
        default=None,
        description="Custom claim text. If not provided, will be auto-generated.",
    )
    claim_subject: str | None = None
    regenerate: bool = Field(
        default=False,
        description="Force regenerate claim text using AI",
    )


class ClaimUpdate(BaseModel):
    """Request to update a claim."""

    claim_text: str | None = None
    claim_subject: str | None = None
    contract_citation: str | None = None
    status: ClaimStatus | None = None
    outcome: ClaimOutcome | None = None
    credit_amount: Decimal | None = None
    carrier_reference: str | None = None
    resolution_notes: str | None = None


class ClaimApproval(BaseModel):
    """Request to approve or reject a claim."""

    approved: bool
    comments: str | None = None


class ClaimMessageCreate(BaseModel):
    """Request to add a message to a claim."""

    direction: MessageDirection
    message_type: MessageType
    content: str
    attachments: dict[str, Any] | None = None
    generate_response: bool = Field(
        default=False,
        description="Generate an AI response to carrier query",
    )


class ClaimListParams(BaseModel):
    """Claim list query parameters."""

    status: ClaimStatus | None = None
    date_from: str | None = None
    date_to: str | None = None
    anomaly_type: str | None = None
    sort_by: str = Field(
        default="created_at",
        pattern="^(created_at|requested_credit|status)$",
    )
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
