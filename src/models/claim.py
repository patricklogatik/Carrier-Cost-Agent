"""Claim and ClaimMessage models."""

import enum
from datetime import datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import DateTime, Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.anomaly import Anomaly


class ClaimStatus(str, enum.Enum):
    """Claim lifecycle status."""

    DRAFT = "draft"
    PENDING_APPROVAL = "pending_approval"
    SUBMITTED = "submitted"
    IN_PROGRESS = "in_progress"
    WON = "won"
    LOST = "lost"
    WITHDRAWN = "withdrawn"


class ClaimOutcome(str, enum.Enum):
    """Claim resolution outcome."""

    APPROVED = "approved"
    DENIED = "denied"
    PARTIAL = "partial"


class MessageDirection(str, enum.Enum):
    """Direction of claim message."""

    OUTBOUND = "outbound"
    INBOUND = "inbound"


class MessageType(str, enum.Enum):
    """Type of claim message."""

    INITIAL_CLAIM = "initial_claim"
    RESPONSE = "response"
    INQUIRY = "inquiry"
    RESOLUTION = "resolution"


class Claim(Base, TimestampMixin):
    """Claim for billing dispute with carrier."""

    __tablename__ = "claims"

    claim_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    anomaly_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("anomalies.anomaly_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    claim_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        unique=True,
        index=True,
        comment="Internal claim reference number",
    )
    status: Mapped[ClaimStatus] = mapped_column(
        Enum(ClaimStatus),
        default=ClaimStatus.DRAFT,
        nullable=False,
        index=True,
    )
    claim_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="Generated claim text for carrier portal",
    )
    claim_subject: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Claim subject line",
    )
    contract_citation: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Relevant contract section citation",
    )
    evidence_references: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="References to supporting documents",
    )
    requested_credit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Amount requested as credit",
    )

    # Workflow dates
    submitted_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    resolution_date: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Resolution
    outcome: Mapped[ClaimOutcome | None] = mapped_column(
        Enum(ClaimOutcome),
        nullable=True,
    )
    credit_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Actual credit received",
    )
    carrier_reference: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        comment="Carrier's claim reference number",
    )
    resolution_notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Approval workflow
    approved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    approved_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Tracking
    created_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    submitted_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Relationships
    anomaly: Mapped["Anomaly"] = relationship("Anomaly", back_populates="claims")
    messages: Mapped[list["ClaimMessage"]] = relationship(
        "ClaimMessage",
        back_populates="claim",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Claim(number={self.claim_number}, status={self.status})>"


class ClaimMessage(Base, TimestampMixin):
    """Message in claim conversation with carrier."""

    __tablename__ = "claim_messages"

    message_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    claim_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("claims.claim_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    direction: Mapped[MessageDirection] = mapped_column(
        Enum(MessageDirection),
        nullable=False,
    )
    message_type: Mapped[MessageType] = mapped_column(
        Enum(MessageType),
        nullable=False,
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    attachments: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="List of attachment references",
    )
    sender: Mapped[str | None] = mapped_column(String(255), nullable=True)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
    )
    is_auto_generated: Mapped[bool] = mapped_column(
        default=False,
        nullable=False,
        comment="Whether message was generated by AI",
    )

    # Relationships
    claim: Mapped["Claim"] = relationship("Claim", back_populates="messages")

    def __repr__(self) -> str:
        return f"<ClaimMessage(direction={self.direction}, type={self.message_type})>"
