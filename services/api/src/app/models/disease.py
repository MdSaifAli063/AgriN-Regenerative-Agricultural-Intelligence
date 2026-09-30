import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class DiseaseDetection(Base):
    __tablename__ = "disease_detections"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="SET NULL"), nullable=True, index=True
    )
    image_s3_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    edge_prediction: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    gemini_vision_prediction: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    ensemble_prediction: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    primary_disease_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    fao_agrovoc_uri: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    severity_level: Mapped[str] = mapped_column(String(32), default="moderate")  # mild, moderate, critical
    organic_treatment: Mapped[str] = mapped_column(Text, nullable=False)
    chemical_treatment: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    chemical_safety_warning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    prevention_measures: Mapped[List[str]] = mapped_column(JSON, default=list)
    spread_risk_score: Mapped[str] = mapped_column(String(32), default="low")  # low, moderate, high, severe
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    ensemble_confidence: Mapped[float] = mapped_column(Float, default=0.0)
    # Offline sync idempotency key (client-generated UUID)
    offline_client_id: Mapped[Optional[str]] = mapped_column(
        String(36), nullable=True, index=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class OutbreakAggregate(Base):
    __tablename__ = "outbreak_aggregates"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_iso: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False
    )
    disease_name: Mapped[str] = mapped_column(String(150), nullable=False, index=True)
    affected_crop: Mapped[str] = mapped_column(String(100), nullable=False)
    incident_count: Mapped[int] = mapped_column(Integer, default=1)
    risk_severity: Mapped[str] = mapped_column(String(32), default="moderate")
    h3_hex_index: Mapped[str] = mapped_column(String(32), nullable=False, index=True)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    period_start: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    period_end: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
