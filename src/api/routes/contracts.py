"""Contract API endpoints."""

from datetime import date, datetime, timezone
from uuid import uuid4

from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.api.schemas.common import PaginatedResponse
from src.api.schemas.contract import (
    ContractCreate,
    ContractDetail,
    ContractLookupRequest,
    ContractLookupResponse,
    ContractResponse,
    ContractTermResponse,
    ContractTermValidation,
    ContractUploadResponse,
    RateLookupResult,
    SLALookupResult,
    SurchargeLookupResult,
)
from src.core.database import get_db_session
from src.core.logging import get_logger
from src.core.security import Roles, UserContext, get_current_user, require_roles
from src.models.contract import Contract, ContractTerm, ParsingStatus, TermType

logger = get_logger(__name__)
router = APIRouter()


@router.post(
    "",
    response_model=ContractUploadResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Upload Contract PDF",
    description="Upload a carrier contract PDF for parsing.",
)
async def upload_contract(
    file: UploadFile = File(..., description="Contract PDF file"),
    carrier_id: str = Query(..., description="Carrier ID for this contract"),
    contract_number: str = Query(..., description="Contract identifier"),
    effective_date: date = Query(..., description="Contract effective date"),
    expiration_date: date = Query(..., description="Contract expiration date"),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_roles(Roles.CONTRACT_MANAGER, Roles.ADMINISTRATOR)),
) -> ContractUploadResponse:
    """Upload a contract PDF for parsing.

    The contract will be queued for GenAI-powered parsing to extract:
    - Rate tables
    - Surcharge definitions
    - SLA terms
    - Discount structures

    Args:
        file: The PDF file to upload.
        carrier_id: The carrier this contract belongs to.
        contract_number: Contract identifier.
        effective_date: When the contract becomes effective.
        expiration_date: When the contract expires.
        db: Database session.
        user: Current authenticated user (must be Contract Manager or Admin).

    Returns:
        Upload confirmation with contract ID and status.
    """
    # Validate file type
    if not file.filename or not file.filename.lower().endswith(".pdf"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Only PDF files are accepted",
        )

    # Validate dates
    if effective_date >= expiration_date:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Effective date must be before expiration date",
        )

    # Check for existing version
    result = await db.execute(
        select(func.max(Contract.version))
        .where(Contract.carrier_id == carrier_id)
        .where(Contract.contract_number == contract_number)
    )
    current_version = result.scalar() or 0

    # Create contract record
    contract_id = str(uuid4())
    contract = Contract(
        contract_id=contract_id,
        carrier_id=carrier_id,
        contract_number=contract_number,
        effective_date=effective_date,
        expiration_date=expiration_date,
        version=current_version + 1,
        parsing_status=ParsingStatus.PENDING,
    )

    # TODO: Store PDF in object storage and update source_document_path
    # TODO: Queue contract for GenAI parsing

    db.add(contract)
    await db.commit()

    logger.info(
        "Contract uploaded",
        contract_id=contract_id,
        contract_number=contract_number,
        version=current_version + 1,
        user_id=user.user_id,
    )

    return ContractUploadResponse(
        contract_id=contract_id,
        status=ParsingStatus.PENDING,
        filename=file.filename,
        uploaded_at=datetime.now(timezone.utc),
    )


