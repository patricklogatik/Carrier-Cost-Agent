"""Shipment model."""

from datetime import date
from decimal import Decimal
from typing import TYPE_CHECKING, Any
from uuid import uuid4

from sqlalchemy import Date, ForeignKey, Numeric, String
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.carrier import Carrier
    from src.models.invoice import InvoiceLine


class Shipment(Base, TimestampMixin):
    """Shipment data from TMS/WMS systems."""

    __tablename__ = "shipments"

    shipment_id: Mapped[str] = mapped_column(
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
        comment="Customer reference number",
    )
    order_number: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )

    # Origin address
    origin_address: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Origin address {name, street, city, state, zip, country}",
    )
    origin_zip: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # Destination address
    destination_address: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Destination address {name, street, city, state, zip, country}",
    )
    destination_zip: Mapped[str | None] = mapped_column(
        String(20),
        nullable=True,
        index=True,
    )

    # Service details
    service_level: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
    )
    package_type: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Dates
    ship_date: Mapped[date | None] = mapped_column(Date, nullable=True, index=True)
    expected_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)
    actual_delivery: Mapped[date | None] = mapped_column(Date, nullable=True)

    # Weight and dimensions
    weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Actual weight in lbs",
    )
    weight_unit: Mapped[str] = mapped_column(
        String(10),
        default="lbs",
        nullable=False,
    )
    dimensions: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Package dimensions {length, width, height, unit}",
    )
    dim_weight: Mapped[Decimal | None] = mapped_column(
        Numeric(10, 2),
        nullable=True,
        comment="Dimensional weight",
    )

    # Billing
    quoted_amount: Mapped[Decimal | None] = mapped_column(
        Numeric(12, 2),
        nullable=True,
        comment="Amount quoted by carrier",
    )
    zone: Mapped[str | None] = mapped_column(String(50), nullable=True)

    # Status
    status: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Shipment status (delivered, in_transit, cancelled, etc.)",
    )
    delivery_signature: Mapped[str | None] = mapped_column(String(255), nullable=True)

    # Source system
    source_system: Mapped[str | None] = mapped_column(
        String(50),
        nullable=True,
        comment="Source system (TMS, WMS, ERP)",
    )
    external_id: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
        index=True,
        comment="ID from source system",
    )

    # Additional data
    metadata: Mapped[dict[str, Any] | None] = mapped_column(
        JSONB,
        nullable=True,
        comment="Additional metadata from source system",
    )

    # Relationships
    carrier: Mapped["Carrier"] = relationship("Carrier", back_populates="shipments")
    invoice_lines: Mapped[list["InvoiceLine"]] = relationship(
        "InvoiceLine",
        back_populates="shipment",
    )

    def __repr__(self) -> str:
        return f"<Shipment(pro={self.pro_number}, tracking={self.tracking_number})>"
