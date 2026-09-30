import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class RegenerativeAdvisory(Base):
    __tablename__ = "regenerative_advisories"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    advisory_status: Mapped[str] = mapped_column(String(32), default="published")
    confidence_score: Mapped[float] = mapped_column(Float, nullable=False)
    hallucination_guard_passed: Mapped[bool] = mapped_column(Boolean, default=True)
    top_crop_recommendations: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    regenerative_practices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    sowing_window: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    irrigation_schedule: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    organic_fertilizer_plan: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    action_calendar_30days: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, nullable=False)
    data_signals_cited: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    carbon_sequestration_est_t_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    water_conservation_est_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    yield_uplift_est_pct: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    human_in_the_loop_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    disclaimer_notice: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="advisories")


class AgronomyKnowledgeDocument(Base):
    __tablename__ = "agronomy_knowledge_documents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    source_agency: Mapped[str] = mapped_column(String(100), nullable=False)  # FAO, ICAR, EMBRAPA, CAAS
    agrovoc_concept_uri: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    crop_focus: Mapped[Optional[str]] = mapped_column(String(100), nullable=True, index=True)
    climate_zone: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    chunk_index: Mapped[int] = mapped_column(Integer, nullable=False)
    content_chunk: Mapped[str] = mapped_column(Text, nullable=False)
    embedding: Mapped[Optional[List[float]]] = mapped_column(JSON, nullable=True)  # JSON representation for cross-DB compatibility
    metadata_json: Mapped[Dict[str, Any]] = mapped_column("metadata", JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
