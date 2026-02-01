"""Application configuration management."""

from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "carrier-cost-agent"
    app_env: str = "development"
    debug: bool = False
    log_level: str = "INFO"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 8000
    api_prefix: str = "/api/v1"

    # Database
    database_url: str = "postgresql://postgres:postgres@localhost:5432/carrier_cost_agent"

    # Redis
    redis_url: str = "redis://localhost:6379/0"

    # Authentication
    api_key_secret: str = "change-me-in-production"
    jwt_secret_key: str = "change-me-in-production"
    jwt_algorithm: str = "HS256"
    jwt_access_token_expire_minutes: int = 30

    # SSO
    sso_enabled: bool = False
    sso_provider: str = ""
    sso_client_id: str = ""
    sso_client_secret: str = ""
    sso_authority: str = ""
    sso_redirect_uri: str = ""

    # Celonis
    celonis_base_url: str = ""
    celonis_api_token: str = ""
    celonis_data_pool_id: str = ""

    # Storage
    storage_type: str = "local"
    storage_local_path: str = "./uploads"
    aws_access_key_id: str = ""
    aws_secret_access_key: str = ""
    aws_region: str = "eu-central-1"
    s3_bucket_name: str = ""

    # GenAI
    llm_provider: str = "anthropic"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    azure_openai_api_key: str = ""
    azure_openai_endpoint: str = ""
    llm_model_contract_parsing: str = "claude-3-5-sonnet-20241022"
    llm_model_claim_generation: str = "claude-3-5-sonnet-20241022"
    llm_model_embeddings: str = "text-embedding-3-small"

    # PDF Processing
    ocr_provider: str = "tesseract"
    azure_document_intelligence_endpoint: str = ""
    azure_document_intelligence_key: str = ""

    # Email
    smtp_host: str = ""
    smtp_port: int = 587
    smtp_user: str = ""
    smtp_password: str = ""
    smtp_from_email: str = ""

    # CORS
    cors_origins: list[str] = ["http://localhost:3000", "http://localhost:8000"]

    # Rate Limiting
    rate_limit_requests: int = 100
    rate_limit_period: int = 60

    # Feature Flags
    feature_claim_approval_required: bool = True
    feature_auto_matching: bool = True
    feature_webhook_notifications: bool = False

    # Monitoring
    sentry_dsn: str = ""
    prometheus_enabled: bool = False

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, v: Any) -> list[str]:
        """Parse CORS origins from string or list."""
        if isinstance(v, str):
            import json

            try:
                return json.loads(v)
            except json.JSONDecodeError:
                return [origin.strip() for origin in v.split(",")]
        return v

    @property
    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.app_env.lower() == "production"

    @property
    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.app_env.lower() == "development"

    @property
    def is_testing(self) -> bool:
        """Check if running in test environment."""
        return self.app_env.lower() == "testing"


@lru_cache
def get_settings() -> Settings:
    """Get cached settings instance."""
    return Settings()


settings = get_settings()
