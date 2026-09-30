import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base


class FederatedModelRegistry(Base):
    __tablename__ = "federated_model_registry"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    version: Mapped[str] = mapped_column(String(32), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)  # 'disease_detection', 'yield_forecast'
    participating_countries: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ['IND', 'BRA', 'ZAF']
    global_round_index: Mapped[int] = mapped_column(Integer, nullable=False)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    weights_s3_key: Mapped[str] = mapped_column(String(512), nullable=False)
    model_card_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    dpg_standard_compliant: Mapped[bool] = mapped_column(Boolean, default=True)
    license_type: Mapped[str] = mapped_column(String(64), default="Apache-2.0")
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ClimateAnalogueMatch(Base):
    __tablename__ = "climate_analogue_matches"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_region: Mapped[str] = mapped_column(String(150), nullable=False)
    source_country: Mapped[str] = mapped_column(String(3), nullable=False)
    analogue_region: Mapped[str] = mapped_column(String(150), nullable=False)
    analogue_country: Mapped[str] = mapped_column(String(3), nullable=False)
    bioclimatic_similarity_score: Mapped[float] = mapped_column(Float, nullable=False)
    shared_crop_successes: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    validated_regenerative_practices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
