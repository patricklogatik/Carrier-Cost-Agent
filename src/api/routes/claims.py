"""Claim API endpoints."""

from datetime import datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.claim import (
    ClaimApproval,
    ClaimCreate,
    ClaimDetail,
    ClaimMessageCreate,
    ClaimMessageResponse,
    ClaimResponse,
    ClaimUpdate,
)
from src.api.schemas.common import PaginatedResponse
from src.core.database import get_db_session
from src.core.logging import get_logger
from src.core.security import Roles, UserContext, get_current_user, require_roles
from src.models.anomaly import Anomaly
from src.models.claim import Claim, ClaimMessage, ClaimStatus, MessageDirection, MessageType
from src.models.invoice import Invoice, InvoiceLine

logger = get_logger(__name__)
router = APIRouter()


def generate_claim_number() -> str:
    """Generate a unique claim number."""
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%d")
    unique_part = uuid4().hex[:6].upper()
    return f"CLM-{timestamp}-{unique_part}"


@router.post(
    "",
    response_model=ClaimResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create Claim",
    description="Create a new claim from an anomaly.",
)
async def create_claim(
    request: ClaimCreate,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ClaimResponse:
    """Create a claim from a validated anomaly.

    If claim_text is not provided, it will be auto-generated using GenAI.

    Args:
        request: Claim creation request.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Created claim.
    """
    # Get anomaly
    result = await db.execute(
        select(Anomaly)
        .options(selectinload(Anomaly.invoice_line))
        .where(Anomaly.anomaly_id == request.anomaly_id)
    )
    anomaly = result.scalar_one_or_none()

    if not anomaly:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Anomaly {request.anomaly_id} not found",
        )

    # Check if claim already exists
    existing = await db.execute(
        select(Claim).where(Claim.anomaly_id == request.anomaly_id)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Claim already exists for this anomaly",
        )

    # Generate claim text if not provided
    claim_text = request.claim_text
    if not claim_text or request.regenerate:
        # TODO: Call GenAI service to generate claim text
        claim_text = f"""Claim for {anomaly.anomaly_type.value} Overcharge

We have identified a billing discrepancy on the attached invoice that requires your attention and credit.

Invoice Details:
- Charge Amount: ${anomaly.actual_amount:.2f}
- Expected Amount: ${anomaly.expected_amount:.2f if anomaly.expected_amount else 'N/A'}
- Variance: ${anomaly.variance:.2f}

This charge appears to be a {anomaly.anomaly_type.value.replace('_', ' ')} based on our analysis of the shipment data and contract terms.

We request a credit of ${anomaly.variance:.2f} for this discrepancy.

Please review and process this claim at your earliest convenience.
"""

    # Create claim
    claim = Claim(
        claim_id=str(uuid4()),
        anomaly_id=request.anomaly_id,
        claim_number=generate_claim_number(),
        status=ClaimStatus.DRAFT,
        claim_text=claim_text,
        claim_subject=request.claim_subject or f"Billing Dispute: {anomaly.anomaly_type.value}",
        requested_credit=anomaly.variance,
        created_by=user.user_id,
    )

    db.add(claim)
    await db.commit()
    await db.refresh(claim)

    logger.info(
        "Claim created",
        claim_id=claim.claim_id,
        claim_number=claim.claim_number,
        anomaly_id=request.anomaly_id,
        user_id=user.user_id,
    )

    return ClaimResponse(
        claim_id=claim.claim_id,
        anomaly_id=claim.anomaly_id,
        claim_number=claim.claim_number,
        status=claim.status,
        requested_credit=claim.requested_credit,
        outcome=claim.outcome,
        credit_amount=claim.credit_amount,
        submitted_date=claim.submitted_date,
        resolution_date=claim.resolution_date,
        created_at=claim.created_at,
        anomaly_type=anomaly.anomaly_type.value,
        invoice_number=None,  # Would need join
        variance=anomaly.variance,
        message_count=0,
    )


