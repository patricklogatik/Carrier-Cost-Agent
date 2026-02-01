"""Tests for anomaly detection rules."""

from datetime import date
from decimal import Decimal
from unittest.mock import AsyncMock, MagicMock

import pytest

from src.models.anomaly import AnomalyType
from src.models.contract import ContractTerm, ParsingStatus, TermType
from src.models.invoice import Invoice, InvoiceLine
from src.models.shipment import Shipment
from src.services.anomaly.detector import AnomalyDetector, DetectionContext
from src.services.anomaly.rules.duplicate import DuplicateDetectionRule
from src.services.anomaly.rules.late_delivery import LateDeliveryDetectionRule
from src.services.anomaly.rules.rate_error import RateErrorDetectionRule


class TestDuplicateDetectionRule:
    """Tests for duplicate charge detection."""

    @pytest.fixture
    def rule(self) -> DuplicateDetectionRule:
        """Create rule instance."""
        return DuplicateDetectionRule()

    @pytest.mark.asyncio
    async def test_detect_duplicate_by_pro_number(self, rule: DuplicateDetectionRule):
        """Test detecting duplicate by PRO number."""
        # Create mock context
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_invoice.invoice_number = "INV-001"

        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.line_id = "line-1"
        mock_line.pro_number = "PRO123456"
        mock_line.tracking_number = None
        mock_line.shipment_id = None
        mock_line.charge_type = "freight"
        mock_line.amount = Decimal("100.00")

        # Mock duplicate found
        mock_duplicate = MagicMock(spec=InvoiceLine)
        mock_duplicate.line_id = "line-2"
        mock_duplicate.pro_number = "PRO123456"
        mock_duplicate.tracking_number = None
        mock_duplicate.charge_type = "freight"
        mock_duplicate.amount = Decimal("100.00")
        mock_duplicate.invoice_id = "inv-2"

        # Configure mock execute to return duplicate
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = mock_duplicate
        mock_db.execute = AsyncMock(return_value=mock_result)

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)

        assert result is not None
        assert result.anomaly_type == AnomalyType.DUPLICATE
        assert result.variance == Decimal("100.00")
        assert result.confidence_score >= Decimal("0.9")
        assert result.duplicate_of_line_id == "line-2"

    @pytest.mark.asyncio
    async def test_no_duplicate_found(self, rule: DuplicateDetectionRule):
        """Test when no duplicate is found."""
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)
        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.line_id = "line-1"
        mock_line.pro_number = "PRO123456"
        mock_line.tracking_number = None
        mock_line.shipment_id = None
        mock_line.charge_type = "freight"
        mock_line.amount = Decimal("100.00")

        # No duplicate found
        mock_result = MagicMock()
        mock_result.scalar_one_or_none.return_value = None
        mock_db.execute = AsyncMock(return_value=mock_result)

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)
        assert result is None


class TestLateDeliveryDetectionRule:
    """Tests for late delivery charge detection."""

    @pytest.fixture
    def rule(self) -> LateDeliveryDetectionRule:
        """Create rule instance."""
        return LateDeliveryDetectionRule()

    @pytest.mark.asyncio
    async def test_detect_false_late_charge(self, rule: LateDeliveryDetectionRule):
        """Test detecting false late delivery charge."""
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)

        mock_shipment = MagicMock(spec=Shipment)
        mock_shipment.shipment_id = "ship-1"
        mock_shipment.pro_number = "PRO123"
        mock_shipment.tracking_number = "TRACK123"
        mock_shipment.service_level = "FedEx Ground"
        mock_shipment.expected_delivery = date(2026, 1, 15)
        mock_shipment.actual_delivery = date(2026, 1, 14)  # Delivered early!

        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.line_id = "line-1"
        mock_line.charge_type = "late_delivery"
        mock_line.charge_description = "Late Delivery Fee"
        mock_line.amount = Decimal("25.00")
        mock_line.shipment = mock_shipment

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)

        assert result is not None
        assert result.anomaly_type == AnomalyType.LATE_DELIVERY
        assert result.expected_amount == Decimal("0")
        assert result.variance == Decimal("25.00")
        assert result.confidence_score >= Decimal("0.9")

    @pytest.mark.asyncio
    async def test_valid_late_charge(self, rule: LateDeliveryDetectionRule):
        """Test that actual late delivery is not flagged."""
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)

        mock_shipment = MagicMock(spec=Shipment)
        mock_shipment.expected_delivery = date(2026, 1, 15)
        mock_shipment.actual_delivery = date(2026, 1, 17)  # Actually late

        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.charge_type = "late_delivery"
        mock_line.charge_description = None
        mock_line.amount = Decimal("25.00")
        mock_line.shipment = mock_shipment

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)
        assert result is None

    @pytest.mark.asyncio
    async def test_not_late_charge_type(self, rule: LateDeliveryDetectionRule):
        """Test that non-late charges are ignored."""
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)

        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.charge_type = "freight"
        mock_line.charge_description = "Base Transportation"
        mock_line.shipment = None

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)
        assert result is None


class TestRateErrorDetectionRule:
    """Tests for rate error detection."""

    @pytest.fixture
    def rule(self) -> RateErrorDetectionRule:
        """Create rule instance."""
        return RateErrorDetectionRule()

    @pytest.mark.asyncio
    async def test_detect_rate_error(self, rule: RateErrorDetectionRule):
        """Test detecting rate discrepancy."""
        mock_db = AsyncMock()
        mock_invoice = MagicMock(spec=Invoice)

        mock_shipment = MagicMock(spec=Shipment)
        mock_shipment.ship_date = date(2026, 1, 10)

        mock_line = MagicMock(spec=InvoiceLine)
        mock_line.line_id = "line-1"
        mock_line.service_level = "FedEx Ground"
        mock_line.zone = "2"
        mock_line.weight = Decimal("5.0")
        mock_line.billed_weight = None
        mock_line.charge_type = "freight"
        mock_line.amount = Decimal("75.00")  # Overcharged
        mock_line.ship_date = date(2026, 1, 10)
        mock_line.shipment = mock_shipment

        # Mock contract
        mock_contract = MagicMock()
        mock_contract.contract_id = "contract-1"
        mock_contract.contract_number = "FEDX-2026"

        # Mock term with lower rate
        mock_term = MagicMock(spec=ContractTerm)
        mock_term.term_id = "term-1"
        mock_term.rate = Decimal("50.00")  # Contract rate
        mock_term.rate_type = "flat"
        mock_term.confidence_score = Decimal("0.95")
        mock_term.validated = True
        mock_term.source_page = 5
        mock_term.source_text = "Ground Zone 2: $50.00"

        # Configure mock executes
        def mock_execute_side_effect(query):
            result = MagicMock()
            # Check if looking for contract or term
            if "Contract" in str(query) or "contract" in str(query).lower():
                result.scalar_one_or_none.return_value = mock_contract
            else:
                result.scalar_one_or_none.return_value = mock_term
            return result

        mock_db.execute = AsyncMock(side_effect=mock_execute_side_effect)

        context = DetectionContext(
            invoice=mock_invoice,
            line=mock_line,
            carrier_id="carrier-1",
            db=mock_db,
        )

        result = await rule.detect(context)

        assert result is not None
        assert result.anomaly_type == AnomalyType.RATE_ERROR
        assert result.expected_amount == Decimal("50.00")
        assert result.actual_amount == Decimal("75.00")
        assert result.variance == Decimal("25.00")
