"""Health check endpoints."""

from datetime import datetime, timezone
from typing import Any

from fastapi import APIRouter, Depends, status
from pydantic import BaseModel
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from src.core.config import settings
from src.core.database import get_db_session

router = APIRouter()


class HealthResponse(BaseModel):
    """Health check response model."""

    status: str
    timestamp: datetime
    version: str
    environment: str
    checks: dict[str, Any]


@router.get(
    "/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check",
    description="Check the health status of the API and its dependencies.",
)
async def health_check(
    db: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """Perform health check on the API and its dependencies.

    Returns:
        HealthResponse with status of all components.
    """
    checks: dict[str, Any] = {}

    # Check database connection
    try:
        await db.execute(text("SELECT 1"))
        checks["database"] = {"status": "healthy"}
    except Exception as e:
        checks["database"] = {"status": "unhealthy", "error": str(e)}

    # Overall status
    all_healthy = all(
        check.get("status") == "healthy" for check in checks.values()
    )

    return HealthResponse(
        status="healthy" if all_healthy else "degraded",
        timestamp=datetime.now(timezone.utc),
        version="0.1.0",
        environment=settings.app_env,
        checks=checks,
    )


@router.get(
    "/api/v1/health",
    response_model=HealthResponse,
    status_code=status.HTTP_200_OK,
    summary="Health Check (v1)",
    description="Check the health status of the API and its dependencies.",
)
async def health_check_v1(
    db: AsyncSession = Depends(get_db_session),
) -> HealthResponse:
    """Perform health check on the API and its dependencies (v1 endpoint).

    Returns:
        HealthResponse with status of all components.
    """
    return await health_check(db)
