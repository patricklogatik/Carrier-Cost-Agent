"""Shipment API endpoints."""

from datetime import date
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.common import PaginatedResponse
from src.api.schemas.shipment import (
    ShipmentCreate,
    ShipmentDetail,
    ShipmentImportRequest,
    ShipmentImportResponse,
    ShipmentResponse,
)
from src.core.database import get_db_session
from src.core.logging import get_logger
from src.core.security import UserContext, get_current_user
from src.models.shipment import Shipment

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "/import",
    response_model=ShipmentImportResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Import Shipments",
    description="Bulk import shipments from TMS/WMS data.",
)
async def import_shipments(
    request: ShipmentImportRequest,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ShipmentImportResponse:
    """Bulk import shipments.

    Supports upsert logic - existing shipments (matched by pro_number or
    tracking_number) can be updated if update_existing is True.

    Args:
        request: Import request with shipment data.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Import summary with counts and any errors.
    """
    created = 0
    updated = 0
    errors = 0
    error_details: list[dict[str, Any]] = []

    for idx, shipment_data in enumerate(request.shipments):
        try:
            # Try to find existing shipment
            existing = None
            if request.update_existing:
                query = select(Shipment).where(
                    Shipment.carrier_id == shipment_data.carrier_id
                )
                if shipment_data.pro_number:
                    query = query.where(Shipment.pro_number == shipment_data.pro_number)
                elif shipment_data.tracking_number:
                    query = query.where(
                        Shipment.tracking_number == shipment_data.tracking_number
                    )

                result = await db.execute(query)
                existing = result.scalar_one_or_none()

            if existing:
                # Update existing
                for field, value in shipment_data.model_dump(exclude_unset=True).items():
                    if value is not None:
                        setattr(existing, field, value)
                updated += 1
            else:
                # Create new
                shipment = Shipment(
                    shipment_id=str(uuid4()),
                    **shipment_data.model_dump(),
                )
                db.add(shipment)
                created += 1

        except Exception as e:
            errors += 1
            error_details.append({
                "index": idx,
                "pro_number": shipment_data.pro_number,
                "tracking_number": shipment_data.tracking_number,
                "error": str(e),
            })
            logger.warning(
                "Shipment import error",
                index=idx,
                error=str(e),
            )

    await db.commit()

    logger.info(
        "Shipment import completed",
        total=len(request.shipments),
        created=created,
        updated=updated,
        errors=errors,
        user_id=user.user_id,
    )

    return ShipmentImportResponse(
        total=len(request.shipments),
        created=created,
        updated=updated,
        errors=errors,
        error_details=error_details,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ShipmentResponse],
    summary="List Shipments",
    description="Retrieve a paginated list of shipments with optional filters.",
)
async def list_shipments(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    carrier_id: str | None = Query(default=None),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    service_level: str | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    search: str | None = Query(
        default=None,
        description="Search by PRO number, tracking number, or reference",
    ),
    sort_by: str = Query(default="ship_date", pattern="^(ship_date|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> PaginatedResponse[ShipmentResponse]:
    """List shipments with filtering and pagination.

    Args:
        limit: Maximum number of results.
        offset: Number of results to skip.
        carrier_id: Filter by carrier.
        date_from: Filter shipments from this date.
        date_to: Filter shipments until this date.
        service_level: Filter by service level.
        status_filter: Filter by shipment status.
        search: Search term for PRO/tracking/reference.
        sort_by: Field to sort by.
        sort_order: Sort direction.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Paginated list of shipments.
    """
    query = select(Shipment)

    if carrier_id:
        query = query.where(Shipment.carrier_id == carrier_id)
    if date_from:
        query = query.where(Shipment.ship_date >= date_from)
    if date_to:
        query = query.where(Shipment.ship_date <= date_to)
    if service_level:
        query = query.where(Shipment.service_level == service_level)
    if status_filter:
        query = query.where(Shipment.status == status_filter)
    if search:
        query = query.where(
            or_(
                Shipment.pro_number.ilike(f"%{search}%"),
                Shipment.tracking_number.ilike(f"%{search}%"),
                Shipment.reference_number.ilike(f"%{search}%"),
            )
        )

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Shipment, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    shipments = result.scalars().all()

    items = [
        ShipmentResponse(
            shipment_id=s.shipment_id,
            carrier_id=s.carrier_id,
            pro_number=s.pro_number,
            tracking_number=s.tracking_number,
            reference_number=s.reference_number,
            order_number=s.order_number,
            origin_zip=s.origin_zip,
            destination_zip=s.destination_zip,
            service_level=s.service_level,
            ship_date=s.ship_date,
            expected_delivery=s.expected_delivery,
            actual_delivery=s.actual_delivery,
            weight=s.weight,
            zone=s.zone,
            status=s.status,
            source_system=s.source_system,
            created_at=s.created_at,
        )
        for s in shipments
    ]

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{shipment_id}",
    response_model=ShipmentDetail,
    summary="Get Shipment Detail",
    description="Retrieve detailed shipment information.",
)
async def get_shipment(
    shipment_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ShipmentDetail:
    """Get detailed shipment information.

    Args:
        shipment_id: The shipment ID.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Detailed shipment information.
    """
    result = await db.execute(
        select(Shipment).where(Shipment.shipment_id == shipment_id)
    )
    shipment = result.scalar_one_or_none()

    if not shipment:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Shipment {shipment_id} not found",
        )

    return ShipmentDetail(
        shipment_id=shipment.shipment_id,
        carrier_id=shipment.carrier_id,
        pro_number=shipment.pro_number,
        tracking_number=shipment.tracking_number,
        reference_number=shipment.reference_number,
        order_number=shipment.order_number,
        origin_zip=shipment.origin_zip,
        destination_zip=shipment.destination_zip,
        origin_address=shipment.origin_address,
        destination_address=shipment.destination_address,
        service_level=shipment.service_level,
        package_type=shipment.package_type,
        ship_date=shipment.ship_date,
        expected_delivery=shipment.expected_delivery,
        actual_delivery=shipment.actual_delivery,
        weight=shipment.weight,
        weight_unit=shipment.weight_unit,
        dimensions=shipment.dimensions,
        dim_weight=shipment.dim_weight,
        quoted_amount=shipment.quoted_amount,
        zone=shipment.zone,
        status=shipment.status,
        delivery_signature=shipment.delivery_signature,
        source_system=shipment.source_system,
        external_id=shipment.external_id,
        metadata=shipment.metadata,
        created_at=shipment.created_at,
        invoice_line_count=0,  # TODO: Count linked invoice lines
    )
