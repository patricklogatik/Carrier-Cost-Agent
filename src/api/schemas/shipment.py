"""Shipment-related schemas."""

from datetime import date, datetime
from decimal import Decimal
from typing import Any

from pydantic import BaseModel, Field


class AddressSchema(BaseModel):
    """Address structure."""

    name: str | None = None
    street: str | None = None
    city: str | None = None
    state: str | None = None
    zip: str | None = None
    country: str = "US"


class DimensionsSchema(BaseModel):
    """Package dimensions."""

    length: Decimal | None = None
    width: Decimal | None = None
    height: Decimal | None = None
    unit: str = "in"


class ShipmentCreate(BaseModel):
    """Shipment creation/update request."""

    carrier_id: str
    pro_number: str | None = None
    tracking_number: str | None = None
    reference_number: str | None = None
    order_number: str | None = None
    origin_address: AddressSchema | None = None
    origin_zip: str | None = None
    destination_address: AddressSchema | None = None
    destination_zip: str | None = None
    service_level: str | None = None
    package_type: str | None = None
    ship_date: date | None = None
    expected_delivery: date | None = None
    actual_delivery: date | None = None
    weight: Decimal | None = None
    weight_unit: str = "lbs"
    dimensions: DimensionsSchema | None = None
    dim_weight: Decimal | None = None
    quoted_amount: Decimal | None = None
    zone: str | None = None
    status: str | None = None
    delivery_signature: str | None = None
    source_system: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] | None = None


class ShipmentResponse(BaseModel):
    """Shipment response."""

    shipment_id: str
    carrier_id: str
    pro_number: str | None = None
    tracking_number: str | None = None
    reference_number: str | None = None
    order_number: str | None = None
    origin_zip: str | None = None
    destination_zip: str | None = None
    service_level: str | None = None
    ship_date: date | None = None
    expected_delivery: date | None = None
    actual_delivery: date | None = None
    weight: Decimal | None = None
    zone: str | None = None
    status: str | None = None
    source_system: str | None = None
    created_at: datetime

    class Config:
        from_attributes = True


class ShipmentDetail(ShipmentResponse):
    """Detailed shipment response."""

    origin_address: dict[str, Any] | None = None
    destination_address: dict[str, Any] | None = None
    package_type: str | None = None
    weight_unit: str = "lbs"
    dimensions: dict[str, Any] | None = None
    dim_weight: Decimal | None = None
    quoted_amount: Decimal | None = None
    delivery_signature: str | None = None
    external_id: str | None = None
    metadata: dict[str, Any] | None = None
    invoice_line_count: int = 0


class ShipmentImportRequest(BaseModel):
    """Bulk shipment import request."""

    shipments: list[ShipmentCreate]
    update_existing: bool = Field(
        default=True,
        description="Update existing shipments by pro_number/tracking_number if found",
    )


class ShipmentImportResponse(BaseModel):
    """Bulk shipment import response."""

    total: int = Field(description="Total shipments in request")
    created: int = Field(description="New shipments created")
    updated: int = Field(description="Existing shipments updated")
    errors: int = Field(description="Shipments with errors")
    error_details: list[dict[str, Any]] = Field(
        default_factory=list,
        description="Details of any errors encountered",
    )


class ShipmentListParams(BaseModel):
    """Shipment list query parameters."""

    carrier_id: str | None = None
    date_from: date | None = None
    date_to: date | None = None
    status: str | None = None
    service_level: str | None = None
    sort_by: str = Field(default="ship_date", pattern="^(ship_date|created_at)$")
    sort_order: str = Field(default="desc", pattern="^(asc|desc)$")
