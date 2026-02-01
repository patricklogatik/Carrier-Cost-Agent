"""Anomaly model."""

import enum
from decimal import Decimal
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import Enum, ForeignKey, Numeric, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.claim import Claim
    from src.models.contract import ContractTerm
    from src.models.invoice import InvoiceLine


class AnomalyType(str, enum.Enum):
    """Types of billing anomalies."""

    DUPLICATE = "duplicate"
    RATE_ERROR = "rate_error"
    LATE_DELIVERY = "late_delivery"
    UNAUTHORIZED_SURCHARGE = "unauthorized_surcharge"
    WEIGHT_DISCREPANCY = "weight_discrepancy"
    ADDRESS_CORRECTION = "address_correction"
    SERVICE_FAILURE = "service_failure"


class AnomalyStatus(str, enum.Enum):
    """Anomaly lifecycle status."""

    DETECTED = "detected"
    VALIDATED = "validated"
    DISMISSED = "dismissed"
    DISPUTED = "disputed"
    RESOLVED = "resolved"


class Anomaly(Base, TimestampMixin):
    """Detected billing anomaly."""

    __tablename__ = "anomalies"

    anomaly_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    line_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("invoice_lines.line_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    anomaly_type: Mapped[AnomalyType] = mapped_column(
        Enum(AnomalyType),
        nullable=False,
        index=True,
    )
    expected_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Expected charge based on contract/shipment data",
    )
    actual_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Actual charged amount on invoice",
    )
    variance: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
        comment="Difference between actual and expected",
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(5, 4),
        nullable=False,
        comment="Detection confidence (0-1)",
    )
    contract_reference: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
        comment="Human-readable contract reference",
    )
    contract_term_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("contract_terms.term_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    detection_rule: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Name of the detection rule that found this",
    )
    status: Mapped[AnomalyStatus] = mapped_column(
        Enum(AnomalyStatus),
        default=AnomalyStatus.DETECTED,
        nullable=False,
        index=True,
    )
    description: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Human-readable description of the anomaly",
    )
    evidence: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Supporting evidence for the anomaly",
    )
    resolution_notes: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )
    resolved_by: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # For duplicate detection: reference to original charge
    duplicate_of_line_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("invoice_lines.line_id", ondelete="SET NULL"),
        nullable=True,
    )

    # Relationships
    invoice_line: Mapped["InvoiceLine"] = relationship(
        "InvoiceLine",
        back_populates="anomalies",
        foreign_keys=[line_id],
    )
    contract_term: Mapped["ContractTerm | None"] = relationship(
        "ContractTerm",
        back_populates="anomalies",
    )
    duplicate_of: Mapped["InvoiceLine | None"] = relationship(
        "InvoiceLine",
        foreign_keys=[duplicate_of_line_id],
    )
    claims: Mapped[list["Claim"]] = relationship(
        "Claim",
        back_populates="anomaly",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Anomaly(type={self.anomaly_type}, variance={self.variance})>"
