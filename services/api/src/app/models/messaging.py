"""
SQLAlchemy models for Phase 8 Messaging Gateway, Broadcasts, and Session FSM.
Single source of truth with Phase 1 message_sessions backwards compatibility.
"""

from datetime import datetime, timezone
import uuid
from typing import Any, Dict, Optional
from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, String, Text, JSON, Numeric
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base


class MessageSession(Base):
    """
    Stateful conversational session for WhatsApp / SMS farmers.
    Maintains FSM state, context memory, and data privacy guarantees.
    """
    __tablename__ = "message_sessions"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    # Phase 1 backwards compatibility
    phone_number: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp", index=True)  # whatsapp, sms, simulator
    session_state: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    last_interaction: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        index=True
    )

    # Phase 8 Data Minimisation & Sovereign Enhancements
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)  # Salted SHA-256 for O(1) lookup
    phone_encrypted: Mapped[Optional[str]] = mapped_column(Text, nullable=True)     # Fernet ciphertext for outbound reply
    preferred_language: Mapped[str] = mapped_column(String(10), default="en")       # 12 BRICS/African locales
    current_state: Mapped[str] = mapped_column(String(32), default="NEW", index=True)# FSM State
    previous_state: Mapped[Optional[str]] = mapped_column(String(32), nullable=True) # Enables 0=Back navigation
    context_data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)        # FSM slot data (crop, location, coords)
    
    # Consent and Safety
    opt_out: Mapped[bool] = mapped_column(Boolean, default=False, index=True)        # Instant STOP/ROKO/PARE flag
    consent_granted: Mapped[bool] = mapped_column(Boolean, default=False)
    consent_receipt_code: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    consent_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)

    # Lightweight messaging farmer profile
    is_farmer_linked: Mapped[bool] = mapped_column(Boolean, default=False)
    linked_user_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)
    linked_field_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True, index=True)


class InboundMessage(Base):
    """
    Log of inbound messages received across providers.
    Body text is subject to configured retention purging.
    """
    __tablename__ = "inbound_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)  # twilio, meta, africastalking, simulator
    provider_message_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    from_phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    message_type: Mapped[str] = mapped_column(String(32), default="text")  # text, location, image, voice
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)       # Purged after retention window
    media_url: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    raw_payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    processed_status: Mapped[str] = mapped_column(String(32), default="received")  # received, processed, ignored, error
    received_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    processed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class OutboundMessage(Base):
    """
    Audit record of all outbound SMS/WhatsApp dispatches, segment counts, and costs.
    """
    __tablename__ = "outbound_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    provider_message_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True, index=True)
    to_phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    message_type: Mapped[str] = mapped_column(String(32), default="text")  # text, template, media
    body: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    segments_count: Mapped[int] = mapped_column(Integer, default=1)
    cost_estimate_usd: Mapped[float] = mapped_column(Float, default=0.0)
    status: Mapped[str] = mapped_column(
        String(32), default="queued", index=True
    )  # queued, sent, delivered, failed, dropped_quiet_hours, dropped_budget
    error_reason: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    delivered_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class DeadLetterMessage(Base):
    """
    Dead-letter queue for failed outbound and inbound message processing.
    Inspectable via Admin API.
    """
    __tablename__ = "dead_letter_messages"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    source: Mapped[str] = mapped_column(String(32), default="outbound")  # inbound, outbound
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    payload: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
    error_message: Mapped[str] = mapped_column(Text, nullable=False)
    retry_count: Mapped[int] = mapped_column(Integer, default=0)
    resolved: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )


class BroadcastCampaign(Base):
    """
    Officer-initiated mass agricultural alert campaigns (Closing Phase 6 gap).
    """
    __tablename__ = "broadcast_campaigns"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    officer_user_id: Mapped[str] = mapped_column(String(36), nullable=False, index=True)
    jurisdiction_district: Mapped[str] = mapped_column(String(128), nullable=False, index=True)
    target_crop: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    target_language: Mapped[Optional[str]] = mapped_column(String(10), nullable=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    body_template: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(32), default="queued")  # preview, queued, running, completed, failed
    recipient_count: Mapped[int] = mapped_column(Integer, default=0)
    sent_count: Mapped[int] = mapped_column(Integer, default=0)
    failed_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc), index=True
    )
    completed_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)


class MessagingCostLedger(Base):
    """
    Daily aggregated expenditure ledger for messaging gateway kill switch guard.
    """
    __tablename__ = "messaging_cost_ledger"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    date: Mapped[str] = mapped_column(String(10), nullable=False, index=True)  # YYYY-MM-DD
    provider: Mapped[str] = mapped_column(String(32), nullable=False)
    message_count: Mapped[int] = mapped_column(Integer, default=0)
    cost_usd: Mapped[float] = mapped_column(Float, default=0.0)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ChatConsentReceipt(Base):
    """
    Cryptographic / hash verification receipts for farmer consent given in-chat.
    """
    __tablename__ = "chat_consent_receipts"

    id: Mapped[str] = mapped_column(
        String(36), primary_key=True, default=lambda: str(uuid.uuid4())
    )
    receipt_code: Mapped[str] = mapped_column(String(32), unique=True, index=True)
    phone_hash: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    consent_version: Mapped[str] = mapped_column(String(32), default="CONSENT-V1.0-MESSAGING")
    channel: Mapped[str] = mapped_column(String(32), default="whatsapp")
    granted_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    revoked_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True), nullable=True)
    audit_id: Mapped[Optional[str]] = mapped_column(String(36), nullable=True)
