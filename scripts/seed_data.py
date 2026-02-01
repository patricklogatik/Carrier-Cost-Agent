"""Seed script to populate initial data in Celonis Data Pool."""

from datetime import datetime
from uuid import uuid4

import pandas as pd
import structlog

from config.celonis_config import get_celonis_connection, get_data_pool, get_table

logger = structlog.get_logger(__name__)


def seed_carriers(data_pool) -> int:
    """Seed carrier data to Celonis Data Pool.

    Args:
        data_pool: Celonis Data Pool connection.

    Returns:
        Number of carriers seeded.
    """
    carrier_table = get_table("carrier", data_pool)

    carriers = pd.DataFrame([
        {
            "carrier_id": str(uuid4()),
            "name": "FedEx",
            "code": "FEDX",
            "portal_url": "https://www.fedex.com/billing",
            "contact_email": "billing@fedex.com",
            "is_active": True,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        {
            "carrier_id": str(uuid4()),
            "name": "UPS",
            "code": "UPS",
            "portal_url": "https://www.ups.com/billing",
            "contact_email": "billing@ups.com",
            "is_active": False,  # Not active for MVP
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
        {
            "carrier_id": str(uuid4()),
            "name": "DHL Express",
            "code": "DHL",
            "portal_url": "https://www.dhl.com/billing",
            "contact_email": "billing@dhl.com",
            "is_active": False,  # Not active for MVP
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        },
    ])

    carrier_table.upsert(carriers, keys=["carrier_id"])
    logger.info("Seeded carriers", count=len(carriers))

    return len(carriers)


def main() -> None:
    """Run seed scripts."""
    logger.info("Starting seed script")

    try:
        celonis = get_celonis_connection()
        data_pool = get_data_pool(celonis)

        logger.info("Connected to Celonis Data Pool")

        carrier_count = seed_carriers(data_pool)

        logger.info("Seed complete", carriers=carrier_count)

    except Exception as e:
        logger.error("Seed failed", error=str(e))
        raise


if __name__ == "__main__":
    main()
