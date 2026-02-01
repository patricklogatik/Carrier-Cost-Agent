"""Invoice and InvoiceLine models."""

import enum
from datetime import date, datetime
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import (
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
    from src.models.shipment import Shipment


class SourceType(str, enum.Enum):
    """Invoice source type."""

    PDF = "pdf"
    EDI = "edi"
    API = "api"


class ProcessingStatus(str, enum.Enum):
    """Invoice processing status."""

    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class Invoice(Base, TimestampMixin):
    """Carrier invoice entity."""

    __tablename__ = "invoices"

    invoice_id: Mapped[str] = mapped_column(
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
    invoice_number: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    invoice_date: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    total_amount: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        nullable=False,
    )
    currency: Mapped[str] = mapped_column(
        String(3),
        default="USD",
        nullable=False,
    )
    source_type: Mapped[SourceType] = mapped_column(
        Enum(SourceType),
        default=SourceType.PDF,
        nullable=False,
    )
    source_document_path: Mapped[str | None] = mapped_column(
        String(500),
        nullable=True,
        comment="Path to stored PDF in object storage",
    )
    processing_status: Mapped[ProcessingStatus] = mapped_column(
        Enum(ProcessingStatus),
        default=ProcessingStatus.PENDING,
        nullable=False,
        index=True,
    )
    processing_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    extracted_text: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
        comment="Raw extracted text for debugging",
    )
    account_number: Mapped[str | None] = mapped_column(String(100), nullable=True)
    billing_period_start: Mapped[date | None] = mapped_column(Date, nullable=True)
    billing_period_end: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="invoices")
    lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="invoice",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Invoice(number={self.invoice_number}, total={self.total_amount})>"


class InvoiceLine(Base, TimestampMixin):
    """Individual line item from an invoice."""

    __tablename__ = "invoice_lines"

    line_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    invoice_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("invoices.invoice_id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    shipment_id: Mapped[str | None] = mapped_column(
        UUID(as_uuid=False),
        ForeignKey("shipments.shipment_id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(Integer, nullable=False)
    pro_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="Progressive number / freight shipment ID",
    )
    tracking_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    reference_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    service_level: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
    charge_type: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        comment="Type of charge (base_rate, fuel_surcharge, residential, etc.)",
    )
    charge_description: Mapped[str | None] = mapped_column(String(500), nullable=True)
    amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )
    billed_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Billed weight (may differ from actual)",
    )
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Package dimensions {length, width, height, unit}",
    )
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)
    origin_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    destination_zip: Mapped[str | None] = mapped_column(String(20), nullable=True)
    ship_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    delivery_date: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Relationships
    invoice: Mapped["Invoice"] = relationship("Invoice", back_populates="lines")
    shipment: Mapped["Shipment | None"] = relationship(
        "Shipment",
        back_populates="invoice_lines",
    )
    anomalies: Mapped[list["Anomaly"]] = relationship(
        "Anomaly",
        back_populates="invoice_line",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<InvoiceLine(pro={self.pro_number}, amount={self.amount})>"
