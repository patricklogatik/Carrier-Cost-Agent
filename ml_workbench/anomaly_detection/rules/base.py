"""Base class for anomaly detection rules."""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Any, Dict, Optional

import pandas as pd


@dataclass
class DetectionContext:
    """Context for anomaly detection containing all relevant data.

    Attributes:
        line: Invoice line being evaluated (as dict from DataFrame row).
        invoice: Parent invoice data.
        shipment: Matched shipment data (if available).
        contract_terms: Applicable contract terms DataFrame.
        carrier_id: Carrier identifier.
        historical_lines: Historical invoice lines for duplicate detection.
    """

    line: Dict[str, Any]
    invoice: Dict[str, Any]
    shipment: Optional[Dict[str, Any]]
    contract_terms: pd.DataFrame
    carrier_id: str
    historical_lines: pd.DataFrame


@dataclass
class DetectedAnomaly:
    """Represents a detected billing anomaly.

    Attributes:
        anomaly_type: Type of anomaly (duplicate, rate_error, etc.).
        expected_amount: What the charge should have been.
        actual_amount: What was actually charged.
        variance: Difference between actual and expected.
        confidence_score: Confidence in the detection (0-1).
        detection_rule: Name of the rule that detected this.
        description: Human-readable description.
        evidence: Detailed evidence supporting the anomaly.
        contract_term_id: Reference to relevant contract term.
        contract_reference: Human-readable contract reference.
        duplicate_of_line_id: For duplicate detection, the original line ID.
    """

    anomaly_type: str
    expected_amount: Decimal
    actual_amount: Decimal
    variance: Decimal
    confidence_score: Decimal
    detection_rule: str
    description: str = ""
    evidence: str = ""
    contract_term_id: Optional[str] = None
    contract_reference: Optional[str] = None
    duplicate_of_line_id: Optional[str] = None


class AnomalyRule(ABC):
    """Abstract base class for anomaly detection rules.

    All detection rules should inherit from this class and implement
    the detect method.
    """

    # Rule identifier
    name: str = "base_rule"

    # Whether the rule is enabled
    enabled: bool = True

    @abstractmethod
    def detect(self, context: DetectionContext) -> Optional[DetectedAnomaly]:
        """Detect anomalies in the given context.

        Args:
            context: Detection context with all relevant data.

        Returns:
            DetectedAnomaly if an anomaly is found, None otherwise.
        """
        pass