@router.get(
    "",
    response_model=PaginatedResponse[ContractResponse],
    summary="List Contracts",
    description="Retrieve a paginated list of contracts.",
)
async def list_contracts(
    limit: int = Query(default=50, ge=1, le=100),
    offset: int = Query(default=0, ge=0),
    carrier_id: str | None = Query(default=None),
    active_only: bool = Query(default=True),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> PaginatedResponse[ContractResponse]:
    """List contracts with filtering and pagination.

    Args:
        limit: Maximum number of results.
        offset: Number of results to skip.
        carrier_id: Filter by carrier.
        active_only: Only return active contracts.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Paginated list of contracts.
    """
    query = select(Contract)

    if carrier_id:
        query = query.where(Contract.carrier_id == carrier_id)
    if active_only:
        query = query.where(Contract.is_active == True)

    # Count total
    count_query = select(func.count()).select_from(query.subquery())
    total = await db.scalar(count_query) or 0

    # Apply pagination
    query = query.order_by(Contract.created_at.desc()).offset(offset).limit(limit)

    result = await db.execute(query)
    contracts = result.scalars().all()

    items = []
    for c in contracts:
        # Count terms
        term_count_result = await db.execute(
            select(func.count()).where(ContractTerm.contract_id == c.contract_id)
        )
        term_count = term_count_result.scalar() or 0

        validated_count_result = await db.execute(
            select(func.count())
            .where(ContractTerm.contract_id == c.contract_id)
            .where(ContractTerm.validated == True)
        )
        validated_count = validated_count_result.scalar() or 0

        items.append(
            ContractResponse(
                contract_id=c.contract_id,
                carrier_id=c.carrier_id,
                contract_number=c.contract_number,
                effective_date=c.effective_date,
                expiration_date=c.expiration_date,
                parsing_status=c.parsing_status,
                version=c.version,
                is_active=c.is_active,
                term_count=term_count,
                validated_term_count=validated_count,
                created_at=c.created_at,
            )
        )

    return PaginatedResponse(
        items=items,
        total=total,
        limit=limit,
        offset=offset,
    )


@router.get(
    "/lookup",
    response_model=ContractLookupResponse,
    summary="Lookup Contract Terms",
    description="Look up applicable contract terms for a shipment.",
)
async def lookup_contract_terms(
    carrier_id: str = Query(...),
    service_level: str = Query(...),
    zone: str | None = Query(default=None),
    weight: float | None = Query(default=None),
    ship_date: date | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ContractLookupResponse:
    """Look up applicable contract terms.

    Finds the active contract for the carrier and returns matching rate,
    surcharge, and SLA terms.

    Args:
        carrier_id: The carrier ID.
        service_level: Service level to look up.
        zone: Optional zone.
        weight: Optional weight for rate lookup.
        ship_date: Date to check contract validity.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Matching contract terms.
    """
    lookup_date = ship_date or date.today()

    # Find active contract
    result = await db.execute(
        select(Contract)
        .where(Contract.carrier_id == carrier_id)
        .where(Contract.is_active == True)
        .where(Contract.effective_date <= lookup_date)
        .where(Contract.expiration_date >= lookup_date)
        .where(Contract.parsing_status == ParsingStatus.COMPLETED)
        .order_by(Contract.version.desc())
        .limit(1)
    )
    contract = result.scalar_one_or_none()

    if not contract:
        return ContractLookupResponse()

    # Look up base rate
    rate_query = (
        select(ContractTerm)
        .where(ContractTerm.contract_id == contract.contract_id)
        .where(ContractTerm.term_type == TermType.RATE)
        .where(ContractTerm.service_level == service_level)
    )
    if zone:
        rate_query = rate_query.where(ContractTerm.zone == zone)
    if weight:
        rate_query = rate_query.where(ContractTerm.weight_min <= weight)
        rate_query = rate_query.where(ContractTerm.weight_max >= weight)

    rate_result = await db.execute(rate_query.limit(1))
    rate_term = rate_result.scalar_one_or_none()

    base_rate = None
    if rate_term and rate_term.rate:
        base_rate = RateLookupResult(
            amount=rate_term.rate,
            rate_type=rate_term.rate_type,
            term_id=rate_term.term_id,
            source_text=rate_term.source_text,
            confidence_score=rate_term.confidence_score,
        )

    # Look up surcharges
    surcharge_result = await db.execute(
        select(ContractTerm)
        .where(ContractTerm.contract_id == contract.contract_id)
        .where(ContractTerm.term_type == TermType.SURCHARGE)
    )
    surcharge_terms = surcharge_result.scalars().all()

    surcharges = [
        SurchargeLookupResult(
            surcharge_type=t.service_level or "unknown",
            amount=t.rate,
            rate_type=t.rate_type,
            conditions=t.conditions,
            term_id=t.term_id,
        )
        for t in surcharge_terms
    ]

    # Look up SLA
    sla_result = await db.execute(
        select(ContractTerm)
        .where(ContractTerm.contract_id == contract.contract_id)
        .where(ContractTerm.term_type == TermType.SLA)
        .where(ContractTerm.service_level == service_level)
        .limit(1)
    )
    sla_term = sla_result.scalar_one_or_none()

    sla = None
    if sla_term:
        sla = SLALookupResult(
            delivery_days=sla_term.conditions.get("delivery_days") if sla_term.conditions else None,
            guarantee=sla_term.conditions.get("guarantee") if sla_term.conditions else None,
            conditions=sla_term.conditions,
            term_id=sla_term.term_id,
        )

    return ContractLookupResponse(
        base_rate=base_rate,
        surcharges=surcharges,
        sla=sla,
        contract_id=contract.contract_id,
        contract_number=contract.contract_number,
    )


@router.get(
    "/{contract_id}",
    response_model=ContractDetail,
    summary="Get Contract Detail",
    description="Retrieve detailed contract information including terms.",
)
async def get_contract(
    contract_id: str,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> ContractDetail:
    """Get detailed contract information.

    Args:
        contract_id: The contract ID.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Detailed contract with extracted terms.
    """
    result = await db.execute(
        select(Contract)
        .options(selectinload(Contract.terms))
        .where(Contract.contract_id == contract_id)
    )
    contract = result.scalar_one_or_none()

    if not contract:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Contract {contract_id} not found",
        )

    terms = [
        ContractTermResponse(
            term_id=t.term_id,
            term_type=t.term_type,
            service_level=t.service_level,
            zone=t.zone,
            weight_min=t.weight_min,
            weight_max=t.weight_max,
            rate=t.rate,
            rate_type=t.rate_type,
            conditions=t.conditions,
            source_page=t.source_page,
            source_text=t.source_text,
            confidence_score=t.confidence_score,
            validated=t.validated,
            validated_by=t.validated_by,
            validated_at=t.validated_at,
        )
        for t in contract.terms
    ]

    validated_count = sum(1 for t in terms if t.validated)

    return ContractDetail(
        contract_id=contract.contract_id,
        carrier_id=contract.carrier_id,
        contract_number=contract.contract_number,
        effective_date=contract.effective_date,
        expiration_date=contract.expiration_date,
        parsing_status=contract.parsing_status,
        version=contract.version,
        is_active=contract.is_active,
        term_count=len(terms),
        validated_term_count=validated_count,
        created_at=contract.created_at,
        source_document_url=contract.source_document_path,
        parsing_error=contract.parsing_error,
        terms=terms,
    )


@router.put(
    "/{contract_id}/terms/{term_id}/validate",
    response_model=ContractTermResponse,
    summary="Validate Contract Term",
    description="Validate or update an extracted contract term.",
)
async def validate_term(
    contract_id: str,
    term_id: str,
    validation: ContractTermValidation,
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(require_roles(Roles.CONTRACT_MANAGER, Roles.ADMINISTRATOR)),
) -> ContractTermResponse:
    """Validate or update an extracted contract term.

    Args:
        contract_id: The contract ID.
        term_id: The term ID.
        validation: Validation data.
        db: Database session.
        user: Current authenticated user (must be Contract Manager or Admin).

    Returns:
        Updated contract term.
    """
    result = await db.execute(
        select(ContractTerm)
        .where(ContractTerm.term_id == term_id)
        .where(ContractTerm.contract_id == contract_id)
    )
    term = result.scalar_one_or_none()

    if not term:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Term {term_id} not found in contract {contract_id}",
        )

    # Update term
    term.validated = validation.validated
    if validation.rate is not None:
        term.rate = validation.rate
    if validation.rate_type is not None:
        term.rate_type = validation.rate_type
    if validation.conditions is not None:
        term.conditions = validation.conditions
    if validation.service_level is not None:
        term.service_level = validation.service_level
    if validation.zone is not None:
        term.zone = validation.zone
    if validation.weight_min is not None:
        term.weight_min = validation.weight_min
    if validation.weight_max is not None:
        term.weight_max = validation.weight_max

    if validation.validated:
        term.validated_by = user.user_id
        term.validated_at = datetime.now(timezone.utc)

    await db.commit()
    await db.refresh(term)

    logger.info(
        "Contract term validated",
        term_id=term_id,
        contract_id=contract_id,
        validated=validation.validated,
        user_id=user.user_id,
    )

    return ContractTermResponse(
        term_id=term.term_id,
        term_type=term.term_type,
        service_level=term.service_level,
        zone=term.zone,
        weight_min=term.weight_min,
        weight_max=term.weight_max,
        rate=term.rate,
        rate_type=term.rate_type,
        conditions=term.conditions,
        source_page=term.source_page,
        source_text=term.source_text,
        confidence_score=term.confidence_score,
        validated=term.validated,
        validated_by=term.validated_by,
        validated_at=term.validated_at,
    )
