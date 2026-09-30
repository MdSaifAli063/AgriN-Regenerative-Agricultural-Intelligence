import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class MLModel(Base):
    __tablename__ = "ml_models"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_name: Mapped[str] = mapped_column(String(150), nullable=False)
    task_type: Mapped[str] = mapped_column(String(64), nullable=False)  # disease_detection, yield_forecast
    license_type: Mapped[str] = mapped_column(String(64), default="Apache-2.0")
    dpg_compliant: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    model_cards: Mapped[List["ModelCard"]] = relationship("ModelCard", back_populates="model", cascade="all, delete-orphan")
    federated_rounds: Mapped[List["FederatedRound"]] = relationship("FederatedRound", back_populates="model", cascade="all, delete-orphan")


class ModelCard(Base):
    __tablename__ = "model_cards"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    version_tag: Mapped[str] = mapped_column(String(32), nullable=False)
    accuracy_score: Mapped[float] = mapped_column(Float, nullable=False)
    f1_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    training_data_summary: Mapped[str] = mapped_column(Text, nullable=False)
    bias_limitations: Mapped[str] = mapped_column(Text, nullable=False)
    s3_weights_uri: Mapped[str] = mapped_column(String(512), nullable=False)
    weights_sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    card_markdown: Mapped[str] = mapped_column(Text, nullable=False)
    published_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    model: Mapped["MLModel"] = relationship("MLModel", back_populates="model_cards")


class FederatedRound(Base):
    __tablename__ = "federated_rounds"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    model_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("ml_models.id", ondelete="CASCADE"), nullable=False, index=True
    )
    round_number: Mapped[int] = mapped_column(Integer, nullable=False)
    participating_nodes: Mapped[List[str]] = mapped_column(JSON, nullable=False)  # ['IN', 'BR', 'ZA']
    aggregation_strategy: Mapped[str] = mapped_column(String(64), default="FedAvg-DP")
    epsilon_privacy_budget: Mapped[float] = mapped_column(Float, default=0.500)
    started_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    model: Mapped["MLModel"] = relationship("MLModel", back_populates="federated_rounds")


class DataSharingAgreement(Base):
    __tablename__ = "data_sharing_agreements"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    signatory_country: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False
    )
    agreement_title: Mapped[str] = mapped_column(String(255), nullable=False)
    terms_url: Mapped[str] = mapped_column(String(512), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    ratified_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ClimateAnalogue(Base):
    __tablename__ = "climate_analogues"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source_region: Mapped[str] = mapped_column(String(150), nullable=False)
    source_country: Mapped[str] = mapped_column(String(3), nullable=False)
    analogue_region: Mapped[str] = mapped_column(String(150), nullable=False)
    analogue_country: Mapped[str] = mapped_column(String(3), nullable=False)
    similarity_index: Mapped[float] = mapped_column(Float, nullable=False)
    successful_regenerative_practices: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ImpactMetric(Base):
    __tablename__ = "impact_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_iso: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False
    )
    recorded_date: Mapped[date] = mapped_column(Date, nullable=False)
    active_farmers_count: Mapped[int] = mapped_column(Integer, nullable=False)
    total_area_under_regeneration_ha: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_water_saved_m3: Mapped[float] = mapped_column(Float, nullable=False)
    estimated_co2e_sequestered_tonnes: Mapped[float] = mapped_column(Float, nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
