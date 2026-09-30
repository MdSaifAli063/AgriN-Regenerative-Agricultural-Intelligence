import uuid
from datetime import datetime, timezone
from typing import List, Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class BricsNode(Base):
    __tablename__ = "brics_nodes"

    country_iso: Mapped[str] = mapped_column(String(3), primary_key=True)
    country_name: Mapped[str] = mapped_column(String(100), nullable=False)
    lead_agency: Mapped[str] = mapped_column(String(255), nullable=False)
    node_base_url: Mapped[str] = mapped_column(String(255), nullable=False)
    public_x509_cert: Mapped[str] = mapped_column(Text, nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    organisations: Mapped[List["Organisation"]] = relationship("Organisation", back_populates="node")
    users: Mapped[List["User"]] = relationship("User", back_populates="node")


class Organisation(Base):
    __tablename__ = "organisations"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    country_iso: Mapped[str] = mapped_column(
        String(3), ForeignKey("brics_nodes.country_iso", ondelete="CASCADE"), nullable=False
    )
    org_name: Mapped[str] = mapped_column(String(255), nullable=False)
    org_type: Mapped[str] = mapped_column(String(64), nullable=False)  # research_institute, extension_department
    contact_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )

    node: Mapped["BricsNode"] = relationship("BricsNode", back_populates="organisations")
    users: Mapped[List["User"]] = relationship("User", back_populates="organisation")
