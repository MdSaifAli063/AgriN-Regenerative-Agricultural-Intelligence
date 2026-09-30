"""
Simulator Messaging Provider for DEMO_MODE and Local Testing.
Requires zero external API credentials or internet connectivity.
Provides:
1. In-memory outbox inspection.
2. Synthetic leaf photo and voice note mock generation.
3. Accurate simulated cost accounting.
"""

from datetime import datetime, timezone
import io
import uuid
from typing import Any, Dict, List, Optional
from PIL import Image
from app.messaging.providers.base import (
    DeliveryStatusDTO,
    InboundMessageDTO,
    MessagingProvider,
    OutboundResult,
)
from app.messaging.segment_calc import calculate_segments


class SimulatorProvider(MessagingProvider):
    provider_name: str = "simulator"

    def __init__(self) -> None:
        self.outbox: List[Dict[str, Any]] = []
        self.dead_letters: List[Dict[str, Any]] = []

    def clear(self) -> None:
        """Clears in-memory simulator queues."""
        self.outbox.clear()
        self.dead_letters.clear()

    async def send_text(
        self,
        to: str,
        text: str,
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        seg_info = calculate_segments(text)
        segments = int(seg_info["segments"])
        cost = 0.0075 * segments if channel == "sms" else 0.005

        msg_id = f"sim-{uuid.uuid4().hex[:12]}"
        record = {
            "id": msg_id,
            "to": to,
            "channel": channel,
            "text": text,
            "type": "text",
            "segments": segments,
            "cost_usd": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.outbox.append(record)

        return OutboundResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=msg_id,
            to_phone=to,
            channel=channel,
            segments_count=segments,
            cost_estimate_usd=cost,
            status="sent",
        )

    async def send_template(
        self,
        to: str,
        template_name: str,
        language: str,
        parameters: Dict[str, Any],
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        msg_id = f"sim-tmpl-{uuid.uuid4().hex[:12]}"
        cost = 0.015  # Template marketing/utility tier
        record = {
            "id": msg_id,
            "to": to,
            "channel": channel,
            "template": template_name,
            "language": language,
            "parameters": parameters,
            "type": "template",
            "segments": 1,
            "cost_usd": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.outbox.append(record)

        return OutboundResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=msg_id,
            to_phone=to,
            channel=channel,
            segments_count=1,
            cost_estimate_usd=cost,
            status="sent",
        )

    async def send_media(
        self,
        to: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        msg_id = f"sim-media-{uuid.uuid4().hex[:12]}"
        cost = 0.02
        record = {
            "id": msg_id,
            "to": to,
            "channel": channel,
            "media_url": media_url,
            "caption": caption,
            "media_type": media_type,
            "type": "media",
            "segments": 1,
            "cost_usd": cost,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self.outbox.append(record)

        return OutboundResult(
            success=True,
            provider=self.provider_name,
            provider_message_id=msg_id,
            to_phone=to,
            channel=channel,
            segments_count=1,
            cost_estimate_usd=cost,
            status="sent",
        )

    def parse_inbound(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> InboundMessageDTO:
        msg_id = payload.get("id") or f"sim-in-{uuid.uuid4().hex[:10]}"
        return InboundMessageDTO(
            provider=self.provider_name,
            provider_message_id=msg_id,
            from_phone=payload.get("from", "+919876543210"),
            to_phone=payload.get("to", "+911140001234"),
            channel=payload.get("channel", "whatsapp"),
            message_type=payload.get("type", "text"),
            body=payload.get("text"),
            media_url=payload.get("media_url"),
            media_id=payload.get("media_id"),
            latitude=payload.get("latitude"),
            longitude=payload.get("longitude"),
            raw_payload=payload,
        )

    def verify_signature(
        self,
        url: str,
        params: Dict[str, Any],
        body_bytes: bytes,
        headers: Dict[str, str],
        secret: Optional[str] = None
    ) -> bool:
        # In simulator mode, check for explicit rejection test or valid simulator token
        sig = headers.get("X-Simulator-Signature") or headers.get("x-simulator-signature")
        if sig == "invalid_signature":
            return False
        return True

    async def download_media(
        self,
        media_id_or_url: str
    ) -> bytes:
        """Generates synthetic leaf photo JPEG or synthetic audio bytes."""
        if "audio" in media_id_or_url.lower() or "voice" in media_id_or_url.lower():
            # Minimal valid WAV header + silence
            # 44 bytes header + sample data
            wav_header = (
                b"RIFF\x24\x00\x00\x00WAVEfmt \x10\x00\x00\x00\x01\x00\x01\x00"
                b"\x44\xac\x00\x00\x88\x58\x01\x00\x02\x00\x10\x00data\x00\x00\x00\x00"
            )
            return wav_header

        # Generate a 224x224 synthetic leaf image (green with yellow lesions for crop demo)
        img = Image.new("RGB", (224, 224), color=(34, 139, 34))  # Forest green
        # Add slight yellow/brown spots to simulate disease lesions
        for x in range(80, 140):
            for y in range(80, 140):
                img.putpixel((x, y), (189, 183, 107))
        buf = io.BytesIO()
        img.save(buf, format="JPEG")
        return buf.getvalue()
