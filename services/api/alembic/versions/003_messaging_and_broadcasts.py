"""messaging_and_broadcasts

Revision ID: 003_messaging_and_broadcasts
Revises: 002_phase4_ai_engine
Create Date: 2026-09-30 22:30:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "003_messaging_and_broadcasts"
down_revision: Union[str, None] = "002_phase4_ai_engine"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enhance message_sessions with data minimisation, encryption, and FSM tracking
    with op.batch_alter_table("message_sessions") as batch_op:
        batch_op.add_column(sa.Column("phone_hash", sa.String(64), nullable=True))
        batch_op.add_column(sa.Column("phone_encrypted", sa.Text(), nullable=True))
        batch_op.add_column(sa.Column("preferred_language", sa.String(10), server_default="en", nullable=False))
        batch_op.add_column(sa.Column("current_state", sa.String(32), server_default="NEW", nullable=False))
        batch_op.add_column(sa.Column("previous_state", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("context_data", sa.JSON(), server_default="{}", nullable=False))
        batch_op.add_column(sa.Column("opt_out", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("consent_granted", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("consent_receipt_code", sa.String(32), nullable=True))
        batch_op.add_column(sa.Column("consent_timestamp", sa.DateTime(timezone=True), nullable=True))
        batch_op.add_column(sa.Column("is_farmer_linked", sa.Boolean(), server_default="0", nullable=False))
        batch_op.add_column(sa.Column("linked_user_id", sa.String(36), nullable=True))
        batch_op.add_column(sa.Column("linked_field_id", sa.String(36), nullable=True))
        batch_op.create_index("ix_message_sessions_phone_hash", ["phone_hash"])
        batch_op.create_index("ix_message_sessions_current_state", ["current_state"])
        batch_op.create_index("ix_message_sessions_opt_out", ["opt_out"])

    # 2. Inbound messages table
    op.create_table(
        "inbound_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_message_id", sa.String(128), unique=True, nullable=False),
        sa.Column("from_phone_hash", sa.String(64), nullable=False, index=True),
        sa.Column("channel", sa.String(32), server_default="whatsapp", nullable=False),
        sa.Column("message_type", sa.String(32), server_default="text", nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("media_url", sa.Text(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("processed_status", sa.String(32), server_default="received", nullable=False),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("processed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 3. Outbound messages table
    op.create_table(
        "outbound_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("provider_message_id", sa.String(128), nullable=True, index=True),
        sa.Column("to_phone_hash", sa.String(64), nullable=False, index=True),
        sa.Column("channel", sa.String(32), server_default="whatsapp", nullable=False),
        sa.Column("message_type", sa.String(32), server_default="text", nullable=False),
        sa.Column("body", sa.Text(), nullable=True),
        sa.Column("segments_count", sa.Integer(), server_default="1", nullable=False),
        sa.Column("cost_estimate_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False, index=True),
        sa.Column("error_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("delivered_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 4. Dead-letter messages queue
    op.create_table(
        "dead_letter_messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("source", sa.String(32), server_default="outbound", nullable=False),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("payload", sa.JSON(), server_default="{}", nullable=False),
        sa.Column("error_message", sa.Text(), nullable=False),
        sa.Column("retry_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("resolved", sa.Boolean(), server_default="0", nullable=False, index=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
    )

    # 5. Broadcast campaigns
    op.create_table(
        "broadcast_campaigns",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("officer_user_id", sa.String(36), nullable=False, index=True),
        sa.Column("jurisdiction_district", sa.String(128), nullable=False, index=True),
        sa.Column("target_crop", sa.String(64), nullable=True),
        sa.Column("target_language", sa.String(10), nullable=True),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("body_template", sa.Text(), nullable=False),
        sa.Column("status", sa.String(32), server_default="queued", nullable=False),
        sa.Column("recipient_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("sent_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("failed_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, index=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
    )

    # 6. Messaging cost ledger
    op.create_table(
        "messaging_cost_ledger",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("date", sa.String(10), nullable=False, index=True),
        sa.Column("provider", sa.String(32), nullable=False),
        sa.Column("message_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("cost_usd", sa.Float(), server_default="0.0", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )

    # 7. Chat consent receipts
    op.create_table(
        "chat_consent_receipts",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("receipt_code", sa.String(32), unique=True, nullable=False, index=True),
        sa.Column("phone_hash", sa.String(64), nullable=False, index=True),
        sa.Column("consent_version", sa.String(32), server_default="CONSENT-V1.0-MESSAGING", nullable=False),
        sa.Column("channel", sa.String(32), server_default="whatsapp", nullable=False),
        sa.Column("granted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("audit_id", sa.String(36), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("chat_consent_receipts")
    op.drop_table("messaging_cost_ledger")
    op.drop_table("broadcast_campaigns")
    op.drop_table("dead_letter_messages")
    op.drop_table("outbound_messages")
    op.drop_table("inbound_messages")
    with op.batch_alter_table("message_sessions") as batch_op:
        batch_op.drop_index("ix_message_sessions_opt_out")
        batch_op.drop_index("ix_message_sessions_current_state")
        batch_op.drop_index("ix_message_sessions_phone_hash")
        batch_op.drop_column("linked_field_id")
        batch_op.drop_column("linked_user_id")
        batch_op.drop_column("is_farmer_linked")
        batch_op.drop_column("consent_timestamp")
        batch_op.drop_column("consent_receipt_code")
        batch_op.drop_column("consent_granted")
        batch_op.drop_column("opt_out")
        batch_op.drop_column("context_data")
        batch_op.drop_column("previous_state")
        batch_op.drop_column("current_state")
        batch_op.drop_column("preferred_language")
        batch_op.drop_column("phone_encrypted")
        batch_op.drop_column("phone_hash")
