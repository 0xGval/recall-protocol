"""Initial schema

Revision ID: 001
Revises:
Create Date: 2025-01-01
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import UUID, ARRAY

revision: str = "001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")

    op.create_table(
        "agents",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("api_key_hash", sa.Text(), unique=True, nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
        sa.Column("disabled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("trust_level", sa.SmallInteger(), nullable=False, server_default=sa.text("0")),
        sa.Column("notes", sa.Text(), nullable=True),
    )
    op.create_index("ix_agents_name", "agents", ["name"])

    # Create memories table via raw SQL to handle vector column properly
    op.execute("""
        CREATE TABLE memories (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            short_id TEXT UNIQUE NOT NULL,
            agent_id UUID NOT NULL REFERENCES agents(id),
            content TEXT NOT NULL,
            tags TEXT[] NOT NULL DEFAULT '{}',
            source_url TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            embedding vector(1536) NOT NULL,
            embedding_model TEXT NOT NULL,
            quality SMALLINT NOT NULL DEFAULT 0,
            duplicate_of UUID REFERENCES memories(id)
        )
    """)
    op.create_index("ix_memories_tags", "memories", ["tags"], postgresql_using="gin")
    op.create_index("ix_memories_created_at", "memories", ["created_at"])
    op.create_index("ix_memories_agent_id", "memories", ["agent_id"])
    op.create_index("ix_memories_quality", "memories", ["quality"])
    op.execute(
        "CREATE INDEX ix_memories_embedding ON memories USING hnsw (embedding vector_cosine_ops)"
    )

    op.create_table(
        "memory_links",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("memory_id", UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("related_id", UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("relation", sa.Text(), nullable=False),
        sa.Column("similarity", sa.REAL(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_memory_links_memory_id", "memory_links", ["memory_id"])
    op.create_index("ix_memory_links_related_id", "memory_links", ["related_id"])

    op.create_table(
        "retrieval_events",
        sa.Column("id", UUID(as_uuid=True), primary_key=True, server_default=sa.text("gen_random_uuid()")),
        sa.Column("agent_id", UUID(as_uuid=True), sa.ForeignKey("agents.id"), nullable=False),
        sa.Column("memory_id", UUID(as_uuid=True), sa.ForeignKey("memories.id"), nullable=False),
        sa.Column("query", sa.Text(), nullable=False),
        sa.Column("similarity", sa.REAL(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()")),
    )
    op.create_index("ix_retrieval_events_memory_id", "retrieval_events", ["memory_id"])
    op.create_index("ix_retrieval_events_agent_id", "retrieval_events", ["agent_id"])
    op.create_index("ix_retrieval_events_created_at", "retrieval_events", ["created_at"])


def downgrade() -> None:
    op.drop_table("retrieval_events")
    op.drop_table("memory_links")
    op.drop_table("memories")
    op.drop_table("agents")
    op.execute("DROP EXTENSION IF EXISTS vector")
