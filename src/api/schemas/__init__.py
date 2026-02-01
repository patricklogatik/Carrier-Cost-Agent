"""Pydantic schemas for API request/response validation."""

from src.api.schemas.common import PaginatedResponse, PaginationParams
from src.api.schemas.invoice import (
    InvoiceCreate,
    InvoiceDetail,
    InvoiceLineResponse,
    InvoiceResponse,
    InvoiceUploadResponse,
)
from src.api.schemas.shipment import (
    ShipmentCreate,
    ShipmentImportResponse,
    ShipmentResponse,
)
from src.api.schemas.contract import (
    ContractCreate,
    ContractDetail,
    ContractResponse,
    ContractTermResponse,
    ContractTermValidation,
    ContractLookupRequest,
    ContractLookupResponse,
)
from src.api.schemas.anomaly import (
    AnomalyDetail,
    AnomalyResponse,
    AnomalyStatusUpdate,
)
from src.api.schemas.claim import (
    ClaimCreate,
    ClaimDetail,
    ClaimMessageCreate,
    ClaimMessageResponse,
    ClaimResponse,
    ClaimUpdate,
)
from src.api.schemas.analytics import (
    AnomalyMetrics,
    RecoveryMetrics,
)

__all__ = [
    # Common
    "PaginatedResponse",
    "PaginationParams",
    # Invoice
    "InvoiceCreate",
    "InvoiceDetail",
    "InvoiceLineResponse",
    "InvoiceResponse",
    "InvoiceUploadResponse",
    # Shipment
    "ShipmentCreate",
    "ShipmentImportResponse",
    "ShipmentResponse",
    # Contract
    "ContractCreate",
    "ContractDetail",
    "ContractResponse",
    "ContractTermResponse",
    "ContractTermValidation",
    "ContractLookupRequest",
    "ContractLookupResponse",
    # Anomaly
    "AnomalyDetail",
    "AnomalyResponse",
    "AnomalyStatusUpdate",
    # Claim
    "ClaimCreate",
    "ClaimDetail",
    "ClaimMessageCreate",
    "ClaimMessageResponse",
    "ClaimResponse",
    "ClaimUpdate",
    # Analytics
    "AnomalyMetrics",
    "RecoveryMetrics",
]
