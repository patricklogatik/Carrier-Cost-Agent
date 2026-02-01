"""FastAPI application entry point."""

from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from src.api.middleware import LoggingMiddleware, RequestIDMiddleware
from src.api.routes import anomalies, analytics, claims, contracts, health, invoices, shipments
from src.core.config import settings
from src.core.database import close_db, init_db
from src.core.logging import get_logger

logger = get_logger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Carrier Cost Agent API", env=settings.app_env)
    if settings.is_development:
        await init_db()
    yield
    # Shutdown
    logger.info("Shutting down Carrier Cost Agent API")
    await close_db()


def create_application() -> FastAPI:
    """Create and configure the FastAPI application."""
    app = FastAPI(
        title="Carrier Cost Agent API",
        description="AI-powered carrier invoice validation and cost recovery",
        version="0.1.0",
        docs_url="/docs" if settings.debug else None,
        redoc_url="/redoc" if settings.debug else None,
        openapi_url=f"{settings.api_prefix}/openapi.json",
        lifespan=lifespan,
    )

    # Add middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(LoggingMiddleware)

    # Register exception handlers
    register_exception_handlers(app)

    # Register routers
    app.include_router(health.router, tags=["Health"])
    app.include_router(
        invoices.router,
        prefix=f"{settings.api_prefix}/invoices",
        tags=["Invoices"],
    )
    app.include_router(
        shipments.router,
        prefix=f"{settings.api_prefix}/shipments",
        tags=["Shipments"],
    )
    app.include_router(
        contracts.router,
        prefix=f"{settings.api_prefix}/contracts",
        tags=["Contracts"],
    )
    app.include_router(
        anomalies.router,
        prefix=f"{settings.api_prefix}/anomalies",
        tags=["Anomalies"],
    )
    app.include_router(
        claims.router,
        prefix=f"{settings.api_prefix}/claims",
        tags=["Claims"],
    )
    app.include_router(
        analytics.router,
        prefix=f"{settings.api_prefix}/analytics",
        tags=["Analytics"],
    )

    return app


def register_exception_handlers(app: FastAPI) -> None:
    """Register global exception handlers."""

    @app.exception_handler(ValueError)
    async def value_error_handler(request: Request, exc: ValueError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content={"detail": str(exc), "type": "validation_error"},
        )

    @app.exception_handler(Exception)
    async def generic_exception_handler(
        request: Request, exc: Exception
    ) -> JSONResponse:
        logger.error(
            "Unhandled exception",
            error=str(exc),
            path=request.url.path,
            method=request.method,
        )
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content={
                "detail": "An internal error occurred",
                "type": "internal_error",
            },
        )


# Create application instance
app = create_application()
