import uuid
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from sqlalchemy import Date, DateTime, Float, ForeignKey, Numeric, String, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class Farm(Base):
    __tablename__ = "farms"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    farm_name: Mapped[str] = mapped_column(String(255), nullable=False)
    village_district: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    state_province: Mapped[str] = mapped_column(String(255), nullable=False)
    country_iso: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False
    )
    total_area_hectares: Mapped[float] = mapped_column(Float, default=0.0)
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
        String(36), ForeignKey("farms.id", ondelete="CASCADE"), nullable=False, index=True
    )
    field_name: Mapped[str] = mapped_column(String(100), nullable=False)
    boundary_geojson: Mapped[Dict[str, Any]] = mapped_column(JSON, nullable=False)
    centroid_lat: Mapped[float] = mapped_column(Float, nullable=False)
    centroid_lon: Mapped[float] = mapped_column(Float, nullable=False)
    area_hectares: Mapped[float] = mapped_column(Float, nullable=False)
    irrigation_type: Mapped[str] = mapped_column(String(32), default="rainfed")  # rainfed, drip, sprinkler, furrow
    current_crop: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    farm: Mapped["Farm"] = relationship("Farm", back_populates="fields")
    crop_history: Mapped[List["CropHistory"]] = relationship("CropHistory", back_populates="field", cascade="all, delete-orphan")
    satellite_observations: Mapped[List["SatelliteObservation"]] = relationship(
        "SatelliteObservation", back_populates="field", cascade="all, delete-orphan"
    )
    soil_profiles: Mapped[List["SoilProfile"]] = relationship(
        "SoilProfile", back_populates="field", cascade="all, delete-orphan"
    )
    weather_snapshots: Mapped[List["WeatherSnapshot"]] = relationship(
        "WeatherSnapshot", back_populates="field", cascade="all, delete-orphan"
    )
    advisories: Mapped[List["Advisory"]] = relationship(
        "Advisory", back_populates="field", cascade="all, delete-orphan"
    )


class CropHistory(Base):
    __tablename__ = "crop_history"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    field_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("fields.id", ondelete="CASCADE"), nullable=False, index=True
    )
    crop_name: Mapped[str] = mapped_column(String(100), nullable=False)
    fao_agrovoc_uri: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    season_name: Mapped[str] = mapped_column(String(64), nullable=False)
    sowing_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    harvest_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    yield_kg_ha: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    fertilizers_applied: Mapped[List[Dict[str, Any]]] = mapped_column(JSON, default=list)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    field: Mapped["Field"] = relationship("Field", back_populates="crop_history")