@router.get(
    "",
    response_model=PaginatedResponse[ClaimResponse],
    summary="List Claims",
    description="Retrieve a paginated list of claims.",
)
async def list_claims(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    status_filter: ClaimStatus | None = Query(default=None, alias="status"),
    sort_by: str = Query(
        default="created_at",
        pattern="^(created_at|requested_credit|status)$",
    ),
    sort_order: str = Query(default="desc", pattern="^(asc|desc)$"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> PaginatedResponse[ClaimResponse]:
    """List claims with filtering and pagination.

    Args:
        limit: Maximum number of results.
        offset: Number of results to skip.
        status_filter: Filter by claim status.
        sort_by: Field to sort by.
        sort_order: Sort direction.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Paginated list of claims.
    """
    query = select(Claim).options(selectinload(Claim.anomaly))

    if status_filter:
        query = query.where(Claim.status == status_filter)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply sorting
    sort_column = getattr(Claim, sort_by)
    if sort_order == "desc":
        query = query.order_by(sort_column.desc())
    else:
        query = query.order_by(sort_column.asc())

    # Apply pagination
    query = query.offset(offset).limit(limit)

    result = await db.execute(query)
    claims = result.scalars().all()

    items = []
    for c in claims:
        # Count messages
        msg_count = await db.scalar(
            select(func.count()).where(ClaimMessage.claim_id == c.claim_id)
        )

        items.append(
            ClaimResponse(
                claim_id=c.claim_id,
                anomaly_id=c.anomaly_id,
                claim_number=c.claim_number,
                status=c.status,
                requested_credit=c.requested_credit,
                outcome=c.outcome,
                credit_amount=c.credit_amount,
                submitted_date=c.submitted_date,
                resolution_date=c.resolution_date,
                created_at=c.created_at,
                anomaly_type=c.anomaly.anomaly_type.value if c.anomaly else None,
                invoice_number=None,
                variance=c.anomaly.variance if c.anomaly else None,
                message_count=msg_count or 0,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/{claim_id}",
    response_model=ClaimDetail,
    summary="Get Claim Detail",
    description="Retrieve detailed claim information.",
)
async def get_claim(
    claim_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ClaimDetail:
    """Get detailed claim information.

    Args:
        claim_id: The claim ID.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Detailed claim with messages.
    """
    result = await db.execute(
        select(Claim)
        .options(
            selectinload(Claim.anomaly),
            selectinload(Claim.messages),
        )
        .where(Claim.claim_id == claim_id)
    )
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    messages = [
        ClaimMessageResponse(
            message_id=m.message_id,
            claim_id=m.claim_id,
            direction=m.direction,
            message_type=m.message_type,
            content=m.content,
            attachments=m.attachments,
            sender=m.sender,
            timestamp=m.timestamp,
            is_auto_generated=m.is_auto_generated,
        )
        for m in claim.messages
    ]

    return ClaimDetail(
        claim_id=claim.claim_id,
        anomaly_id=claim.anomaly_id,
        claim_number=claim.claim_number,
        status=claim.status,
        requested_credit=claim.requested_credit,
        outcome=claim.outcome,
        credit_amount=claim.credit_amount,
        submitted_date=claim.submitted_date,
        resolution_date=claim.resolution_date,
        created_at=claim.created_at,
        anomaly_type=claim.anomaly.anomaly_type.value if claim.anomaly else None,
        invoice_number=None,
        variance=claim.anomaly.variance if claim.anomaly else None,
        message_count=len(messages),
        claim_text=claim.claim_text,
        claim_subject=claim.claim_subject,
        contract_citation=claim.contract_citation,
        evidence_references=claim.evidence_references,
        carrier_reference=claim.carrier_reference,
        resolution_notes=claim.resolution_notes,
        approved_by=claim.approved_by,
        approved_at=claim.approved_at,
        rejection_reason=claim.rejection_reason,
        created_by=claim.created_by,
        submitted_by=claim.submitted_by,
        messages=messages,
    )


@router.put(
    "/{claim_id}",
    response_model=ClaimResponse,
    summary="Update Claim",
    description="Update claim details.",
)
async def update_claim(
    claim_id: str,
    update: ClaimUpdate,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ClaimResponse:
    """Update claim details.

    Args:
        claim_id: The claim ID.
        update: Update data.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Updated claim.
    """
    result = await db.execute(
        select(Claim)
        .options(selectinload(Claim.anomaly))
        .where(Claim.claim_id == claim_id)
    )
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    # Update fields
    if update.claim_text is not None:
        claim.claim_text = update.claim_text
    if update.claim_subject is not None:
        claim.claim_subject = update.claim_subject
    if update.contract_citation is not None:
        claim.contract_citation = update.contract_citation
    if update.status is not None:
        claim.status = update.status
        if update.status == ClaimStatus.SUBMITTED:
            claim.submitted_date = datetime.now(timezone.utc)
            claim.submitted_by = user.user_id
    if update.outcome is not None:
        claim.outcome = update.outcome
        claim.resolution_date = datetime.now(timezone.utc)
    if update.credit_amount is not None:
        claim.credit_amount = update.credit_amount
    if update.carrier_reference is not None:
        claim.carrier_reference = update.carrier_reference
    if update.resolution_notes is not None:
        claim.resolution_notes = update.resolution_notes

    await db.commit()
    await db.refresh(claim)

    logger.info(
        "Claim updated",
        claim_id=claim_id,
        user_id=user.user_id,
    )

    msg_count = await db.scalar(
        select(func.count()).where(ClaimMessage.claim_id == claim.claim_id)
    )

    return ClaimResponse(
        claim_id=claim.claim_id,
        anomaly_id=claim.anomaly_id,
        claim_number=claim.claim_number,
        status=claim.status,
        requested_credit=claim.requested_credit,
        outcome=claim.outcome,
        credit_amount=claim.credit_amount,
        submitted_date=claim.submitted_date,
        resolution_date=claim.resolution_date,
        created_at=claim.created_at,
        anomaly_type=claim.anomaly.anomaly_type.value if claim.anomaly else None,
        invoice_number=None,
        variance=claim.anomaly.variance if claim.anomaly else None,
        message_count=msg_count or 0,
    )


@router.post(
    "/{claim_id}/approve",
    response_model=ClaimResponse,
    summary="Approve Claim",
    description="Approve a claim for submission.",
)
async def approve_claim(
    claim_id: str,
    approval: ClaimApproval,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_roles(Roles.APPROVER, Roles.ADMINISTRATOR)),
) -> ClaimResponse:
    """Approve or reject a claim.

    Args:
        claim_id: The claim ID.
        approval: Approval decision.
        db: Database session.
        user: Current authenticated user (must be Approver or Admin).

    Returns:
        Updated claim.
    """
    result = await db.execute(
        select(Claim)
        .options(selectinload(Claim.anomaly))
        .where(Claim.claim_id == claim_id)
    )
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    if claim.status != ClaimStatus.PENDING_APPROVAL:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Claim is not pending approval",
        )

    if approval.approved:
        claim.status = ClaimStatus.SUBMITTED
        claim.submitted_date = datetime.now(timezone.utc)
        claim.submitted_by = user.user_id
    else:
        claim.status = ClaimStatus.DRAFT
        claim.rejection_reason = approval.comments

    claim.approved_by = user.user_id
    claim.approved_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(claim)

    logger.info(
        "Claim approval processed",
        claim_id=claim_id,
        approved=approval.approved,
        user_id=user.user_id,
    )

    msg_count = await db.scalar(
        select(func.count()).where(ClaimMessage.claim_id == claim.claim_id)
    )

    return ClaimResponse(
        claim_id=claim.claim_id,
        anomaly_id=claim.anomaly_id,
        claim_number=claim.claim_number,
        status=claim.status,
        requested_credit=claim.requested_credit,
        outcome=claim.outcome,
        credit_amount=claim.credit_amount,
        submitted_date=claim.submitted_date,
        resolution_date=claim.resolution_date,
        created_at=claim.created_at,
        anomaly_type=claim.anomaly.anomaly_type.value if claim.anomaly else None,
        invoice_number=None,
        variance=claim.anomaly.variance if claim.anomaly else None,
        message_count=msg_count or 0,
    )


@router.post(
    "/{claim_id}/messages",
    response_model=ClaimMessageResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Add Message",
    description="Add a message to a claim conversation.",
)
async def add_claim_message(
    claim_id: str,
    message: ClaimMessageCreate,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ClaimMessageResponse:
    """Add a message to a claim.

    Args:
        claim_id: The claim ID.
        message: Message data.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Created message.
    """
    # Verify claim exists
    result = await db.execute(
        select(Claim).where(Claim.claim_id == claim_id)
    )
    claim = result.scalar_one_or_none()

    if not claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Claim {claim_id} not found",
        )

    # Create message
    claim_message = ClaimMessage(
        message_id=str(uuid4()),
        claim_id=claim_id,
        direction=message.direction,
        message_type=message.message_type,
        content=message.content,
        attachments=message.attachments,
        sender=user.user_id,
        timestamp=datetime.now(timezone.utc),
        is_auto_generated=False,
    )

    db.add(claim_message)

    # TODO: If generate_response is True, call GenAI to generate response

    await db.commit()
    await db.refresh(claim_message)

    logger.info(
        "Claim message added",
        claim_id=claim_id,
        message_id=claim_message.message_id,
        direction=message.direction.value,
        user_id=user.user_id,
    )

    return ClaimMessageResponse(
        message_id=claim_message.message_id,
        claim_id=claim_message.claim_id,
        direction=claim_message.direction,
        message_type=claim_message.message_type,
        content=claim_message.content,
        attachments=claim_message.attachments,
        sender=claim_message.sender,
        timestamp=claim_message.timestamp,
        is_auto_generated=claim_message.is_auto_generated,
    )
