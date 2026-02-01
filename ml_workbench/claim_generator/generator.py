"""Claim Generator using Celonis native LLM.

This module provides GenAI-powered claim text generation
for carrier dispute claims using Celonis' native LLM integration.
"""

import json
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Any, Dict, List, Optional
from uuid import uuid4

import pandas as pd
import structlog

# Note: pycelonis_llm is available in Celonis ML Workbench (Sept 2025 release)
try:
    from pycelonis_llm import CelonisLLM
except ImportError:
    CelonisLLM = None

from config.celonis_config import get_table
from config.settings import settings

logger = structlog.get_logger(__name__)


@dataclass
class GeneratedClaim:
    """Represents a generated claim."""

    claim_subject: str
    claim_text: str
    contract_citation: str
    requested_credit: Decimal
    evidence_references: List[str]
    confidence_score: float = 0.9


class ClaimGenerator:
    """Generate carrier dispute claims using Celonis LLM.

    Generates professional, carrier-portal-ready claim text
    with proper evidence and contract citations.
    """

    # Category-specific templates for fallback
    TEMPLATES = {
        "duplicate": """
Subject: Duplicate Charge - Invoice {invoice_number}

Dear Carrier Team,

We have identified a duplicate charge on invoice {invoice_number} dated {invoice_date}.

CLAIM DETAILS:
- Invoice Number: {invoice_number}
- Invoice Date: {invoice_date}
- PRO/Tracking: {tracking_number}
- Charge Type: {charge_type}
- Charged Amount: ${actual_amount}

DUPLICATE REFERENCE:
This charge appears to be a duplicate of a previous charge on invoice line {duplicate_line_id}.

REQUEST:
We request a credit of ${variance} for this duplicate charge.

Please review and process this claim at your earliest convenience.

Best regards,
{company_name}
""",
        "rate_error": """
Subject: Rate Discrepancy - Invoice {invoice_number}

Dear Carrier Team,

We have identified a rate discrepancy on invoice {invoice_number} dated {invoice_date}.

CLAIM DETAILS:
- Invoice Number: {invoice_number}
- Invoice Date: {invoice_date}
- PRO/Tracking: {tracking_number}
- Service Level: {service_level}
- Zone: {zone}
- Weight: {weight} lbs

RATE COMPARISON:
- Charged Amount: ${actual_amount}
- Contract Rate: ${expected_amount}
- Variance: ${variance}

CONTRACT REFERENCE:
{contract_citation}

REQUEST:
We request a credit of ${variance} to correct this rate discrepancy per our contracted rates.

Best regards,
{company_name}
""",
        "late_delivery": """
Subject: Invalid Late Delivery Charge - Invoice {invoice_number}

Dear Carrier Team,

We are disputing a late delivery charge on invoice {invoice_number} as our records show the shipment was delivered on time.

SHIPMENT DETAILS:
- Invoice Number: {invoice_number}
- PRO/Tracking: {tracking_number}
- Service Level: {service_level}
- Expected Delivery: {expected_delivery}
- Actual Delivery: {actual_delivery}
- Late Charge Amount: ${actual_amount}

EVIDENCE:
The shipment was delivered on {actual_delivery}, which is on or before the expected delivery date of {expected_delivery}. Therefore, the late delivery charge is not valid.

REQUEST:
We request a full credit of ${actual_amount} for this invalid late delivery charge.

Best regards,
{company_name}
""",
        "unauthorized_surcharge": """
Subject: Unauthorized Surcharge - Invoice {invoice_number}

Dear Carrier Team,

We have identified an unauthorized surcharge on invoice {invoice_number}.

CLAIM DETAILS:
- Invoice Number: {invoice_number}
- Invoice Date: {invoice_date}
- PRO/Tracking: {tracking_number}
- Surcharge Type: {charge_type}
- Charged Amount: ${actual_amount}

CONTRACT REFERENCE:
This surcharge type is not included in our current contract terms.
{contract_citation}

REQUEST:
We request a credit of ${variance} as this surcharge is not authorized under our agreement.

Best regards,
{company_name}
""",
    }

    def __init__(self, data_pool=None):
        """Initialize the claim generator.

        Args:
            data_pool: Optional Celonis Data Pool connection.
        """
        self.data_pool = data_pool

        # Initialize LLM if available
        self.llm = None
        if CelonisLLM:
            try:
                self.llm = CelonisLLM(
                    model=settings.llm_model_claim_generation
                )
                logger.info("Initialized Celonis LLM for claim generation")
            except Exception as e:
                logger.warning(f"Failed to initialize Celonis LLM: {e}")

    def generate_claim(
        self,
        anomaly_id: str,
        company_name: str = "Our Company",
        regenerate: bool = False,
    ) -> Optional[GeneratedClaim]:
        """Generate a claim for an anomaly.

        Args:
            anomaly_id: UUID of the anomaly to create claim for.
            company_name: Name to use in claim signature.
            regenerate: Whether to regenerate with different phrasing.

        Returns:
            GeneratedClaim if successful, None otherwise.
        """
        logger.info("Generating claim", anomaly_id=anomaly_id)

        # Fetch anomaly and related data
        context = self._build_context(anomaly_id)
        if not context:
            logger.warning("Failed to build context", anomaly_id=anomaly_id)
            return None

        context["company_name"] = company_name

        # Generate claim text
        if self.llm and not regenerate:
            claim = self._generate_with_llm(context)
        else:
            claim = self._generate_with_template(context)

        return claim

    def save_claim(
        self,
        claim: GeneratedClaim,
        anomaly_id: str,
        created_by: str,
    ) -> str:
        """Save a generated claim to the Data Pool.

        Args:
            claim: Generated claim to save.
            anomaly_id: ID of the source anomaly.
            created_by: Username of claim creator.

        Returns:
            Created claim ID.
        """
        claim_id = str(uuid4())
        claim_number = f"CLM-{datetime.now().strftime('%Y%m%d')}-{claim_id[:8].upper()}"

        record = {
            "claim_id": claim_id,
            "anomaly_id": anomaly_id,
            "claim_number": claim_number,
            "status": "draft",
            "claim_subject": claim.claim_subject,
            "claim_text": claim.claim_text,
            "contract_citation": claim.contract_citation,
            "evidence_references": json.dumps(claim.evidence_references),
            "requested_credit": float(claim.requested_credit),
            "created_by": created_by,
            "created_at": datetime.now(),
            "updated_at": datetime.now(),
        }

        df = pd.DataFrame([record])
        claim_table = get_table("claim", self.data_pool)
        claim_table.upsert(df, keys=["claim_id"])

        logger.info("Claim saved", claim_id=claim_id, claim_number=claim_number)
        return claim_id

    def _build_context(self, anomaly_id: str) -> Optional[Dict[str, Any]]:
        """Build context for claim generation.

        Args:
            anomaly_id: ID of the anomaly.

        Returns:
            Context dictionary with all relevant data.
        """
        # Fetch anomaly
        anomaly_table = get_table("anomaly", self.data_pool)
        anomalies = anomaly_table.get_data_frame(
            filter=f"anomaly_id = '{anomaly_id}'"
        )

        if anomalies.empty:
            return None

        anomaly = anomalies.iloc[0].to_dict()

        # Fetch invoice line
        line_id = anomaly.get("line_id")
        line_table = get_table("invoice_line", self.data_pool)
        lines = line_table.get_data_frame(filter=f"line_id = '{line_id}'")

        line = lines.iloc[0].to_dict() if not lines.empty else {}

        # Fetch invoice
        invoice_id = line.get("invoice_id")
        invoice_table = get_table("invoice", self.data_pool)
        invoices = invoice_table.get_data_frame(
            filter=f"invoice_id = '{invoice_id}'"
        )

        invoice = invoices.iloc[0].to_dict() if not invoices.empty else {}

        # Fetch shipment if available
        shipment_id = line.get("shipment_id")
        shipment = {}
        if shipment_id:
            shipment_table = get_table("shipment", self.data_pool)
            shipments = shipment_table.get_data_frame(
                filter=f"shipment_id = '{shipment_id}'"
            )
            shipment = shipments.iloc[0].to_dict() if not shipments.empty else {}

        # Fetch contract term if referenced
        contract_citation = ""
        term_id = anomaly.get("contract_term_id")
        if term_id:
            term_table = get_table("contract_term", self.data_pool)
            terms = term_table.get_data_frame(filter=f"term_id = '{term_id}'")
            if not terms.empty:
                term = terms.iloc[0]
                contract_citation = (
                    f"Contract Page {term.get('source_page', '?')}: "
                    f"{term.get('source_text', 'See attached contract')[:300]}"
                )

        # Build context
        context = {
            "anomaly_type": anomaly.get("anomaly_type"),
            "expected_amount": anomaly.get("expected_amount", 0),
            "actual_amount": anomaly.get("actual_amount", 0),
            "variance": anomaly.get("variance", 0),
            "confidence_score": anomaly.get("confidence_score", 0),
            "duplicate_line_id": anomaly.get("duplicate_of_line_id"),
            "contract_reference": anomaly.get("contract_reference", ""),
            "invoice_number": invoice.get("invoice_number", ""),
            "invoice_date": invoice.get("invoice_date", ""),
            "tracking_number": line.get("tracking_number") or line.get("pro_number") or "",
            "charge_type": line.get("charge_type", ""),
            "charge_description": line.get("charge_description", ""),
            "service_level": line.get("service_level") or shipment.get("service_level", ""),
            "zone": line.get("zone", ""),
            "weight": line.get("weight") or shipment.get("weight", ""),
            "expected_delivery": shipment.get("expected_delivery", ""),
            "actual_delivery": shipment.get("actual_delivery", ""),
            "contract_citation": contract_citation,
        }

        return context

    def _generate_with_llm(self, context: Dict[str, Any]) -> GeneratedClaim:
        """Generate claim using Celonis LLM.

        Args:
            context: Context data for generation.

        Returns:
            Generated claim.
        """
        prompt = self._build_generation_prompt(context)

        try:
            response = self.llm.generate(prompt)
            return self._parse_llm_response(response, context)
        except Exception as e:
            logger.warning("LLM generation failed, using template", error=str(e))
            return self._generate_with_template(context)

    def _build_generation_prompt(self, context: Dict[str, Any]) -> str:
        """Build the generation prompt for the LLM."""
        anomaly_type = context.get("anomaly_type", "unknown")

        return f"""Generate a professional carrier dispute claim for a {anomaly_type} anomaly.

CONTEXT:
- Anomaly Type: {anomaly_type}
- Invoice Number: {context.get('invoice_number')}
- Invoice Date: {context.get('invoice_date')}
- Tracking/PRO: {context.get('tracking_number')}
- Charged Amount: ${context.get('actual_amount')}
- Expected Amount: ${context.get('expected_amount')}
- Variance: ${context.get('variance')}
- Service Level: {context.get('service_level')}
- Zone: {context.get('zone')}
- Contract Citation: {context.get('contract_citation')}

REQUIREMENTS:
1. Professional, formal tone suitable for carrier portal submission
2. Clear statement of the issue
3. Specific invoice and shipment references
4. Contract citation if available
5. Clear credit request with amount
6. Concise but complete

Generate a claim with:
- Subject line (one line)
- Claim body (professional letter format)

Format as JSON:
{{"subject": "...", "body": "..."}}"""

    def _parse_llm_response(
        self, response: str, context: Dict[str, Any]
    ) -> GeneratedClaim:
        """Parse LLM response into GeneratedClaim."""
        try:
            # Clean JSON
            response = response.strip()
            if response.startswith("```"):
                response = response.split("```")[1]
                if response.startswith("json"):
                    response = response[4:]

            data = json.loads(response)

            return GeneratedClaim(
                claim_subject=data.get("subject", "Billing Dispute"),
                claim_text=data.get("body", ""),
                contract_citation=context.get("contract_citation", ""),
                requested_credit=Decimal(str(context.get("variance", 0))),
                evidence_references=[
                    f"Invoice: {context.get('invoice_number')}",
                    f"PRO/Tracking: {context.get('tracking_number')}",
                ],
                confidence_score=0.9,
            )

        except Exception as e:
            logger.warning("Failed to parse LLM response", error=str(e))
            return self._generate_with_template(context)

    def _generate_with_template(self, context: Dict[str, Any]) -> GeneratedClaim:
        """Generate claim using template fallback.

        Args:
            context: Context data for generation.

        Returns:
            Generated claim.
        """
        anomaly_type = context.get("anomaly_type", "duplicate")
        template = self.TEMPLATES.get(anomaly_type, self.TEMPLATES["duplicate"])

        # Fill template
        claim_text = template.format(**{
            k: v if v else "N/A"
            for k, v in context.items()
        })

        # Extract subject from first line
        lines = claim_text.strip().split("\n")
        subject = lines[0].replace("Subject: ", "") if lines else "Billing Dispute"

        return GeneratedClaim(
            claim_subject=subject,
            claim_text=claim_text,
            contract_citation=context.get("contract_citation", ""),
            requested_credit=Decimal(str(context.get("variance", 0))),
            evidence_references=[
                f"Invoice: {context.get('invoice_number')}",
                f"PRO/Tracking: {context.get('tracking_number')}",
            ],
            confidence_score=0.85,
        )


# Export
__all__ = ["ClaimGenerator", "GeneratedClaim"]
