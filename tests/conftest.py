"""Pytest configuration and fixtures for Celonis-native tests."""

import pytest
from datetime import date
from decimal import Decimal
from typing import Dict, Any, List
from uuid import uuid4

import pandas as pd


@pytest.fixture
def sample_invoice_text() -> str:
    """Sample FedEx invoice text for parsing tests."""
    return """
    FedEx Invoice

    Invoice Number: INV-2026-001234
    Invoice Date: 01/15/2026
    Due Date: 02/15/2026
    Account #: 123456789

    Total Amount Due: $1,234.56

    Tracking Number    Service        Zone    Weight    Amount
    794644790292      Ground          2       5.5       $75.00
    794644790293      Ground          3       8.0       $95.00
    794644790294      Express         1       2.0       $125.00

    Fuel Surcharge: $15.00
    Residential Delivery Fee: $4.50

    Grand Total: $1,234.56
    """


@pytest.fixture
def sample_invoice_data() -> Dict[str, Any]:
    """Sample invoice data as dictionary."""
    return {
        "invoice_id": str(uuid4()),
        "carrier_id": str(uuid4()),
        "invoice_number": "INV-2026-001234",
        "invoice_date": "2026-01-15",
        "total_amount": 1234.56,
    }


@pytest.fixture
def sample_invoice_lines_df() -> pd.DataFrame:
    """Sample invoice lines as DataFrame (mimics Celonis Data Pool data)."""
    return pd.DataFrame([
        {
            "line_id": str(uuid4()),
            "invoice_id": "inv-001",
            "tracking_number": "794644790292",
            "service_level": "FedEx Ground",
            "charge_type": "freight",
            "amount": 75.00,
            "zone": "2",
            "weight": 5.5,
        },
        {
            "line_id": str(uuid4()),
            "invoice_id": "inv-001",
            "tracking_number": "794644790292",
            "service_level": "FedEx Ground",
            "charge_type": "fuel_surcharge",
            "amount": 11.25,
        },
        {
            "line_id": str(uuid4()),
            "invoice_id": "inv-001",
            "tracking_number": "794644790293",
            "service_level": "FedEx Ground",
            "charge_type": "freight",
            "amount": 95.00,
            "zone": "3",
            "weight": 8.0,
        },
    ])


@pytest.fixture
def sample_shipments_df() -> pd.DataFrame:
    """Sample shipments as DataFrame."""
    return pd.DataFrame([
        {
            "shipment_id": str(uuid4()),
            "tracking_number": "794644790292",
            "service_level": "FedEx Ground",
            "ship_date": date(2026, 1, 10),
            "expected_delivery": date(2026, 1, 15),
            "actual_delivery": date(2026, 1, 14),
            "weight": 5.5,
            "zone": "2",
        },
        {
            "shipment_id": str(uuid4()),
            "tracking_number": "794644790293",
            "service_level": "FedEx Ground",
            "ship_date": date(2026, 1, 12),
            "expected_delivery": date(2026, 1, 17),
            "actual_delivery": date(2026, 1, 20),  # Late delivery
            "weight": 8.0,
            "zone": "3",
        },
    ])


@pytest.fixture
def sample_contract_terms_df() -> pd.DataFrame:
    """Sample contract terms as DataFrame."""
    return pd.DataFrame([
        {
            "term_id": str(uuid4()),
            "contract_id": "contract-001",
            "term_type": "rate",
            "service_level": "FedEx Ground",
            "zone": "2",
            "weight_min": 0,
            "weight_max": 10,
            "rate": 5.50,
            "rate_type": "per_lb",
        },
        {
            "term_id": str(uuid4()),
            "contract_id": "contract-001",
            "term_type": "surcharge",
            "service_level": "Fuel Surcharge",
            "rate": 15.0,
            "rate_type": "percentage",
        },
        {
            "term_id": str(uuid4()),
            "contract_id": "contract-001",
            "term_type": "sla",
            "service_level": "FedEx Ground",
            "zone": "3",
            "delivery_days": 5,
        },
    ])


@pytest.fixture
def sample_anomaly_data() -> Dict[str, Any]:
    """Sample anomaly data."""
    return {
        "anomaly_id": str(uuid4()),
        "line_id": str(uuid4()),
        "anomaly_type": "rate_error",
        "expected_amount": 30.25,
        "actual_amount": 75.00,
        "variance": 44.75,
        "confidence_score": 0.92,
        "status": "validated",
    }


@pytest.fixture
def sample_carrier_info() -> Dict[str, Any]:
    """Sample carrier information."""
    return {
        "carrier_id": str(uuid4()),
        "name": "FedEx",
        "code": "FEDX",
        "contact_email": "billing@fedex.com",
    }
