import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class DiseaseDiagnosis(Base):
    __tablename__ = "disease_diagnoses"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="SET NULL"), nullable=True, index=True
    )
    farmer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id"), nullable=False, index=True
    )
    original_image_url: Mapped[str] = mapped_column(String(512), nullable=False)
    edge_model_prediction: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    gemini_vision_prediction: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ensemble_prediction: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    primary_disease_name: Mapped[str] = mapped_column(String(150), nullable=False)
    fao_agrovoc_disease_uri: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severity_rating: Mapped[str] = mapped_column(String(32), default="moderate")  # mild, moderate, critical
    organic_treatment: Mapped[str] = mapped_column(Text, nullable=False)
    chemical_treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chemical_safety_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prevention_measures: Mapped[List[str]] = mapped_column(JSON, default=list)
    spread_risk_level: Mapped[str] = mapped_column(String(32), default="low")  # low, moderate, high, severe
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class DiseaseOutbreak(Base):
    __tablename__ = "disease_outbreaks"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_code: Mapped[str] = mapped_column(String(3), ForeignKey("brics_countries.code"), nullable=False)
    disease_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    affected_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, default=1)
    risk_level: Mapped[str] = mapped_column(String(32), default="moderate")
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    h3_hexagon_index: Mapped[Optional[str]] = mapped_column(String(32), nullable=True, index=True)
    first_detected: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_reported: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    active_advisory: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
