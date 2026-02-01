"""Initial schema with all MVP entities.

Revision ID: 20260201_000001
Revises:
Create Date: 2026-02-01

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = "20260201_000001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create enum types
    op.execute(
        """
        CREATE TYPE processingstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
        CREATE TYPE parsingstatus AS ENUM ('pending', 'processing', 'completed', 'failed');
        CREATE TYPE sourcetype AS ENUM ('pdf', 'edi', 'api');
        CREATE TYPE termtype AS ENUM ('rate', 'surcharge', 'discount', 'sla', 'exception');
        CREATE TYPE anomalytype AS ENUM (
            'duplicate', 'rate_error', 'late_delivery', 'unauthorized_surcharge',
            'weight_discrepancy', 'address_correction', 'service_failure'
        );
        CREATE TYPE anomalystatus AS ENUM ('detected', 'validated', 'dismissed', 'disputed', 'resolved');
        CREATE TYPE claimstatus AS ENUM (
            'draft', 'pending_approval', 'submitted', 'in_progress', 'won', 'lost', 'withdrawn'
        );
        CREATE TYPE claimoutcome AS ENUM ('approved', 'denied', 'partial');
        CREATE TYPE messagedirection AS ENUM ('outbound', 'inbound');
        CREATE TYPE messagetype AS ENUM ('initial_claim', 'response', 'inquiry', 'resolution');
        """
    )

    # Create carriers table
    op.create_table(
        "carriers",
        sa.Column("carrier_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("code", sa.String(10), nullable=False),
        sa.Column("portal_url", sa.String(500), nullable=True),
        sa.Column("contact_email", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("carrier_id"),
        sa.UniqueConstraint("code"),
    )
    op.create_index("ix_carriers_code", "carriers", ["code"])

    # Create contracts table
    op.create_table(
        "contracts",
        sa.Column("contract_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("contract_number", sa.String(100), nullable=False),
        sa.Column("effective_date", sa.Date(), nullable=False),
        sa.Column("expiration_date", sa.Date(), nullable=False),
        sa.Column("source_document_path", sa.String(500), nullable=True),
        sa.Column(
            "parsing_status",
            postgresql.ENUM(
                "pending",
                "processing",
                "completed",
                "failed",
                name="parsingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("parsing_error", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default="true"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("contract_id"),
        sa.ForeignKeyConstraint(
            ["carrier_id"], ["carriers.carrier_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_contracts_carrier_id", "contracts", ["carrier_id"])
    op.create_index("ix_contracts_contract_number", "contracts", ["contract_number"])

    # Create contract_terms table
    op.create_table(
        "contract_terms",
        sa.Column("term_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("contract_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "term_type",
            postgresql.ENUM(
                "rate",
                "surcharge",
                "discount",
                "sla",
                "exception",
                name="termtype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("service_level", sa.String(100), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("weight_min", sa.Numeric(10, 2), nullable=True),
        sa.Column("weight_max", sa.Numeric(10, 2), nullable=True),
        sa.Column("rate", sa.Numeric(12, 4), nullable=True),
        sa.Column("rate_type", sa.String(50), nullable=True),
        sa.Column("conditions", postgresql.JSONB(), nullable=True),
        sa.Column("source_page", sa.Integer(), nullable=True),
        sa.Column("source_text", sa.Text(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=True),
        sa.Column("validated", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("validated_by", sa.String(255), nullable=True),
        sa.Column("validated_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("term_id"),
        sa.ForeignKeyConstraint(
            ["contract_id"], ["contracts.contract_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_contract_terms_contract_id", "contract_terms", ["contract_id"])
    op.create_index("ix_contract_terms_term_type", "contract_terms", ["term_type"])
    op.create_index(
        "ix_contract_terms_service_level", "contract_terms", ["service_level"]
    )
    op.create_index("ix_contract_terms_zone", "contract_terms", ["zone"])

    # Create shipments table
    op.create_table(
        "shipments",
        sa.Column("shipment_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("pro_number", sa.String(100), nullable=True),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("order_number", sa.String(100), nullable=True),
        sa.Column("origin_address", postgresql.JSONB(), nullable=True),
        sa.Column("origin_zip", sa.String(20), nullable=True),
        sa.Column("destination_address", postgresql.JSONB(), nullable=True),
        sa.Column("destination_zip", sa.String(20), nullable=True),
        sa.Column("service_level", sa.String(100), nullable=True),
        sa.Column("package_type", sa.String(50), nullable=True),
        sa.Column("ship_date", sa.Date(), nullable=True),
        sa.Column("expected_delivery", sa.Date(), nullable=True),
        sa.Column("actual_delivery", sa.Date(), nullable=True),
        sa.Column("weight", sa.Numeric(10, 2), nullable=True),
        sa.Column("weight_unit", sa.String(10), nullable=False, server_default="lbs"),
        sa.Column("dimensions", postgresql.JSONB(), nullable=True),
        sa.Column("dim_weight", sa.Numeric(10, 2), nullable=True),
        sa.Column("quoted_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("status", sa.String(50), nullable=True),
        sa.Column("delivery_signature", sa.String(255), nullable=True),
        sa.Column("source_system", sa.String(50), nullable=True),
        sa.Column("external_id", sa.String(100), nullable=True),
        sa.Column("metadata", postgresql.JSONB(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("shipment_id"),
        sa.ForeignKeyConstraint(
            ["carrier_id"], ["carriers.carrier_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_shipments_carrier_id", "shipments", ["carrier_id"])
    op.create_index("ix_shipments_pro_number", "shipments", ["pro_number"])
    op.create_index("ix_shipments_tracking_number", "shipments", ["tracking_number"])
    op.create_index("ix_shipments_reference_number", "shipments", ["reference_number"])
    op.create_index("ix_shipments_order_number", "shipments", ["order_number"])
    op.create_index("ix_shipments_service_level", "shipments", ["service_level"])
    op.create_index("ix_shipments_ship_date", "shipments", ["ship_date"])
    op.create_index("ix_shipments_external_id", "shipments", ["external_id"])

    # Create invoices table
    op.create_table(
        "invoices",
        sa.Column("invoice_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("carrier_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invoice_number", sa.String(100), nullable=False),
        sa.Column("invoice_date", sa.Date(), nullable=False),
        sa.Column("due_date", sa.Date(), nullable=True),
        sa.Column("total_amount", sa.Numeric(14, 2), nullable=False),
        sa.Column("currency", sa.String(3), nullable=False, server_default="USD"),
        sa.Column(
            "source_type",
            postgresql.ENUM(
                "pdf", "edi", "api", name="sourcetype", create_type=False
            ),
            nullable=False,
            server_default="pdf",
        ),
        sa.Column("source_document_path", sa.String(500), nullable=True),
        sa.Column(
            "processing_status",
            postgresql.ENUM(
                "pending",
                "processing",
                "completed",
                "failed",
                name="processingstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="pending",
        ),
        sa.Column("processing_error", sa.Text(), nullable=True),
        sa.Column("extracted_text", sa.Text(), nullable=True),
        sa.Column("account_number", sa.String(100), nullable=True),
        sa.Column("billing_period_start", sa.Date(), nullable=True),
        sa.Column("billing_period_end", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("invoice_id"),
        sa.ForeignKeyConstraint(
            ["carrier_id"], ["carriers.carrier_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_invoices_carrier_id", "invoices", ["carrier_id"])
    op.create_index("ix_invoices_invoice_number", "invoices", ["invoice_number"])
    op.create_index("ix_invoices_invoice_date", "invoices", ["invoice_date"])
    op.create_index("ix_invoices_processing_status", "invoices", ["processing_status"])

    # Create invoice_lines table
    op.create_table(
        "invoice_lines",
        sa.Column("line_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("invoice_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("shipment_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("line_number", sa.Integer(), nullable=False),
        sa.Column("pro_number", sa.String(100), nullable=True),
        sa.Column("tracking_number", sa.String(100), nullable=True),
        sa.Column("reference_number", sa.String(100), nullable=True),
        sa.Column("service_level", sa.String(100), nullable=True),
        sa.Column("charge_type", sa.String(100), nullable=False),
        sa.Column("charge_description", sa.String(500), nullable=True),
        sa.Column("amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("weight", sa.Numeric(10, 2), nullable=True),
        sa.Column("billed_weight", sa.Numeric(10, 2), nullable=True),
        sa.Column("dimensions", postgresql.JSONB(), nullable=True),
        sa.Column("zone", sa.String(50), nullable=True),
        sa.Column("origin_zip", sa.String(20), nullable=True),
        sa.Column("destination_zip", sa.String(20), nullable=True),
        sa.Column("ship_date", sa.Date(), nullable=True),
        sa.Column("delivery_date", sa.Date(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("line_id"),
        sa.ForeignKeyConstraint(
            ["invoice_id"], ["invoices.invoice_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["shipment_id"], ["shipments.shipment_id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_invoice_lines_invoice_id", "invoice_lines", ["invoice_id"])
    op.create_index("ix_invoice_lines_shipment_id", "invoice_lines", ["shipment_id"])
    op.create_index("ix_invoice_lines_pro_number", "invoice_lines", ["pro_number"])
    op.create_index(
        "ix_invoice_lines_tracking_number", "invoice_lines", ["tracking_number"]
    )
    op.create_index(
        "ix_invoice_lines_reference_number", "invoice_lines", ["reference_number"]
    )

    # Create anomalies table
    op.create_table(
        "anomalies",
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("line_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "anomaly_type",
            postgresql.ENUM(
                "duplicate",
                "rate_error",
                "late_delivery",
                "unauthorized_surcharge",
                "weight_discrepancy",
                "address_correction",
                "service_failure",
                name="anomalytype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("expected_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("actual_amount", sa.Numeric(12, 2), nullable=False),
        sa.Column("variance", sa.Numeric(12, 2), nullable=False),
        sa.Column("confidence_score", sa.Numeric(5, 4), nullable=False),
        sa.Column("contract_reference", sa.String(255), nullable=True),
        sa.Column("contract_term_id", postgresql.UUID(as_uuid=False), nullable=True),
        sa.Column("detection_rule", sa.String(100), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM(
                "detected",
                "validated",
                "dismissed",
                "disputed",
                "resolved",
                name="anomalystatus",
                create_type=False,
            ),
            nullable=False,
            server_default="detected",
        ),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("evidence", sa.Text(), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("resolved_by", sa.String(255), nullable=True),
        sa.Column(
            "duplicate_of_line_id", postgresql.UUID(as_uuid=False), nullable=True
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("anomaly_id"),
        sa.ForeignKeyConstraint(
            ["line_id"], ["invoice_lines.line_id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["contract_term_id"], ["contract_terms.term_id"], ondelete="SET NULL"
        ),
        sa.ForeignKeyConstraint(
            ["duplicate_of_line_id"], ["invoice_lines.line_id"], ondelete="SET NULL"
        ),
    )
    op.create_index("ix_anomalies_line_id", "anomalies", ["line_id"])
    op.create_index("ix_anomalies_anomaly_type", "anomalies", ["anomaly_type"])
    op.create_index("ix_anomalies_status", "anomalies", ["status"])
    op.create_index("ix_anomalies_contract_term_id", "anomalies", ["contract_term_id"])

    # Create claims table
    op.create_table(
        "claims",
        sa.Column("claim_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("anomaly_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("claim_number", sa.String(100), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM(
                "draft",
                "pending_approval",
                "submitted",
                "in_progress",
                "won",
                "lost",
                "withdrawn",
                name="claimstatus",
                create_type=False,
            ),
            nullable=False,
            server_default="draft",
        ),
        sa.Column("claim_text", sa.Text(), nullable=False),
        sa.Column("claim_subject", sa.String(500), nullable=True),
        sa.Column("contract_citation", sa.Text(), nullable=True),
        sa.Column("evidence_references", postgresql.JSONB(), nullable=True),
        sa.Column("requested_credit", sa.Numeric(12, 2), nullable=False),
        sa.Column("submitted_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_date", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "outcome",
            postgresql.ENUM(
                "approved", "denied", "partial", name="claimoutcome", create_type=False
            ),
            nullable=True,
        ),
        sa.Column("credit_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("carrier_reference", sa.String(100), nullable=True),
        sa.Column("resolution_notes", sa.Text(), nullable=True),
        sa.Column("approved_by", sa.String(255), nullable=True),
        sa.Column("approved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("created_by", sa.String(255), nullable=True),
        sa.Column("submitted_by", sa.String(255), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("claim_id"),
        sa.ForeignKeyConstraint(
            ["anomaly_id"], ["anomalies.anomaly_id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint("claim_number"),
    )
    op.create_index("ix_claims_anomaly_id", "claims", ["anomaly_id"])
    op.create_index("ix_claims_claim_number", "claims", ["claim_number"])
    op.create_index("ix_claims_status", "claims", ["status"])

    # Create claim_messages table
    op.create_table(
        "claim_messages",
        sa.Column("message_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column("claim_id", postgresql.UUID(as_uuid=False), nullable=False),
        sa.Column(
            "direction",
            postgresql.ENUM(
                "outbound", "inbound", name="messagedirection", create_type=False
            ),
            nullable=False,
        ),
        sa.Column(
            "message_type",
            postgresql.ENUM(
                "initial_claim",
                "response",
                "inquiry",
                "resolution",
                name="messagetype",
                create_type=False,
            ),
            nullable=False,
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("attachments", postgresql.JSONB(), nullable=True),
        sa.Column("sender", sa.String(255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
        sa.Column(
            "is_auto_generated", sa.Boolean(), nullable=False, server_default="false"
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.PrimaryKeyConstraint("message_id"),
        sa.ForeignKeyConstraint(
            ["claim_id"], ["claims.claim_id"], ondelete="CASCADE"
        ),
    )
    op.create_index("ix_claim_messages_claim_id", "claim_messages", ["claim_id"])


def downgrade() -> None:
    # Drop tables in reverse order
    op.drop_table("claim_messages")
    op.drop_table("claims")
    op.drop_table("anomalies")
    op.drop_table("invoice_lines")
    op.drop_table("invoices")
    op.drop_table("shipments")
    op.drop_table("contract_terms")
    op.drop_table("contracts")
    op.drop_table("carriers")

    # Drop enum types
    op.execute(
        """
        DROP TYPE IF EXISTS messagetype;
        DROP TYPE IF EXISTS messagedirection;
        DROP TYPE IF EXISTS claimoutcome;
        DROP TYPE IF EXISTS claimstatus;
        DROP TYPE IF EXISTS anomalystatus;
        DROP TYPE IF EXISTS anomalytype;
        DROP TYPE IF EXISTS termtype;
        DROP TYPE IF EXISTS sourcetype;
        DROP TYPE IF EXISTS parsingstatus;
        DROP TYPE IF EXISTS processingstatus;
        """
    )
