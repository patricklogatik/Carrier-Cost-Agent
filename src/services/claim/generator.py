"""Claim text generation service."""

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from src.core.config import settings
from src.core.logging import get_logger
from src.models.anomaly import Anomaly, AnomalyType
from src.models.contract import ContractTerm
from src.models.invoice import Invoice, InvoiceLine

logger = get_logger(__name__)


@dataclass
class ClaimContext:
    """Context for claim generation."""

    anomaly: Anomaly
    invoice_line: InvoiceLine
    invoice: Invoice
    shipment: Any | None
    contract_term: ContractTerm | None


@dataclass
class GeneratedClaim:
    """Generated claim content."""

    subject: str
    body: str
    contract_citation: str | None
    requested_credit: Decimal


class ClaimGenerator:
    """Generate claim text from anomalies."""

    def __init__(self, db: AsyncSession) -> None:
        """Initialize the generator.

        Args:
            db: Database session.
        """
        self.db = db

    async def generate(self, anomaly_id: str) -> GeneratedClaim:
        """Generate claim text for an anomaly.

        Args:
            anomaly_id: The anomaly to generate a claim for.

        Returns:
            GeneratedClaim with subject, body, and citation.
        """
        # Load anomaly with related data
        result = await self.db.execute(
            select(Anomaly)
            .options(
                selectinload(Anomaly.invoice_line)
                .selectinload(InvoiceLine.invoice),
                selectinload(Anomaly.invoice_line)
                .selectinload(InvoiceLine.shipment),
                selectinload(Anomaly.contract_term),
            )
            .where(Anomaly.anomaly_id == anomaly_id)
        )
        anomaly = result.scalar_one_or_none()

        if not anomaly:
            raise ValueError(f"Anomaly {anomaly_id} not found")

        context = ClaimContext(
            anomaly=anomaly,
            invoice_line=anomaly.invoice_line,
            invoice=anomaly.invoice_line.invoice,
            shipment=anomaly.invoice_line.shipment,
            contract_term=anomaly.contract_term,
        )

        # Use template-based generation for MVP
        # TODO: Replace with GenAI-powered generation
        return self._generate_from_template(context)

    def _generate_from_template(self, context: ClaimContext) -> GeneratedClaim:
        """Generate claim using templates.

        Args:
            context: Claim context with all related data.

        Returns:
            GeneratedClaim with formatted content.
        """
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice

        # Select template based on anomaly type
        if anomaly.anomaly_type == AnomalyType.DUPLICATE:
            return self._generate_duplicate_claim(context)
        elif anomaly.anomaly_type == AnomalyType.RATE_ERROR:
            return self._generate_rate_error_claim(context)
        elif anomaly.anomaly_type == AnomalyType.LATE_DELIVERY:
            return self._generate_late_delivery_claim(context)
        elif anomaly.anomaly_type == AnomalyType.UNAUTHORIZED_SURCHARGE:
            return self._generate_surcharge_claim(context)
        else:
            return self._generate_generic_claim(context)

    def _generate_duplicate_claim(self, context: ClaimContext) -> GeneratedClaim:
        """Generate duplicate charge claim."""
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice

        subject = f"Duplicate Charge Dispute - Invoice {invoice.invoice_number}"

        body = f"""Dear FedEx Billing Team,

We are writing to dispute a duplicate charge on our account.

INVOICE DETAILS
- Invoice Number: {invoice.invoice_number}
- Invoice Date: {invoice.invoice_date}
- Account Number: {invoice.account_number or 'N/A'}

DISPUTED CHARGE
- Tracking/PRO Number: {line.tracking_number or line.pro_number or 'N/A'}
- Charge Type: {line.charge_type}
- Amount: ${line.amount:.2f}

REASON FOR DISPUTE
This shipment has been billed multiple times. Our records indicate that this exact charge
has already been processed on a previous invoice. We request that this duplicate charge
be credited to our account.

REQUESTED CREDIT: ${anomaly.variance:.2f}

Please investigate this matter and process the credit at your earliest convenience.
If you require any additional documentation, please do not hesitate to contact us.

Thank you for your prompt attention to this matter.

Sincerely,
Accounts Payable
"""

        return GeneratedClaim(
            subject=subject,
            body=body,
            contract_citation=None,
            requested_credit=anomaly.variance,
        )

    def _generate_rate_error_claim(self, context: ClaimContext) -> GeneratedClaim:
        """Generate rate error claim."""
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice
        term = context.contract_term

        subject = f"Rate Discrepancy Dispute - Invoice {invoice.invoice_number}"

        citation = None
        contract_reference = ""
        if term:
            citation = f"Contract term {term.term_id}: {term.source_text[:200] if term.source_text else 'See attached contract'}"
            contract_reference = f"""
CONTRACT REFERENCE
- Contract Page: {term.source_page or 'N/A'}
- Contracted Rate: ${term.rate:.4f if term.rate else 'N/A'} ({term.rate_type or 'flat'})
- Relevant Text: {term.source_text[:300] + '...' if term.source_text and len(term.source_text) > 300 else term.source_text or 'N/A'}
"""

        body = f"""Dear FedEx Billing Team,

We are writing to dispute a rate discrepancy on our account.

INVOICE DETAILS
- Invoice Number: {invoice.invoice_number}
- Invoice Date: {invoice.invoice_date}
- Account Number: {invoice.account_number or 'N/A'}

DISPUTED CHARGE
- Tracking/PRO Number: {line.tracking_number or line.pro_number or 'N/A'}
- Service Level: {line.service_level or 'N/A'}
- Zone: {line.zone or 'N/A'}
- Weight: {line.billed_weight or line.weight or 'N/A'} lbs
- Charged Amount: ${line.amount:.2f}
- Expected Amount: ${anomaly.expected_amount:.2f if anomaly.expected_amount else 'N/A'}
- Variance: ${anomaly.variance:.2f}
{contract_reference}
REASON FOR DISPUTE
The rate applied to this shipment does not match our contracted rate. According to our
agreement, the correct rate for this service level and zone should result in a lower charge.

REQUESTED CREDIT: ${anomaly.variance:.2f}

Please review our contract and apply the correct rate. We request a credit for the
difference between the charged amount and the contracted rate.

Thank you for your prompt attention to this matter.

Sincerely,
Accounts Payable
"""

        return GeneratedClaim(
            subject=subject,
            body=body,
            contract_citation=citation,
            requested_credit=anomaly.variance,
        )

    def _generate_late_delivery_claim(self, context: ClaimContext) -> GeneratedClaim:
        """Generate late delivery charge claim."""
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice
        shipment = context.shipment

        subject = f"False Late Delivery Charge - Invoice {invoice.invoice_number}"

        shipment_info = ""
        if shipment:
            shipment_info = f"""
SHIPMENT DETAILS
- PRO Number: {shipment.pro_number or 'N/A'}
- Tracking Number: {shipment.tracking_number or 'N/A'}
- Service Level: {shipment.service_level or 'N/A'}
- Ship Date: {shipment.ship_date or 'N/A'}
- Expected Delivery: {shipment.expected_delivery or 'N/A'}
- Actual Delivery: {shipment.actual_delivery or 'N/A'}
"""

        body = f"""Dear FedEx Billing Team,

We are writing to dispute a late delivery charge that was incorrectly applied.

INVOICE DETAILS
- Invoice Number: {invoice.invoice_number}
- Invoice Date: {invoice.invoice_date}
- Account Number: {invoice.account_number or 'N/A'}

DISPUTED CHARGE
- Charge Type: {line.charge_type}
- Description: {line.charge_description or 'N/A'}
- Amount: ${line.amount:.2f}
{shipment_info}
REASON FOR DISPUTE
Our records indicate that this shipment was delivered on or before the expected delivery
date. Therefore, the late delivery surcharge should not have been applied. The actual
delivery date was {shipment.actual_delivery if shipment else 'N/A'}, which meets or exceeds
the service commitment of {shipment.expected_delivery if shipment else 'N/A'}.

REQUESTED CREDIT: ${anomaly.variance:.2f}

We request that this charge be credited to our account as the delivery met the
service guarantee.

Thank you for your prompt attention to this matter.

Sincerely,
Accounts Payable
"""

        return GeneratedClaim(
            subject=subject,
            body=body,
            contract_citation=None,
            requested_credit=anomaly.variance,
        )

    def _generate_surcharge_claim(self, context: ClaimContext) -> GeneratedClaim:
        """Generate unauthorized surcharge claim."""
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice

        subject = f"Unauthorized Surcharge Dispute - Invoice {invoice.invoice_number}"

        citation = None
        if anomaly.contract_reference:
            citation = f"Contract {anomaly.contract_reference}"

        body = f"""Dear FedEx Billing Team,

We are writing to dispute a surcharge that does not appear to be authorized under
our contract.

INVOICE DETAILS
- Invoice Number: {invoice.invoice_number}
- Invoice Date: {invoice.invoice_date}
- Account Number: {invoice.account_number or 'N/A'}

DISPUTED CHARGE
- Tracking/PRO Number: {line.tracking_number or line.pro_number or 'N/A'}
- Charge Type: {line.charge_type}
- Description: {line.charge_description or 'N/A'}
- Amount: ${line.amount:.2f}

REASON FOR DISPUTE
We have reviewed our contract and cannot find this surcharge type listed among the
authorized surcharges. We believe this charge was applied in error.

CONTRACT REFERENCE: {anomaly.contract_reference or 'See attached agreement'}

REQUESTED CREDIT: ${anomaly.variance:.2f}

Please review our contract terms and process a credit for this unauthorized charge.

Thank you for your prompt attention to this matter.

Sincerely,
Accounts Payable
"""

        return GeneratedClaim(
            subject=subject,
            body=body,
            contract_citation=citation,
            requested_credit=anomaly.variance,
        )

    def _generate_generic_claim(self, context: ClaimContext) -> GeneratedClaim:
        """Generate generic claim for other anomaly types."""
        anomaly = context.anomaly
        line = context.invoice_line
        invoice = context.invoice

        subject = f"Billing Dispute - Invoice {invoice.invoice_number}"

        body = f"""Dear FedEx Billing Team,

We are writing to dispute a charge on our account.

INVOICE DETAILS
- Invoice Number: {invoice.invoice_number}
- Invoice Date: {invoice.invoice_date}
- Account Number: {invoice.account_number or 'N/A'}

DISPUTED CHARGE
- Tracking/PRO Number: {line.tracking_number or line.pro_number or 'N/A'}
- Charge Type: {line.charge_type}
- Amount: ${line.amount:.2f}
- Expected Amount: ${anomaly.expected_amount:.2f if anomaly.expected_amount else 'N/A'}
- Variance: ${anomaly.variance:.2f}

REASON FOR DISPUTE
{anomaly.description or 'Please see attached documentation for details.'}

REQUESTED CREDIT: ${anomaly.variance:.2f}

Please investigate this matter and process the appropriate credit.

Thank you for your prompt attention to this matter.

Sincerely,
Accounts Payable
"""

        return GeneratedClaim(
            subject=subject,
            body=body,
            contract_citation=anomaly.contract_reference,
            requested_credit=anomaly.variance,
        )
