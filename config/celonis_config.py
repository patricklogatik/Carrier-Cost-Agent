"""Celonis connection configuration for Carrier Cost Agent.

This module provides configuration and connection utilities for
interacting with the Celonis EMS platform using PyCelonis.
"""

import os
from dataclasses import dataclass
from functools import lru_cache
from typing import Optional

from pycelonis import get_celonis
from pycelonis.celonis_api.celonis import Celonis


@dataclass
class CelonisConfig:
    """Configuration for Celonis connection."""

    # Celonis cluster URL
    base_url: str

    # API token for authentication
    api_token: str

    # Data Pool ID for Carrier Cost Agent
    data_pool_id: str

    # ML Workbench settings
    workbench_id: Optional[str] = None

    # Object Store settings
    object_store_bucket: str = "carrier-cost-agent"

    @classmethod
    def from_env(cls) -> "CelonisConfig":
        """Create configuration from environment variables.

        Required environment variables:
            CELONIS_BASE_URL: Celonis cluster URL (e.g., https://team.cluster.celonis.cloud)
            CELONIS_API_TOKEN: API token for authentication
            CELONIS_DATA_POOL_ID: ID of the data pool

        Optional environment variables:
            CELONIS_WORKBENCH_ID: ML Workbench ID
            CELONIS_OBJECT_STORE_BUCKET: Object store bucket name
        """
        base_url = os.environ.get("CELONIS_BASE_URL")
        api_token = os.environ.get("CELONIS_API_TOKEN")
        data_pool_id = os.environ.get("CELONIS_DATA_POOL_ID")

        if not all([base_url, api_token, data_pool_id]):
            raise ValueError(
                "Missing required Celonis configuration. "
                "Set CELONIS_BASE_URL, CELONIS_API_TOKEN, and CELONIS_DATA_POOL_ID"
            )

        return cls(
            base_url=base_url,
            api_token=api_token,
            data_pool_id=data_pool_id,
            workbench_id=os.environ.get("CELONIS_WORKBENCH_ID"),
            object_store_bucket=os.environ.get(
                "CELONIS_OBJECT_STORE_BUCKET", "carrier-cost-agent"
            ),
        )


@lru_cache(maxsize=1)
def get_celonis_connection() -> Celonis:
    """Get or create a Celonis connection.

    Returns a cached connection to the Celonis EMS platform.
    Connection is initialized from environment variables.

    Returns:
        Celonis: Connected Celonis client instance.

    Raises:
        ValueError: If required environment variables are not set.
        CelonisApiError: If connection fails.
    """
    config = CelonisConfig.from_env()

    return get_celonis(
        url=config.base_url,
        api_token=config.api_token,
    )


def get_data_pool(celonis: Optional[Celonis] = None):
    """Get the Carrier Cost Agent data pool.

    Args:
        celonis: Optional Celonis connection. If not provided,
                 creates a new connection.

    Returns:
        DataPool: The configured data pool for Carrier Cost Agent.
    """
    if celonis is None:
        celonis = get_celonis_connection()

    config = CelonisConfig.from_env()
    return celonis.data_integration.get_data_pool(config.data_pool_id)


def get_table(table_name: str, celonis: Optional[Celonis] = None):
    """Get a table from the data pool.

    Args:
        table_name: Name of the table (e.g., "invoice", "anomaly").
        celonis: Optional Celonis connection.

    Returns:
        Table: The requested table from the data pool.
    """
    pool = get_data_pool(celonis)
    return pool.get_table(table_name)


# Table names used in the Carrier Cost Agent
TABLES = {
    "carrier": "carrier",
    "contract": "contract",
    "contract_term": "contract_term",
    "invoice": "invoice",
    "invoice_line": "invoice_line",
    "shipment": "shipment",
    "anomaly": "anomaly",
    "claim": "claim",
    "claim_message": "claim_message",
}
