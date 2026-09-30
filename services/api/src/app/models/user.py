import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_iso: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="RESTRICT"), nullable=False
    )
    organisation_id: Mapped[Optional[str]] = mapped_column(
        String(36), ForeignKey("organisations.id", ondelete="SET NULL"), nullable=True
    )
    phone_number: Mapped[Optional[str]] = mapped_column(String(32), unique=True, index=True)
    email: Mapped[Optional[str]] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")
    role: Mapped[str] = mapped_column(String(32), default="farmer")  # farmer, extension_officer, government_admin, researcher
    keycloak_sub: Mapped[Optional[str]] = mapped_column(String(36), unique=True, nullable=True)
    is_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    node: Mapped["BricsNode"] = relationship("BricsNode", back_populates="users")
    organisation: Mapped[Optional["Organisation"]] = relationship("Organisation", back_populates="users")
    farms: Mapped[List["Farm"]] = relationship("Farm", back_populates="owner", cascade="all, delete-orphan")
    consent: Mapped[Optional["Consent"]] = relationship("Consent", back_populates="user", uselist=False, cascade="all, delete-orphan")


class Consent(Base):
    __tablename__ = "consents"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    user_id: Mapped[str] = mapped_column(
        String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, unique=True
    )
    share_anonymized_soil: Mapped[bool] = mapped_column(Boolean, default=True)
    share_outbreak_telemetry: Mapped[bool] = mapped_column(Boolean, default=True)
    participate_in_federated_learning: Mapped[bool] = mapped_column(Boolean, default=True)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc)
    )

    user: Mapped["User"] = relationship("User", back_populates="consent")
