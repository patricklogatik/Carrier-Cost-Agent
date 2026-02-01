"""Seed script to populate initial data including FedEx carrier."""

import asyncio
from uuid import uuid4

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.core.config import settings
from src.models.carrier import Carrier


async def seed_carriers(session: AsyncSession) -> None:
    """Seed carrier data."""
    carriers = [
        Carrier(
            carrier_id=str(uuid4()),
            name="FedEx",
            code="FEDX",
            portal_url="https://www.fedex.com/billing",
            contact_email="billing@fedex.com",
            is_active=True,
        ),
        Carrier(
            carrier_id=str(uuid4()),
            name="UPS",
            code="UPS",
            portal_url="https://www.ups.com/billing",
            contact_email="billing@ups.com",
            is_active=False,  # Not active for MVP
        ),
        Carrier(
            carrier_id=str(uuid4()),
            name="DHL Express",
            code="DHL",
            portal_url="https://www.dhl.com/billing",
            contact_email="billing@dhl.com",
            is_active=False,  # Not active for MVP
        ),
    ]

    for carrier in carriers:
        session.add(carrier)

    await session.commit()
    print(f"Seeded {len(carriers)} carriers")


async def main() -> None:
    """Run seed scripts."""
    # Create database URL for async
    database_url = settings.database_url
    if database_url.startswith("postgresql://"):
        database_url = database_url.replace("postgresql://", "postgresql+asyncpg://", 1)

    engine = create_async_engine(database_url, echo=True)
    async_session = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

    async with async_session() as session:
        print("Seeding carriers...")
        await seed_carriers(session)

    await engine.dispose()
    print("Seed complete!")


if __name__ == "__main__":
    asyncio.run(main())
