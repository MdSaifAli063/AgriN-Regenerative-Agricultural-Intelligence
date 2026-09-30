"""phase4_ai_engine

Revision ID: 002_phase4_ai_engine
Revises: 001_initial_schema
Create Date: 2026-09-29 23:20:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = "002_phase4_ai_engine"
down_revision: Union[str, None] = "001_initial_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    # 1. Update advisories table with versioning, execution trace, and contract JSON
    op.add_column("advisories", sa.Column("prompt_version", sa.String(32), server_default="v1.0.0", nullable=False))
    op.add_column("advisories", sa.Column("engine_mode", sa.String(32), server_default="hybrid", nullable=False))
    op.add_column("advisories", sa.Column("language", sa.String(10), server_default="en", nullable=False))
    op.add_column("advisories", sa.Column("execution_trace", sa.JSON(), server_default="{}", nullable=False))
    op.add_column("advisories", sa.Column("full_advisory_json", sa.JSON(), server_default="{}", nullable=False))

    # 2. Update knowledge_documents with multilingual and tagging metadata
    op.add_column("knowledge_documents", sa.Column("language", sa.String(10), server_default="en", nullable=False))
    op.add_column("knowledge_documents", sa.Column("crop_tags", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("knowledge_documents", sa.Column("region_tags", sa.JSON(), server_default="[]", nullable=False))
    op.add_column("knowledge_documents", sa.Column("published_year", sa.Integer(), nullable=True))

    # 3. Update knowledge_chunks with text search helper
    op.add_column("knowledge_chunks", sa.Column("tsv_content", sa.Text(), nullable=True))

    # 4. Create advisory_feedback table
    op.create_table(
        "advisory_feedback",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("advisory_id", sa.String(36), sa.ForeignKey("advisories.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("user_id", sa.String(36), sa.ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False),
        sa.Column("rating", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text(), nullable=True),
        sa.Column("practices_adopted", sa.JSON(), server_default="[]", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 5. Create token_usage table
    op.create_table(
        "token_usage",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), index=True, nullable=False),
        sa.Column("node_id", sa.String(64), index=True, nullable=False),
        sa.Column("model_name", sa.String(64), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), nullable=False),
        sa.Column("total_tokens", sa.Integer(), nullable=False),
        sa.Column("latency_ms", sa.Float(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
    )

    # 6. Full-Text Search PostgreSQL GIN Index
    if is_postgres:
        op.execute("CREATE INDEX IF NOT EXISTS idx_knowledge_chunks_gin_tsv ON knowledge_chunks USING gin(to_tsvector('english', content_text));")


def downgrade() -> None:
    bind = op.get_bind()
    is_postgres = bind.dialect.name == "postgresql"

    if is_postgres:
        op.execute("DROP INDEX IF EXISTS idx_knowledge_chunks_gin_tsv;")

    op.drop_table("token_usage")
    op.drop_table("advisory_feedback")

    op.drop_column("knowledge_chunks", "tsv_content")
    op.drop_column("knowledge_documents", "published_year")
    op.drop_column("knowledge_documents", "region_tags")
    op.drop_column("knowledge_documents", "crop_tags")
    op.drop_column("knowledge_documents", "language")

    op.drop_column("advisories", "full_advisory_json")
    op.drop_column("advisories", "execution_trace")
    op.drop_column("advisories", "language")
    op.drop_column("advisories", "engine_mode")
    op.drop_column("advisories", "prompt_version")
