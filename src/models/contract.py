"""Contract and ContractTerm models."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
    Boolean,
    Date,
    Enum,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.anomaly import Anomaly
    from src.models.carrier import Carrier


class ParsingStatus(str, enum.Enum):
    """Contract parsing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class TermType(str, enum.Enum):
    """Contract term types."""

    RATE = "rate"
    SURCHARGE = "surcharge"
    DISCOUNT = "discount"
    SLA = "sla"
    EXCEPTION = "exception"


class Contract(Base, TimestampMixin):
    """Carrier contract entity."""

    __tablename__ = "contracts"

    contract_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    carrier_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("carriers.carrier_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    contract_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    effective_date: Mapped[date] = mapped_column(Date, nullable=False)
    expiration_date: Mapped[date] = mapped_column(Date, nullable=False)
    source_document_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to stored PDF in object storage",
    )
    parsing_status: Mapped[ParsingStatus] = mapped_column(
        Enum(ParsingStatus),
        default=ParsingStatus.PENDING,
        nullable=False,
    )
    parsing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, default=1, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="contracts")
    terms: Mapped[list["ContractTerm"]] = relationship(
        "ContractTerm",
        back_populates="contract",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Contract(number={self.contract_number}, carrier_id={self.carrier_id})>"


class ContractTerm(Base, TimestampMixin):
    """Individual term extracted from a contract."""

    __tablename__ = "contract_terms"

    term_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    contract_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("contracts.contract_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    term_type: Mapped[TermType] = mapped_column(
        Enum(TermType),
        nullable=False,
        index=True,
    )
    service_level: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Service level (e.g., Ground, Express, Priority)",
    )
    zone: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        index=True,
    )
    weight_min: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    weight_max: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    rate: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 4),
        nullable=True,
        comment="Rate amount",
    )
    rate_type: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Rate type (per_lb, flat, percentage)",
    )
    conditions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional conditions as JSON",
    )
    source_page: Mapped[int | None] = mapped_column(
        Integer,
        nullable=True,
        comment="Page number in source PDF",
    )
    source_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Original text from contract",
    )
    confidence_score: Mapped[Decimal | None] = mapped_column(
        Numeric(5, 4),
        nullable=True,
        comment="AI extraction confidence (0-1)",
    )
    validated: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
        comment="Whether term has been human-validated",
    )
    validated_by: Mapped[str | None] = mapped_column(String(255), nullable=True)
    validated_at: Mapped[datetime | None] = mapped_column(
        nullable=True,
    )

    # Relationships
    contract: Mapped["Contract"] = relationship("Contract", back_populates="terms")
    anomalies: Mapped[list["Anomaly"]] = relationship(
        "Anomaly",
        back_populates="contract_term",
    )

    def __repr__(self) -> str:
        return f"<ContractTerm(type={self.term_type}, service={self.service_level})>"
