"""Application settings for Carrier Cost Agent.

Provides centralized configuration management for the application.
"""

import os
from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Settings:
    """Application settings loaded from environment variables."""

    # Environment
    environment: str = field(
        default_factory=lambda: os.environ.get("ENVIRONMENT", "development")
    )
    debug: bool = field(
        default_factory=lambda: os.environ.get("DEBUG", "false").lower() == "true"
    )

    # Celonis Configuration
    celonis_base_url: str = field(
        default_factory=lambda: os.environ.get("CELONIS_BASE_URL", "")
    )
    celonis_api_token: str = field(
        default_factory=lambda: os.environ.get("CELONIS_API_TOKEN", "")
    )
    celonis_data_pool_id: str = field(
        default_factory=lambda: os.environ.get("CELONIS_DATA_POOL_ID", "")
    )
    celonis_workbench_id: Optional[str] = field(
        default_factory=lambda: os.environ.get("CELONIS_WORKBENCH_ID")
    )

    # LLM Configuration (for contract parsing and claim generation)
    llm_model_contract_parsing: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_MODEL_CONTRACT_PARSING", "celonis-claude-3-5-sonnet"
        )
    )
    llm_model_claim_generation: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_MODEL_CLAIM_GENERATION", "celonis-claude-3-5-sonnet"
        )
    )
    llm_model_qa_response: str = field(
        default_factory=lambda: os.environ.get(
            "LLM_MODEL_QA_RESPONSE", "celonis-claude-3-5-sonnet"
        )
    )

    # Processing Configuration
    invoice_processing_batch_size: int = field(
        default_factory=lambda: int(
            os.environ.get("INVOICE_PROCESSING_BATCH_SIZE", "100")
        )
    )
    anomaly_detection_confidence_threshold: float = field(
        default_factory=lambda: float(
            os.environ.get("ANOMALY_DETECTION_CONFIDENCE_THRESHOLD", "0.5")
        )
    )
    duplicate_lookback_days: int = field(
        default_factory=lambda: int(
            os.environ.get("DUPLICATE_LOOKBACK_DAYS", "90")
        )
    )

    # File Storage
    object_store_bucket: str = field(
        default_factory=lambda: os.environ.get(
            "CELONIS_OBJECT_STORE_BUCKET", "carrier-cost-agent"
        )
    )

    # Logging
    log_level: str = field(
        default_factory=lambda: os.environ.get("LOG_LEVEL", "INFO")
    )
    log_format: str = field(
        default_factory=lambda: os.environ.get("LOG_FORMAT", "json")
    )


# Global settings instance
settings = Settings()
