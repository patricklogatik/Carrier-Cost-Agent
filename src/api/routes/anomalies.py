"""Anomaly API endpoints."""

from datetime import datetime
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.anomaly import (
    AnomalyDetail,
    AnomalyResponse,
    AnomalyStatusUpdate,
    ContractTermContext,
    InvoiceLineContext,
    ShipmentContext,
)
from src.api.schemas.common import PaginatedResponse
from src.core.database import get_db_session
from src.core.logging import get_logger
from src.core.security import UserContext, get_current_user
from src.models.anomaly import Anomaly, AnomalyStatus, AnomalyType
from src.models.claim import Claim
from src.models.invoice import Invoice, InvoiceLine

logger = get_logger(__name__)
router = APIRouter()


@router.get(
    "",
    response_model=PaginatedResponse[AnomalyResponse],
    summary="List Anomalies",
    description="Retrieve a paginated list of detected anomalies.",
)
async def list_anomalies(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: AnomalyStatus | None = Query(default=None, alias="status"),
    anomaly_type: AnomalyType | None = Query(default=None),
    confidence_min: float | None = Query(default=None, ge=0, le=1),
    invoice_id: str | None = Query(default=None),
    sort_by: str = Query(
        default="variance",
        pattern="^(variance|confidence_score|created_at)$",
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> PaginatedResponse[AnomalyResponse]:
    """List anomalies with filtering and pagination.

    Args:
        limit: Maximum number of results.
        offset: Number of results to skip.
        status_filter: Filter by anomaly status.
        anomaly_type: Filter by anomaly type.
        confidence_min: Minimum confidence score.
        invoice_id: Filter by invoice.
        sort_by: Field to sort by.
        sort_order: Sort direction.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Paginated list of anomalies.
    """
    # Build query with joins
    query = (
        select(Anomaly)
        .join(InvoiceLine, Anomaly.line_id == InvoiceLine.line_id)
        .join(Invoice, InvoiceLine.invoice_id == Invoice.invoice_id)
    )

    if status_filter:
        query = query.where(Anomaly.status == status_filter)
    if anomaly_type:
        query = query.where(Anomaly.anomaly_type == anomaly_type)
    if confidence_min is not None:
        query = query.where(Anomaly.confidence_score >= Decimal(str(confidence_min)))
    if invoice_id:
        query = query.where(Invoice.invoice_id == invoice_id)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Anomaly, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    result = await db.execute(query.options(selectinload(Anomaly.invoice_line)))
    anomalies = result.scalars().all()

    items = []
    for a in anomalies:
        # Check if has claim
        claim_result = await db.execute(
            select(func.count()).where(Claim.anomaly_id == a.anomaly_id)
        )
        has_claim = (claim_result.scalar() or 0) > 0

        # Get invoice number
        line_result = await db.execute(
            select(Invoice.invoice_number)
            .join(InvoiceLine, Invoice.invoice_id == InvoiceLine.invoice_id)
            .where(InvoiceLine.line_id == a.line_id)
        )
        invoice_number = line_result.scalar()

        items.append(
            AnomalyResponse(
                anomaly_id=a.anomaly_id,
                line_id=a.line_id,
                anomaly_type=a.anomaly_type,
                expected_amount=a.expected_amount,
                actual_amount=a.actual_amount,
                variance=a.variance,
                confidence_score=a.confidence_score,
                detection_rule=a.detection_rule,
                status=a.status,
                description=a.description,
                created_at=a.created_at,
                invoice_number=invoice_number,
                pro_number=a.invoice_line.pro_number if a.invoice_line else None,
                has_claim=has_claim,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{anomaly_id}",
    response_model=AnomalyDetail,
    summary="Get Anomaly Detail",
    description="Retrieve detailed anomaly information with context.",
)
async def get_anomaly(
    anomaly_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> AnomalyDetail:
    """Get detailed anomaly information.

    Args:
        anomaly_id: The anomaly ID.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Detailed anomaly with related context.
    """
    result = await db.execute(
        select(Anomaly)
        .options(
            selectinload(Anomaly.invoice_line).selectinload(InvoiceLine.invoice),
            selectinload(Anomaly.invoice_line).selectinload(InvoiceLine.shipment),
            selectinload(Anomaly.contract_term),
        )
        .where(Anomaly.anomaly_id == anomaly_id)
    )
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found",
        )

    # Check if has claim
    claim_result = await db.execute(
        select(func.count()).where(Claim.anomaly_id == anomaly.anomaly_id)
    )
    has_claim = (claim_result.scalar() or 0) > 0

    # Build context objects
    invoice_line = anomaly.invoice_line
    invoice_line_context = None
    invoice_number = None

    if invoice_line:
        invoice_number = invoice_line.invoice.invoice_number if invoice_line.invoice else None
        invoice_line_context = InvoiceLineContext(
            line_id=invoice_line.line_id,
            invoice_id=invoice_line.invoice_id,
            invoice_number=invoice_number or "",
            pro_number=invoice_line.pro_number,
            tracking_number=invoice_line.tracking_number,
            charge_type=invoice_line.charge_type,
            amount=invoice_line.amount,
        )

    shipment_context = None
    if invoice_line and invoice_line.shipment:
        s = invoice_line.shipment
        shipment_context = ShipmentContext(
            shipment_id=s.shipment_id,
            pro_number=s.pro_number,
            tracking_number=s.tracking_number,
            service_level=s.service_level,
            ship_date=str(s.ship_date) if s.ship_date else None,
            expected_delivery=str(s.expected_delivery) if s.expected_delivery else None,
            actual_delivery=str(s.actual_delivery) if s.actual_delivery else None,
        )

    contract_term_context = None
    if anomaly.contract_term:
        t = anomaly.contract_term
        contract_term_context = ContractTermContext(
            term_id=t.term_id,
            contract_id=t.contract_id,
            contract_number="",  # Would need another join
            term_type=t.term_type.value,
            rate=t.rate,
            source_text=t.source_text,
            source_page=t.source_page,
        )

    return AnomalyDetail(
        anomaly_id=anomaly.anomaly_id,
        line_id=anomaly.line_id,
        anomaly_type=anomaly.anomaly_type,
        expected_amount=anomaly.expected_amount,
        actual_amount=anomaly.actual_amount,
        variance=anomaly.variance,
        confidence_score=anomaly.confidence_score,
        detection_rule=anomaly.detection_rule,
        status=anomaly.status,
        description=anomaly.description,
        created_at=anomaly.created_at,
        invoice_number=invoice_number,
        pro_number=invoice_line.pro_number if invoice_line else None,
        has_claim=has_claim,
        contract_reference=anomaly.contract_reference,
        contract_term_id=anomaly.contract_term_id,
        evidence=anomaly.evidence,
        resolution_notes=anomaly.resolution_notes,
        resolved_by=anomaly.resolved_by,
        duplicate_of_line_id=anomaly.duplicate_of_line_id,
        invoice_line=invoice_line_context,
        shipment=shipment_context,
        contract_term=contract_term_context,
    )


@router.put(
    "/{anomaly_id}/status",
    response_model=AnomalyResponse,
    summary="Update Anomaly Status",
    description="Update the status of an anomaly.",
)
async def update_anomaly_status(
    anomaly_id: str,
    update: AnomalyStatusUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> AnomalyResponse:
    """Update anomaly status.

    Args:
        anomaly_id: The anomaly ID.
        update: Status update data.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Updated anomaly.
    """
    result = await db.execute(
        select(Anomaly)
        .options(selectinload(Anomaly.invoice_line))
        .where(Anomaly.anomaly_id == anomaly_id)
    )
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {anomaly_id} not found",
        )

    # Update status
    anomaly.status = update.status
    if update.resolution_notes:
        anomaly.resolution_notes = update.resolution_notes

    if update.status == AnomalyStatus.RESOLVED:
        anomaly.resolved_by = user.user_id

    await db.commit()
    await db.refresh(anomaly)

    logger.info(
        "Anomaly status updated",
        anomaly_id=anomaly_id,
        new_status=update.status.value,
        user_id=user.user_id,
    )

    # Get invoice number
    line_result = await db.execute(
        select(Invoice.invoice_number)
        .join(InvoiceLine, Invoice.invoice_id == InvoiceLine.invoice_id)
        .where(InvoiceLine.line_id == anomaly.line_id)
    )
    invoice_number = line_result.scalar()

    # Check if has claim
    claim_result = await db.execute(
        select(func.count()).where(Claim.anomaly_id == anomaly.anomaly_id)
    )
    has_claim = (claim_result.scalar() or 0) > 0

    return AnomalyResponse(
        anomaly_id=anomaly.anomaly_id,
        line_id=anomaly.line_id,
        anomaly_type=anomaly.anomaly_type,
        expected_amount=anomaly.expected_amount,
        actual_amount=anomaly.actual_amount,
        variance=anomaly.variance,
        confidence_score=anomaly.confidence_score,
        detection_rule=anomaly.detection_rule,
        status=anomaly.status,
        description=anomaly.description,
        created_at=anomaly.created_at,
        invoice_number=invoice_number,
        pro_number=anomaly.invoice_line.pro_number if anomaly.invoice_line else None,
        has_claim=has_claim,
    )
