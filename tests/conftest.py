"""Pytest configuration and fixtures."""

import asyncio
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import AsyncGenerator
from uuid import uuid4

import pytest
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from src.models import Base
from src.models.anomaly import Anomaly, AnomalyStatus, AnomalyType
from src.models.carrier import Carrier
from src.models.claim import Claim, ClaimStatus
from src.models.contract import Contract, ContractTerm, ParsingStatus, TermType
from src.models.invoice import Invoice, InvoiceLine, ProcessingStatus, SourceType
from src.models.shipment import Shipment


@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session")
async def engine():
    """Create test database engine."""
    # Use SQLite for testing
    engine = create_async_engine(
        "sqlite+aiosqlite:///:memory:",
        echo=False,
    )

    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    yield engine

    await engine.dispose()


@pytest.fixture
async def db_session(engine) -> AsyncGenerator[AsyncSession, None]:
    """Create a test database session."""
    async_session = async_sessionmaker(
        engine,
        class_=AsyncSession,
        expire_on_commit=False,
    )

    async with async_session() as session:
        yield session
        await session.rollback()


@pytest.fixture
async def fedex_carrier(db_session: AsyncSession) -> Carrier:
    """Create a FedEx carrier for testing."""
    carrier = Carrier(
        carrier_id=str(uuid4()),
        name="FedEx",
        code="FEDX",
        portal_url="https://www.fedex.com/billing",
        is_active=True,
    )
    db_session.add(carrier)
    await db_session.commit()
    await db_session.refresh(carrier)
    return carrier


@pytest.fixture
async def sample_contract(db_session: AsyncSession, fedex_carrier: Carrier) -> Contract:
    """Create a sample contract for testing."""
    contract = Contract(
        contract_id=str(uuid4()),
        carrier_id=fedex_carrier.carrier_id,
        contract_number="FEDX-2026-001",
        effective_date=date(2026, 1, 1),
        expiration_date=date(2026, 12, 31),
        parsing_status=ParsingStatus.COMPLETED,
        version=1,
        is_active=True,
    )
    db_session.add(contract)
    await db_session.commit()
    await db_session.refresh(contract)
    return contract


@pytest.fixture
async def sample_contract_terms(
    db_session: AsyncSession, sample_contract: Contract
) -> list[ContractTerm]:
    """Create sample contract terms for testing."""
    terms = [
        ContractTerm(
            term_id=str(uuid4()),
            contract_id=sample_contract.contract_id,
            term_type=TermType.RATE,
            service_level="FedEx Ground",
            zone="2",
            weight_min=Decimal("0"),
            weight_max=Decimal("10"),
            rate=Decimal("5.50"),
            rate_type="flat",
            confidence_score=Decimal("0.95"),
            validated=True,
        ),
        ContractTerm(
            term_id=str(uuid4()),
            contract_id=sample_contract.contract_id,
            term_type=TermType.SURCHARGE,
            service_level="Fuel Surcharge",
            rate=Decimal("15"),
            rate_type="percentage",
            confidence_score=Decimal("0.90"),
            validated=True,
        ),
        ContractTerm(
            term_id=str(uuid4()),
            contract_id=sample_contract.contract_id,
            term_type=TermType.SLA,
            service_level="FedEx Ground",
            conditions={"delivery_days": 5, "guarantee": "service_guarantee"},
            confidence_score=Decimal("0.85"),
            validated=True,
        ),
    ]

    for term in terms:
        db_session.add(term)

    await db_session.commit()
    return terms


@pytest.fixture
async def sample_invoice(db_session: AsyncSession, fedex_carrier: Carrier) -> Invoice:
    """Create a sample invoice for testing."""
    invoice = Invoice(
        invoice_id=str(uuid4()),
        carrier_id=fedex_carrier.carrier_id,
        invoice_number="INV-2026-001234",
        invoice_date=date(2026, 1, 15),
        due_date=date(2026, 2, 15),
        total_amount=Decimal("150.00"),
        currency="USD",
        source_type=SourceType.PDF,
        processing_status=ProcessingStatus.COMPLETED,
        account_number="123456789",
    )
    db_session.add(invoice)
    await db_session.commit()
    await db_session.refresh(invoice)
    return invoice


@pytest.fixture
async def sample_invoice_lines(
    db_session: AsyncSession, sample_invoice: Invoice
) -> list[InvoiceLine]:
    """Create sample invoice lines for testing."""
    lines = [
        InvoiceLine(
            line_id=str(uuid4()),
            invoice_id=sample_invoice.invoice_id,
            line_number=1,
            pro_number="PRO123456789",
            tracking_number="794644790292",
            service_level="FedEx Ground",
            charge_type="freight",
            amount=Decimal("75.00"),
            weight=Decimal("5.5"),
            zone="2",
            origin_zip="10001",
            destination_zip="90210",
            ship_date=date(2026, 1, 10),
        ),
        InvoiceLine(
            line_id=str(uuid4()),
            invoice_id=sample_invoice.invoice_id,
            line_number=2,
            pro_number="PRO123456789",
            tracking_number="794644790292",
            service_level="FedEx Ground",
            charge_type="fuel_surcharge",
            amount=Decimal("11.25"),
        ),
        InvoiceLine(
            line_id=str(uuid4()),
            invoice_id=sample_invoice.invoice_id,
            line_number=3,
            pro_number="PRO987654321",
            tracking_number="794644790293",
            service_level="FedEx Ground",
            charge_type="freight",
            amount=Decimal("63.75"),
            weight=Decimal("8.0"),
            zone="3",
            origin_zip="10001",
            destination_zip="60601",
            ship_date=date(2026, 1, 12),
        ),
    ]

    for line in lines:
        db_session.add(line)

    await db_session.commit()
    return lines


@pytest.fixture
async def sample_shipment(
    db_session: AsyncSession, fedex_carrier: Carrier
) -> Shipment:
    """Create a sample shipment for testing."""
    shipment = Shipment(
        shipment_id=str(uuid4()),
        carrier_id=fedex_carrier.carrier_id,
        pro_number="PRO123456789",
        tracking_number="794644790292",
        service_level="FedEx Ground",
        origin_zip="10001",
        destination_zip="90210",
        ship_date=date(2026, 1, 10),
        expected_delivery=date(2026, 1, 15),
        actual_delivery=date(2026, 1, 14),
        weight=Decimal("5.5"),
        zone="2",
        status="delivered",
        source_system="TMS",
    )
    db_session.add(shipment)
    await db_session.commit()
    await db_session.refresh(shipment)
    return shipment
