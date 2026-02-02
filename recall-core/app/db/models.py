import uuid
from datetime import datetime, timezone

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    Boolean,
    DateTime,
    ForeignKey,
    Index,
    SmallInteger,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from app.config import settings


class Base(DeclarativeBase):
    pass


class Agent(Base):
    __tablename__ = "agents"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    api_key_hash: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    disabled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    trust_level: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    notes: Mapped[str | None] = mapped_column(Text, nullable=True)

    __table_args__ = (Index("ix_agents_name", "name"),)


class Memory(Base):
    __tablename__ = "memories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    short_id: Mapped[str] = mapped_column(Text, unique=True, nullable=False)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    content: Mapped[str] = mapped_column(Text, nullable=False)
    tags: Mapped[list[str]] = mapped_column(ARRAY(Text), nullable=False, server_default=text("'{}'"))
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )
    embedding = mapped_column(Vector(settings.embedding_dim), nullable=False)
    embedding_model: Mapped[str] = mapped_column(Text, nullable=False)
    quality: Mapped[int] = mapped_column(SmallInteger, nullable=False, default=0)
    duplicate_of: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id"), nullable=True
    )

    __table_args__ = (
        Index("ix_memories_tags", "tags", postgresql_using="gin"),
        Index("ix_memories_created_at", "created_at"),
        Index("ix_memories_agent_id", "agent_id"),
        Index("ix_memories_quality", "quality"),
    )


class MemoryLink(Base):
    __tablename__ = "memory_links"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id"), nullable=False
    )
    related_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id"), nullable=False
    )
    relation: Mapped[str] = mapped_column(Text, nullable=False)
    similarity: Mapped[float | None] = mapped_column(nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_memory_links_memory_id", "memory_id"),
        Index("ix_memory_links_related_id", "related_id"),
    )


class SystemConfig(Base):
    __tablename__ = "system_config"

    key: Mapped[str] = mapped_column(Text, primary_key=True)
    value: Mapped[str] = mapped_column(Text, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )


class RetrievalEvent(Base):
    __tablename__ = "retrieval_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    agent_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("agents.id"), nullable=False
    )
    memory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("memories.id"), nullable=False
    )
    query: Mapped[str] = mapped_column(Text, nullable=False)
    similarity: Mapped[float] = mapped_column(nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=text("now()")
    )

    __table_args__ = (
        Index("ix_retrieval_events_memory_id", "memory_id"),
        Index("ix_retrieval_events_agent_id", "agent_id"),
        Index("ix_retrieval_events_created_at", "created_at"),
    )
