"""
Abstract Base Messaging Provider Interface and Data Transfer Objects.
Defines strict contract for Twilio, Meta WhatsApp Cloud, Africa's Talking, and Simulator.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class InboundMessageDTO:
    """Standardized representation of an inbound message from any provider."""
    provider: str
    provider_message_id: str
    from_phone: str
    to_phone: str
    channel: str  # 'whatsapp', 'sms'
    message_type: str  # 'text', 'location', 'image', 'voice'
    body: Optional[str] = None
    media_url: Optional[str] = None
    media_id: Optional[str] = None
    media_content_type: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    raw_payload: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


@dataclass
class OutboundResult:
    """Outcome of an outbound dispatch attempt."""
    success: bool
    provider: str
    provider_message_id: Optional[str] = None
    to_phone: str = ""
    channel: str = "whatsapp"
    segments_count: int = 1
    cost_estimate_usd: float = 0.0
    status: str = "sent"  # 'sent', 'queued', 'failed', 'dropped'
    error_message: Optional[str] = None


@dataclass
class DeliveryStatusDTO:
    """Standardized delivery status callback from provider."""
    provider: str
    provider_message_id: str
    status: str  # 'sent', 'delivered', 'read', 'failed', 'undelivered'
    error_code: Optional[str] = None
    error_message: Optional[str] = None
    timestamp: datetime = field(default_factory=lambda: datetime.now(timezone.utc))


class MessagingProvider(ABC):
    """Abstract messaging provider interface."""

    provider_name: str = "base"

    @abstractmethod
    async def send_text(
        self,
        to: str,
        text: str,
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        """Sends plain text message (or SMS segments)."""
        pass

    @abstractmethod
    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        parameters: Dict[str, Any],
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        """Sends pre-approved business initiated template (WhatsApp)."""
        pass

    @abstractmethod
    async def send_media(
        self,
        to: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        """Sends outbound image, document, or audio media message."""
        pass

    @abstractmethod
    def parse_inbound(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> InboundMessageDTO:
        """Parses raw webhook body and headers into normalized InboundMessageDTO."""
        pass

    @abstractmethod
    def verify_signature(
        self,
        url: str,
        params: Dict[str, Any],
        body_bytes: bytes,
        headers: Dict[str, str],
        secret: Optional[str] = None
    ) -> bool:
        """Verifies cryptographic signature of incoming webhook to prevent tampering/spoofing."""
        pass

    @abstractmethod
    async def download_media(
        self,
        media_id_or_url: str
    ) -> bytes:
        """Downloads incoming media (leaf photos, voice notes) with provider authentication."""
        pass
