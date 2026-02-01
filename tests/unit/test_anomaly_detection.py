"""Tests for anomaly detection rules."""

import pytest
import pandas as pd
from datetime import date
from uuid import uuid4

from ml_workbench.anomaly_detection.rules.base import DetectionContext
from ml_workbench.anomaly_detection.rules.duplicate import DuplicateChargeRule
from ml_workbench.anomaly_detection.rules.rate_error import RateErrorRule
from ml_workbench.anomaly_detection.rules.late_delivery import LateDeliveryRule
from ml_workbench.anomaly_detection.rules.unauthorized_surcharge import UnauthorizedSurchargeRule


class TestDuplicateChargeRule:
    """Tests for duplicate charge detection."""

    @pytest.fixture
    def rule(self) -> DuplicateChargeRule:
        """Create rule instance."""
        return DuplicateChargeRule()

    def test_detect_duplicate_tracking_same_amount(self, rule: DuplicateChargeRule):
        """Test detection of duplicate charges by tracking number."""
        # Create context with duplicate charges
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "charge_type": "freight",
                "amount": 75.00,
            },
            {
                "line_id": "line-2",
                "tracking_number": "794644790292",  # Same tracking
                "charge_type": "freight",  # Same charge type
                "amount": 75.00,  # Same amount
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=pd.DataFrame(),
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "duplicate"
        assert anomalies[0].variance == 75.00  # Duplicate amount

    def test_no_duplicates(self, rule: DuplicateChargeRule):
        """Test no false positives when charges are unique."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "charge_type": "freight",
                "amount": 75.00,
            },
            {
                "line_id": "line-2",
                "tracking_number": "794644790293",  # Different tracking
                "charge_type": "freight",
                "amount": 95.00,
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=pd.DataFrame(),
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 0


class TestRateErrorRule:
    """Tests for rate error detection."""

    @pytest.fixture
    def rule(self) -> RateErrorRule:
        """Create rule instance."""
        return RateErrorRule()

    def test_detect_rate_overcharge(self, rule: RateErrorRule):
        """Test detection of rate overcharges."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "charge_type": "freight",
                "amount": 100.00,  # Charged
                "weight": 5.0,
                "zone": "2",
            },
        ])

        # Contract says rate should be $5.50/lb
        contract_terms_df = pd.DataFrame([
            {
                "term_id": "term-1",
                "term_type": "rate",
                "service_level": "FedEx Ground",
                "zone": "2",
                "weight_min": 0,
                "weight_max": 10,
                "rate": 5.50,
                "rate_type": "per_lb",
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=contract_terms_df,
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "rate_error"
        assert anomalies[0].expected_amount == 27.50  # 5.0 * 5.50
        assert anomalies[0].actual_amount == 100.00
        assert anomalies[0].variance == 72.50  # Overcharged

    def test_no_rate_error_when_correct(self, rule: RateErrorRule):
        """Test no false positives when rate is correct."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "charge_type": "freight",
                "amount": 27.50,  # Correct rate
                "weight": 5.0,
                "zone": "2",
            },
        ])

        contract_terms_df = pd.DataFrame([
            {
                "term_id": "term-1",
                "term_type": "rate",
                "service_level": "FedEx Ground",
                "zone": "2",
                "weight_min": 0,
                "weight_max": 10,
                "rate": 5.50,
                "rate_type": "per_lb",
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=contract_terms_df,
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 0


class TestLateDeliveryRule:
    """Tests for late delivery detection."""

    @pytest.fixture
    def rule(self) -> LateDeliveryRule:
        """Create rule instance."""
        return LateDeliveryRule()

    def test_detect_late_delivery_charge(self, rule: LateDeliveryRule):
        """Test detection of charges for late deliveries."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "charge_type": "freight",
                "amount": 75.00,
            },
        ])

        # Shipment was delivered late
        shipments_df = pd.DataFrame([
            {
                "shipment_id": "ship-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "expected_delivery": date(2026, 1, 15),
                "actual_delivery": date(2026, 1, 20),  # 5 days late
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=shipments_df,
            contract_terms=pd.DataFrame(),
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "late_delivery"
        assert anomalies[0].variance == 75.00  # Full charge for late delivery

    def test_no_anomaly_for_on_time_delivery(self, rule: LateDeliveryRule):
        """Test no anomaly when delivery is on time."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "charge_type": "freight",
                "amount": 75.00,
            },
        ])

        shipments_df = pd.DataFrame([
            {
                "shipment_id": "ship-1",
                "tracking_number": "794644790292",
                "service_level": "FedEx Ground",
                "expected_delivery": date(2026, 1, 15),
                "actual_delivery": date(2026, 1, 14),  # Early!
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=shipments_df,
            contract_terms=pd.DataFrame(),
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 0


class TestUnauthorizedSurchargeRule:
    """Tests for unauthorized surcharge detection."""

    @pytest.fixture
    def rule(self) -> UnauthorizedSurchargeRule:
        """Create rule instance."""
        return UnauthorizedSurchargeRule()

    def test_detect_unauthorized_surcharge(self, rule: UnauthorizedSurchargeRule):
        """Test detection of surcharges not in contract."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "Unknown Surcharge",
                "charge_type": "surcharge",
                "amount": 25.00,
            },
        ])

        # Contract only has fuel surcharge
        contract_terms_df = pd.DataFrame([
            {
                "term_id": "term-1",
                "term_type": "surcharge",
                "service_level": "Fuel Surcharge",
                "rate": 15.0,
                "rate_type": "percentage",
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=contract_terms_df,
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 1
        assert anomalies[0].anomaly_type == "unauthorized_surcharge"
        assert anomalies[0].variance == 25.00

    def test_authorized_surcharge_passes(self, rule: UnauthorizedSurchargeRule):
        """Test no anomaly for authorized surcharges."""
        lines_df = pd.DataFrame([
            {
                "line_id": "line-1",
                "tracking_number": "794644790292",
                "service_level": "Fuel Surcharge",
                "charge_type": "fuel_surcharge",
                "amount": 11.25,
            },
        ])

        contract_terms_df = pd.DataFrame([
            {
                "term_id": "term-1",
                "term_type": "surcharge",
                "service_level": "Fuel Surcharge",
                "rate": 15.0,
                "rate_type": "percentage",
            },
        ])

        context = DetectionContext(
            invoice_lines=lines_df,
            shipments=pd.DataFrame(),
            contract_terms=contract_terms_df,
            carrier_id="carrier-001",
            invoice_id="invoice-001",
        )

        anomalies = rule.detect(context)
        assert len(anomalies) == 0
