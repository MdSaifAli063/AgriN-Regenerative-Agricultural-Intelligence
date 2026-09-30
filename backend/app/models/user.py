import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.core.database import Base


class BricsCountry(Base):
    __tablename__ = "brics_countries"

    code: Mapped[str] = mapped_column(String(3), primary_key=True)  # IND, BRA, ZAF, CHN, RUS, etc.
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    national_registry_url: Mapped[str] = mapped_column(String(255), nullable=False)
    contact_agency: Mapped[str] = mapped_column(String(255), nullable=False)
    public_signing_key: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    users: Mapped[List["User"]] = relationship("User", back_populates="country")


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_code: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_countries.code"), nullable=False
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    role: Mapped[str] = mapped_column(String(32), default="farmer")
    keycloak_sub: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    country: Mapped["BricsCountry"] = relationship("BricsCountry", back_populates="users")
    farms: Mapped[List["Farm"]] = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")
    consent: Mapped[Optional["FarmerConsent"]] = relationship("FarmerConsent", back_populates="farmer", uselist=False)


class FarmerConsent(Base):
    __tablename__ = "farmer_consents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    farmer_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    share_anonymized_soil: Mapped[bool] = mapped_column(Boolean, default=True)
    share_disease_telemetry: Mapped[bool] = mapped_column(Boolean, default=True)
    participate_in_federated_learning: Mapped[bool] = mapped_column(Boolean, default=True)
    consent_timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    farmer: Mapped["User"] = relationship("User", back_populates="consent")
