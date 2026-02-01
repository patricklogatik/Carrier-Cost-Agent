"""Analytics-related schemas."""

from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field


class RecoveryByStatus(BaseModel):
    """Recovery breakdown by claim status."""

    identified: Decimal = Field(description="Total variance identified")
    submitted: Decimal = Field(description="Total requested credit submitted")
    recovered: Decimal = Field(description="Total credit received")
    pending: Decimal = Field(description="Total in pending claims")


class RecoveryByType(BaseModel):
    """Recovery breakdown by anomaly type."""

    anomaly_type: str
    count: int
    total_variance: Decimal
    recovered_amount: Decimal


class RecoveryByPeriod(BaseModel):
    """Recovery metrics for a time period."""

    period: str  # e.g., "2026-01", "2026-W04"
    identified: Decimal
    submitted: Decimal
    recovered: Decimal
    claim_count: int


class RecoveryMetrics(BaseModel):
    """Overall recovery metrics response."""

    # Summary KPIs
    total_identified: Decimal = Field(description="Total anomaly variance identified")
    total_submitted: Decimal = Field(description="Total requested in submitted claims")
    total_recovered: Decimal = Field(description="Total credit received")
    recovery_rate: Decimal = Field(description="Percentage recovered of submitted")

    # Counts
    total_anomalies: int
    total_claims: int
    claims_won: int
    claims_lost: int
    claims_pending: int

    # Breakdowns
    by_status: RecoveryByStatus
    by_type: list[RecoveryByType] = []
    by_period: list[RecoveryByPeriod] = []


class AnomalyByType(BaseModel):
    """Anomaly count by type."""

    anomaly_type: str
    count: int
    total_variance: Decimal
    avg_confidence: Decimal


class AnomalyByStatus(BaseModel):
    """Anomaly count by status."""

    status: str
    count: int
    total_variance: Decimal


class AnomalyTrend(BaseModel):
    """Anomaly trend data point."""

    period: str
    count: int
    total_variance: Decimal


class AnomalyMetrics(BaseModel):
    """Anomaly detection metrics response."""

    # Summary
    total_anomalies: int
    total_variance: Decimal
    avg_confidence: Decimal

    # Detection rate
    invoices_scanned: int
    invoices_with_anomalies: int
    detection_rate: Decimal = Field(description="Percentage of invoices with anomalies")

    # Breakdowns
    by_type: list[AnomalyByType] = []
    by_status: list[AnomalyByStatus] = []
    trend: list[AnomalyTrend] = []


class AnalyticsDateRange(BaseModel):
    """Date range for analytics queries."""

    date_from: date | None = None
    date_to: date | None = None
    period: str = Field(
        default="month",
        pattern="^(day|week|month)$",
        description="Aggregation period for trends",
    )
    carrier_id: str | None = None
