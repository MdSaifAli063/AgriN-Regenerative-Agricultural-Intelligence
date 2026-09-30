import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False
    )
    farm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    village_district: Mapped[Optional[str]] = mapped_column(String(255))
    state_province: Mapped[str] = mapped_column(String(255), nullable=False)
    country_code: Mapped[str] = mapped_column(String(3), ForeignKey("brics_countries.code"), nullable=False)
    total_area_hectares: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    owner: Mapped["User"] = relationship("User", back_populates="farms")
    fields: Mapped[List["Field"]] = relationship("Field", back_populates="farm", cascade="all, delete-orphan")


class Field(Base):
    __tablename__ = "fields"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farm_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    boundary_geojson: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    irrigation_type: Mapped[str] = mapped_column(String(32), default="rainfed")
    current_crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    previous_crops: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="fields")
    satellite_metrics: Mapped[List["SatelliteMetric"]] = relationship(
        "SatelliteMetric", back_populates="field", cascade="all, delete-orphan"
    )
    soil_profiles: Mapped[List["SoilProfile"]] = relationship(
        "SoilProfile", back_populates="field", cascade="all, delete-orphan"
    )
    weather_records: Mapped[List["WeatherRecord"]] = relationship(
        "WeatherRecord", back_populates="field", cascade="all, delete-orphan"
    )
    advisories: Mapped[List["RegenerativeAdvisory"]] = relationship(
        "RegenerativeAdvisory", back_populates="field", cascade="all, delete-orphan"
    )


class SatelliteMetric(Base):
    __tablename__ = "satellite_metrics"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    acquisition_date: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    satellite_source: Mapped[str] = mapped_column(String(64), default="Sentinel-2 L2A")
    cloud_coverage_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    mean_ndvi: Mapped[float] = mapped_column(Float, nullable=False)
    p10_ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    p90_ndvi: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    mean_ndwi: Mapped[float] = mapped_column(Float, nullable=False)
    mean_evi: Mapped[float] = mapped_column(Float, nullable=False)
    tile_geojson: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON, nullable=True)
    storage_thumbnail_url: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="satellite_metrics")


class SoilProfile(Base):
    __tablename__ = "soil_profiles"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    source: Mapped[str] = mapped_column(String(64), default="ISRIC SoilGrids 250m v2.0")
    depth_slice: Mapped[str] = mapped_column(String(32), default="0-30cm")
    ph_water: Mapped[float] = mapped_column(Float, nullable=False)
    organic_carbon_g_kg: Mapped[float] = mapped_column(Float, nullable=False)
    total_nitrogen_g_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    cation_exchange_capacity_cmolc_kg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    clay_fraction_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    sand_fraction_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    silt_fraction_percentage: Mapped[float] = mapped_column(Float, nullable=False)
    texture_class: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    bulk_density_g_cm3: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    soil_health_score: Mapped[int] = mapped_column(Integer, nullable=False)
    score_interpretation: Mapped[str] = mapped_column(Text, nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="soil_profiles")


class WeatherRecord(Base):
    __tablename__ = "weather_records"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    record_date: Mapped[date] = mapped_column(Date, nullable=False)
    temp_min_celsius: Mapped[float] = mapped_column(Float, nullable=False)
    temp_max_celsius: Mapped[float] = mapped_column(Float, nullable=False)
    precipitation_mm: Mapped[float] = mapped_column(Float, nullable=False)
    relative_humidity_pct: Mapped[float] = mapped_column(Float, nullable=False)
    wind_speed_kmh: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    rainfall_anomaly_pct: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    heat_stress_hours: Mapped[int] = mapped_column(Integer, default=0)
    frost_risk_flag: Mapped[bool] = mapped_column(Boolean, default=False)
    drought_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    forecast_horizon_days: Mapped[int] = mapped_column(Integer, default=7)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="weather_records")
