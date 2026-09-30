import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Advisory(Base):
    __tablename__ = "advisories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    hallucination_guard_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    top_3_crops: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    regenerative_practices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    sowing_window: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    irrigation_schedule: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    organic_fertilizer_plan: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    explainability_signals: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    carbon_sequestration_t_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    water_saved_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yield_uplift_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    disclaimer_note: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(String(32), default="v1.0.0", nullable=False)
    engine_mode: Mapped[str] = mapped_column(String(32), default="hybrid", nullable=False)
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    execution_trace: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    full_advisory_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="advisories")
    actions: Mapped[List["AdvisoryAction"]] = relationship(
        "AdvisoryAction", back_populates="advisory", cascade="all, delete-orphan"
    )
    feedback: Mapped[List["AdvisoryFeedback"]] = relationship(
        "AdvisoryFeedback", back_populates="advisory", cascade="all, delete-orphan"
    )


class AdvisoryAction(Base):
    __tablename__ = "advisory_actions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    advisory_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advisories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    calendar_day: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 30
    action_title: Mapped[str] = mapped_column(String(255), nullable=False)
    action_description: Mapped[str] = mapped_column(Text, nullable=False)
    category: Mapped[str] = mapped_column(String(64), nullable=False)  # soil, irrigation, ipm, sowing
    is_completed: Mapped[bool] = mapped_column(Boolean, default=False)
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    advisory: Mapped["Advisory"] = relationship("Advisory", back_populates="actions")


class AdvisoryFeedback(Base):
    __tablename__ = "advisory_feedback"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    advisory_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("advisories.id", ondelete="CASCADE"), nullable=False, index=True
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    rating: Mapped[int] = mapped_column(Integer, nullable=False)  # 1 to 5 stars
    comment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    practices_adopted: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    advisory: Mapped["Advisory"] = relationship("Advisory", back_populates="feedback")


class TokenUsage(Base):
    __tablename__ = "token_usage"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(String(36), index=True, nullable=False)
    node_id: Mapped[str] = mapped_column(String(64), index=True, nullable=False)
    model_name: Mapped[str] = mapped_column(String(64), nullable=False)
    prompt_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    completion_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    total_tokens: Mapped[int] = mapped_column(Integer, nullable=False)
    latency_ms: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class KnowledgeDocument(Base):
    __tablename__ = "knowledge_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    publishing_agency: Mapped[str] = mapped_column(String(100), nullable=False)  # FAO, ICAR, EMBRAPA, CAAS
    source_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    license_type: Mapped[str] = mapped_column(String(64), default="CC-BY-4.0")
    language: Mapped[str] = mapped_column(String(10), default="en", nullable=False)
    crop_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    region_tags: Mapped[List[str]] = mapped_column(JSON, default=list, nullable=False)
    published_year: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    chunks: Mapped[List["KnowledgeChunk"]] = relationship(
        "KnowledgeChunk", back_populates="document", cascade="all, delete-orphan"
    )


class KnowledgeChunk(Base):
    __tablename__ = "knowledge_chunks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    document_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("knowledge_documents.id", ondelete="CASCADE"), nullable=False, index=True
    )
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_text: Mapped[str] = mapped_column(Text, nullable=False)
    fao_agrovoc_concept: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    target_crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    climate_zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)
    metadata_json: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    tsv_content: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    document: Mapped["KnowledgeDocument"] = relationship("KnowledgeDocument", back_populates="chunks")
