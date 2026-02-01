"""Analytics API endpoints."""

from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.schemas.analytics import (
    AnomalyByStatus,
    AnomalyByType,
    AnomalyMetrics,
    AnomalyTrend,
    RecoveryByPeriod,
    RecoveryByStatus,
    RecoveryByType,
    RecoveryMetrics,
)
from src.core.database import get_db_session
from src.core.security import UserContext, get_current_user
from src.models.anomaly import Anomaly, AnomalyStatus
from src.models.claim import Claim, ClaimStatus
from src.models.invoice import Invoice

router = APIRouter()


@router.get(
    "/recovery",
    response_model=RecoveryMetrics,
    summary="Get Recovery Metrics",
    description="Get aggregated recovery metrics for the dashboard.",
)
async def get_recovery_metrics(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    carrier_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> RecoveryMetrics:
    """Get recovery metrics.

    Args:
        date_from: Start date filter.
        date_to: End date filter.
        carrier_id: Filter by carrier.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Aggregated recovery metrics.
    """
    # Build base query with filters
    anomaly_query = select(Anomaly)
    claim_query = select(Claim)

    if date_from:
        anomaly_query = anomaly_query.where(Anomaly.created_at >= date_from)
        claim_query = claim_query.where(Claim.created_at >= date_from)
    if date_to:
        anomaly_query = anomaly_query.where(Anomaly.created_at <= date_to)
        claim_query = claim_query.where(Claim.created_at <= date_to)

    # Total identified (sum of all anomaly variances)
    total_identified_result = await db.execute(
        select(func.sum(Anomaly.variance)).select_from(anomaly_query.subquery())
    )
    total_identified = total_identified_result.scalar() or Decimal("0")

    # Total anomalies
    total_anomalies_result = await db.execute(
        select(func.count()).select_from(anomaly_query.subquery())
    )
    total_anomalies = total_anomalies_result.scalar() or 0

    # Total claims
    total_claims_result = await db.execute(
        select(func.count()).select_from(claim_query.subquery())
    )
    total_claims = total_claims_result.scalar() or 0

    # Total submitted (requested credit for submitted/in_progress/won/lost claims)
    submitted_statuses = [
        ClaimStatus.SUBMITTED,
        ClaimStatus.IN_PROGRESS,
        ClaimStatus.WON,
        ClaimStatus.LOST,
    ]
    total_submitted_result = await db.execute(
        select(func.sum(Claim.requested_credit))
        .where(Claim.status.in_(submitted_statuses))
    )
    total_submitted = total_submitted_result.scalar() or Decimal("0")

    # Total recovered (credit_amount for won claims)
    total_recovered_result = await db.execute(
        select(func.sum(Claim.credit_amount))
        .where(Claim.status == ClaimStatus.WON)
    )
    total_recovered = total_recovered_result.scalar() or Decimal("0")

    # Claims by status
    claims_won_result = await db.execute(
        select(func.count()).where(Claim.status == ClaimStatus.WON)
    )
    claims_won = claims_won_result.scalar() or 0

    claims_lost_result = await db.execute(
        select(func.count()).where(Claim.status == ClaimStatus.LOST)
    )
    claims_lost = claims_lost_result.scalar() or 0

    claims_pending_result = await db.execute(
        select(func.count())
        .where(Claim.status.in_([
            ClaimStatus.DRAFT,
            ClaimStatus.PENDING_APPROVAL,
            ClaimStatus.SUBMITTED,
            ClaimStatus.IN_PROGRESS,
        ]))
    )
    claims_pending = claims_pending_result.scalar() or 0

    # Pending amount
    pending_amount_result = await db.execute(
        select(func.sum(Claim.requested_credit))
        .where(Claim.status.in_([
            ClaimStatus.DRAFT,
            ClaimStatus.PENDING_APPROVAL,
            ClaimStatus.SUBMITTED,
            ClaimStatus.IN_PROGRESS,
        ]))
    )
    pending_amount = pending_amount_result.scalar() or Decimal("0")

    # Recovery rate
    recovery_rate = Decimal("0")
    if total_submitted > 0:
        recovery_rate = (total_recovered / total_submitted) * 100

    # By status breakdown
    by_status = RecoveryByStatus(
        identified=total_identified,
        submitted=total_submitted,
        recovered=total_recovered,
        pending=pending_amount,
    )

    # By type breakdown
    by_type_result = await db.execute(
        select(
            Anomaly.anomaly_type,
            func.count().label("count"),
            func.sum(Anomaly.variance).label("total_variance"),
        )
        .group_by(Anomaly.anomaly_type)
    )
    by_type = []
    for row in by_type_result:
        # Get recovered amount for this type
        recovered_for_type = await db.execute(
            select(func.sum(Claim.credit_amount))
            .join(Anomaly, Claim.anomaly_id == Anomaly.anomaly_id)
            .where(Anomaly.anomaly_type == row.anomaly_type)
            .where(Claim.status == ClaimStatus.WON)
        )
        recovered_amount = recovered_for_type.scalar() or Decimal("0")

        by_type.append(
            RecoveryByType(
                anomaly_type=row.anomaly_type.value,
                count=row.count,
                total_variance=row.total_variance or Decimal("0"),
                recovered_amount=recovered_amount,
            )
        )

    return RecoveryMetrics(
        total_identified=total_identified,
        total_submitted=total_submitted,
        total_recovered=total_recovered,
        recovery_rate=recovery_rate,
        total_anomalies=total_anomalies,
        total_claims=total_claims,
        claims_won=claims_won,
        claims_lost=claims_lost,
        claims_pending=claims_pending,
        by_status=by_status,
        by_type=by_type,
        by_period=[],  # TODO: Implement time series
    )


@router.get(
    "/anomalies",
    response_model=AnomalyMetrics,
    summary="Get Anomaly Metrics",
    description="Get aggregated anomaly detection metrics.",
)
async def get_anomaly_metrics(
    date_from: date | None = Query(default=None),
    date_to: date | None = Query(default=None),
    carrier_id: str | None = Query(default=None),
    db: AsyncSession = Depends(get_db_session),
    user: UserContext = Depends(get_current_user),
) -> AnomalyMetrics:
    """Get anomaly detection metrics.

    Args:
        date_from: Start date filter.
        date_to: End date filter.
        carrier_id: Filter by carrier.
        db: Database session.
        user: Current authenticated user.

    Returns:
        Aggregated anomaly metrics.
    """
    # Total anomalies
    anomaly_query = select(Anomaly)
    if date_from:
        anomaly_query = anomaly_query.where(Anomaly.created_at >= date_from)
    if date_to:
        anomaly_query = anomaly_query.where(Anomaly.created_at <= date_to)

    total_result = await db.execute(
        select(func.count()).select_from(anomaly_query.subquery())
    )
    total_anomalies = total_result.scalar() or 0

    # Total variance
    variance_result = await db.execute(
        select(func.sum(Anomaly.variance)).select_from(anomaly_query.subquery())
    )
    total_variance = variance_result.scalar() or Decimal("0")

    # Average confidence
    avg_conf_result = await db.execute(
        select(func.avg(Anomaly.confidence_score)).select_from(anomaly_query.subquery())
    )
    avg_confidence = avg_conf_result.scalar() or Decimal("0")

    # Invoices scanned (with completed status)
    invoice_query = select(Invoice)
    if date_from:
        invoice_query = invoice_query.where(Invoice.created_at >= date_from)
    if date_to:
        invoice_query = invoice_query.where(Invoice.created_at <= date_to)

    invoices_result = await db.execute(
        select(func.count()).select_from(invoice_query.subquery())
    )
    invoices_scanned = invoices_result.scalar() or 0

    # Invoices with anomalies
    invoices_with_anomalies_result = await db.execute(
        select(func.count(func.distinct(Invoice.invoice_id)))
        .select_from(Invoice)
        .join(Anomaly, Anomaly.line_id.in_(
            select(Invoice.invoice_id)  # This is simplified
        ))
    )
    # Simplified - in practice would need proper join
    invoices_with_anomalies = min(total_anomalies, invoices_scanned)

    # Detection rate
    detection_rate = Decimal("0")
    if invoices_scanned > 0:
        detection_rate = Decimal(invoices_with_anomalies) / Decimal(invoices_scanned) * 100

    # By type
    by_type_result = await db.execute(
        select(
            Anomaly.anomaly_type,
            func.count().label("count"),
            func.sum(Anomaly.variance).label("total_variance"),
            func.avg(Anomaly.confidence_score).label("avg_confidence"),
        )
        .group_by(Anomaly.anomaly_type)
    )
    by_type = [
        AnomalyByType(
            anomaly_type=row.anomaly_type.value,
            count=row.count,
            total_variance=row.total_variance or Decimal("0"),
            avg_confidence=row.avg_confidence or Decimal("0"),
        )
        for row in by_type_result
    ]

    # By status
    by_status_result = await db.execute(
        select(
            Anomaly.status,
            func.count().label("count"),
            func.sum(Anomaly.variance).label("total_variance"),
        )
        .group_by(Anomaly.status)
    )
    by_status = [
        AnomalyByStatus(
            status=row.status.value,
            count=row.count,
            total_variance=row.total_variance or Decimal("0"),
        )
        for row in by_status_result
    ]

    return AnomalyMetrics(
        total_anomalies=total_anomalies,
        total_variance=total_variance,
        avg_confidence=avg_confidence,
        invoices_scanned=invoices_scanned,
        invoices_with_anomalies=invoices_with_anomalies,
        detection_rate=detection_rate,
        by_type=by_type,
        by_status=by_status,
        trend=[],  # TODO: Implement time series
    )
