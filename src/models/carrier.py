"""Carrier model."""

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from sqlalchemy import String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from src.models.base import Base, TimestampMixin

if TYPE_CHECKING:
    from src.models.contract import Contract
    from src.models.invoice import Invoice
    from src.models.shipment import Shipment


class Carrier(Base, TimestampMixin):
    """Carrier entity representing shipping carriers like FedEx, UPS, etc."""

    __tablename__ = "carriers"

    carrier_id: Mapped[str] = mapped_column(
        UUID(as_uuid=False),
        primary_key=True,
        default=lambda: str(uuid4()),
    )
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    code: Mapped[str] = mapped_column(
        String(10),
        nullable=False,
        unique=True,
        index=True,
        comment="Carrier code (e.g., FEDX, UPS, DHL)",
    )
    portal_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    contact_email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)

    # Relationships
    contracts: Mapped[list["Contract"]] = relationship(
        "Contract",
        back_populates="carrier",
        cascade="all, delete-orphan",
    )
    invoices: Mapped[list["Invoice"]] = relationship(
        "Invoice",
        back_populates="carrier",
        cascade="all, delete-orphan",
    )
    shipments: Mapped[list["Shipment"]] = relationship(
        "Shipment",
        back_populates="carrier",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Carrier(code={self.code}, name={self.name})>"
