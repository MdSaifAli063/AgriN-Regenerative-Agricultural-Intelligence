import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class SatelliteObservation(Base):
    __tablename__ = "satellite_observations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    acquisition_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    satellite_name: Mapped[str] = mapped_column(String(64), default="Sentinel-2 L2A")
    cloud_cover_pct: Mapped[float] = mapped_column(Float, nullable=False)
    mean_ndvi: Mapped[float] = mapped_column(Float, nullable=False)
    p10_ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p90_ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_ndwi: Mapped[float] = mapped_column(Float, nullable=False)
    mean_evi: Mapped[float] = mapped_column(Float, nullable=False)
    raw_tile_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    s3_storage_key: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="satellite_observations")


class SoilProfile(Base):
    __tablename__ = "soil_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    data_source: Mapped[str] = mapped_column(String(64), default="ISRIC SoilGrids 250m v2.0")
    depth_interval: Mapped[str] = mapped_column(String(32), default="0-30cm")
    ph_h2o: Mapped[float] = mapped_column(Float, nullable=False)
    soil_organic_carbon_g_kg: Mapped[float] = mapped_column(Float, nullable=False)
    nitrogen_total_g_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cation_exchange_capacity_cmol_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clay_pct: Mapped[float] = mapped_column(Float, nullable=False)
    sand_pct: Mapped[float] = mapped_column(Float, nullable=False)
    silt_pct: Mapped[float] = mapped_column(Float, nullable=False)
    bulk_density_cg_cm3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    plain_language_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    sampled_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="soil_profiles")


class WeatherSnapshot(Base):
    __tablename__ = "weather_snapshots"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    snapshot_date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_min_c: Mapped[float] = mapped_column(Float, nullable=False)
    temp_max_c: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    relative_humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_anomaly_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heat_stress_hours: Mapped[int] = mapped_column(Integer, default=0)
    frost_risk_detected: Mapped[bool] = mapped_column(Boolean, default=False)
    drought_spei_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forecast_type: Mapped[str] = mapped_column(String(32), default="7day_forecast")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="weather_snapshots")
