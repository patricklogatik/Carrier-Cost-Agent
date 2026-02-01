"""Invoice API endpoints."""

from datetime import date, datetime, timezone
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.common import PaginatedResponse
from src.api.schemas.invoice import (
    InvoiceDetail,
    InvoiceLineResponse,
    InvoiceResponse,
    InvoiceUploadResponse,
)
from src.core.database import get_db_session
from src.core.logging import get_logger
from src.core.security import UserContext, get_current_user
from src.models.invoice import Invoice, InvoiceLine, ProcessingStatus

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=InvoiceUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Invoice PDF",
    description="Upload a carrier invoice PDF for processing.",
)
async def upload_invoice(
    file: UploadFile = File(..., description="Invoice PDF file (max 50MB)"),
    carrier_id: str = Query(..., description="Carrier ID for this invoice"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> InvoiceUploadResponse:
    """Upload an invoice PDF for processing.

    The invoice will be queued for:
    1. PDF text extraction
    2. Field parsing
    3. Anomaly detection

    Args:
        file: The PDF file to upload.
        carrier_id: The carrier this invoice belongs to.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Upload confirmation with invoice ID and status.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    # Check file size (50MB limit)
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File size exceeds 50MB limit",
        )

    # Create invoice record
    invoice_id = str(uuid4())
    invoice = Invoice(
        invoice_id=invoice_id,
        carrier_id=carrier_id,
        invoice_number=f"PENDING-{invoice_id[:8]}",  # Temporary until parsed
        invoice_date=date.today(),  # Will be updated after parsing
        total_amount=0,  # Will be updated after parsing
        processing_status=ProcessingStatus.PENDING,
    )

    # TODO: Store PDF in object storage and update source_document_path
    # TODO: Queue invoice for processing

    db.add(invoice)
    await db.commit()

    logger.info(
        "Invoice uploaded",
        invoice_id=invoice_id,
        filename=file.filename,
        size_bytes=len(content),
        user_id=user.user_id,
    )

    return InvoiceUploadResponse(
        invoice_id=invoice_id,
        status=ProcessingStatus.PENDING,
        filename=file.filename,
        uploaded_at=datetime.now(timezone.utc),
    )


@router.get(
    "",
    response_model=PaginatedResponse[InvoiceResponse],
    summary="List Invoices",
    description="Retrieve a paginated list of invoices with optional filters.",
)
async def list_invoices(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    carrier_id: str | None = Query(default=None),
    status_filter: ProcessingStatus | None = Query(default=None, alias="status"),
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    sort_by: str = Query(default="invoice_date", pattern="^(invoice_date|total_amount|created_at)$"),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> PaginatedResponse[InvoiceResponse]:
    """List invoices with filtering and pagination.

    Args:
        limit: Maximum number of results.
        offset: Number of results to skip.
        carrier_id: Filter by carrier.
        status_filter: Filter by processing status.
        date_from: Filter invoices from this date.
        date_to: Filter invoices until this date.
        sort_by: Field to sort by.
        sort_order: Sort direction.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Paginated list of invoices.
    """
    # Build query
    query = select(Invoice)

    if carrier_id:
        query = query.where(Invoice.carrier_id == carrier_id)
    if status_filter:
        query = query.where(Invoice.processing_status == status_filter)
    if date_from:
        query = query.where(Invoice.invoice_date >= date_from)
    if date_to:
        query = query.where(Invoice.invoice_date <= date_to)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Invoice, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    invoices = result.scalars().all()

    # Map to response with counts
    items = []
    for inv in invoices:
        # Get line count and anomaly count
        line_count_result = await db.scalar(
            select(func.count()).where(InvoiceLine.invoice_id == inv.invoice_id)
        )
        items.append(
            InvoiceResponse(
                invoice_id=inv.invoice_id,
                carrier_id=inv.carrier_id,
                invoice_number=inv.invoice_number,
                invoice_date=inv.invoice_date,
                due_date=inv.due_date,
                total_amount=inv.total_amount,
                currency=inv.currency,
                source_type=inv.source_type,
                processing_status=inv.processing_status,
                line_count=line_count_result or 0,
                anomaly_count=0,  # TODO: Count anomalies
                created_at=inv.created_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{invoice_id}",
    response_model=InvoiceDetail,
    summary="Get Invoice Detail",
    description="Retrieve detailed invoice information including line items.",
)
async def get_invoice(
    invoice_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> InvoiceDetail:
    """Get detailed invoice information.

    Args:
        invoice_id: The invoice ID.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Detailed invoice with line items.
    """
    result = await db.execute(
        select(Invoice)
        .options(selectinload(Invoice.lines))
        .where(Invoice.invoice_id == invoice_id)
    )
    invoice = result.scalar_one_or_none()

    if not invoice:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Invoice {invoice_id} not found",
        )

    # Map lines to response
    lines = [
        InvoiceLineResponse(
            line_id=line.line_id,
            line_number=line.line_number,
            pro_number=line.pro_number,
            tracking_number=line.tracking_number,
            reference_number=line.reference_number,
            service_level=line.service_level,
            charge_type=line.charge_type,
            charge_description=line.charge_description,
            amount=line.amount,
            weight=line.weight,
            billed_weight=line.billed_weight,
            zone=line.zone,
            origin_zip=line.origin_zip,
            destination_zip=line.destination_zip,
            ship_date=line.ship_date,
            delivery_date=line.delivery_date,
            shipment_id=line.shipment_id,
            anomaly_count=0,  # TODO: Count anomalies
        )
        for line in invoice.lines
    ]

    return InvoiceDetail(
        invoice_id=invoice.invoice_id,
        carrier_id=invoice.carrier_id,
        invoice_number=invoice.invoice_number,
        invoice_date=invoice.invoice_date,
        due_date=invoice.due_date,
        total_amount=invoice.total_amount,
        currency=invoice.currency,
        source_type=invoice.source_type,
        processing_status=invoice.processing_status,
        line_count=len(lines),
        anomaly_count=0,
        created_at=invoice.created_at,
        source_document_url=invoice.source_document_path,
        account_number=invoice.account_number,
        billing_period_start=invoice.billing_period_start,
        billing_period_end=invoice.billing_period_end,
        processing_error=invoice.processing_error,
        lines=lines,
    )
