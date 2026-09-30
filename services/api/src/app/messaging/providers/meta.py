"""
Meta WhatsApp Cloud API Provider.
Implements:
1. Webhook GET verification challenge handler.
2. X-Hub-Signature-256 HMAC-SHA256 signature validation.
3. Graph API v20.0 inbound message payload parsing.
4. Business template and session media dispatch.
5. Authenticated media retrieval.
"""

import hashlib
import hmac
import logging
from typing import Any, Dict, Optional
import httpx
from app.core.config import settings
from app.messaging.providers.base import (
    InboundMessageDTO,
    MessagingProvider,
    OutboundResult,
)

logger = logging.getLogger("krishinet.messaging.meta")


class MetaCloudProvider(MessagingProvider):
    provider_name: str = "meta"

    def __init__(
        self,
        token: Optional[str] = None,
        phone_number_id: Optional[str] = None,
        app_secret: Optional[str] = None,
        verify_token: Optional[str] = None,
    ) -> None:
        self.token = token or settings.META_WHATSAPP_TOKEN or "dummy_meta_token"
        self.phone_number_id = phone_number_id or settings.META_WHATSAPP_PHONE_NUMBER_ID or "100000000000001"
        self.app_secret = app_secret or settings.META_APP_SECRET or "dummy_meta_app_secret"
        self.verify_token = verify_token or settings.META_WEBHOOK_VERIFY_TOKEN or "krishinet_meta_verify_token_2026"

    def verify_challenge(self, mode: str, token: str, challenge: str) -> Optional[str]:
        """Handles Meta webhook verification handshake."""
        if mode == "subscribe" and token == self.verify_token:
            return challenge
        return None

    def verify_signature(
        self,
        url: str,
        params: Dict[str, Any],
        body_bytes: bytes,
        headers: Dict[str, str],
        secret: Optional[str] = None
    ) -> bool:
        """
        Validates X-Hub-Signature-256 header (sha256=<hex_digest>) against raw request bytes.
        """
        app_sec = secret or self.app_secret
        header_sig = headers.get("X-Hub-Signature-256") or headers.get("x-hub-signature-256")
        if not header_sig or not header_sig.startswith("sha256="):
            return False

        expected_hash = header_sig[7:].strip()
        computed_hash = hmac.new(app_sec.encode("utf-8"), body_bytes, hashlib.sha256).hexdigest()
        return hmac.compare_digest(computed_hash, expected_hash)

    async def send_text(
        self,
        to: str,
        text: str,
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        clean_to = to.replace("+", "").strip()
        if settings.DEMO_MODE or self.token.startswith("dummy_"):
            return OutboundResult(
                success=True,
                provider=self.provider_name,
                provider_message_id=f"wamid.mock.{clean_to[-4:]}",
                to_phone=to,
                channel="whatsapp",
                segments_count=1,
                cost_estimate_usd=0.005,
                status="sent",
            )

        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": "text",
            "text": {"preview_url": False, "body": text},
        }

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, json=payload, headers=headers)
                if resp.status_code in [200, 201]:
                    data = resp.json()
                    wamid = data.get("messages", [{}])[0].get("id", f"wamid.{clean_to[-4:]}")
                    return OutboundResult(
                        success=True,
                        provider=self.provider_name,
                        provider_message_id=wamid,
                        to_phone=to,
                        channel="whatsapp",
                        segments_count=1,
                        cost_estimate_usd=0.005,
                        status="sent",
                    )
                logger.error(f"Meta Graph API error {resp.status_code}: {resp.text}")
                return OutboundResult(
                    success=False,
                    provider=self.provider_name,
                    to_phone=to,
                    channel="whatsapp",
                    status="failed",
                    error_message=resp.text,
                )
        except Exception as exc:
            logger.exception("Meta API dispatch exception")
            return OutboundResult(
                success=False,
                provider=self.provider_name,
                to_phone=to,
                channel="whatsapp",
                status="failed",
                error_message=str(exc),
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
        clean_to = to.replace("+", "").strip()
        if settings.DEMO_MODE or self.token.startswith("dummy_"):
            return OutboundResult(
                success=True,
                provider=self.provider_name,
                provider_message_id=f"wamid.tmpl.{clean_to[-4:]}",
                to_phone=to,
                channel="whatsapp",
                segments_count=1,
                cost_estimate_usd=0.015,
                status="sent",
            )

        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        
        # Build components
        components = []
        if parameters:
            body_params = [{"type": "text", "text": str(v)} for v in parameters.values()]
            components.append({"type": "body", "parameters": body_params})

        payload = {
            "messaging_product": "whatsapp",
            "to": clean_to,
            "type": "template",
            "template": {
                "name": template_name,
                "language": {"code": language},
                "components": components,
            },
        }

        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                data = resp.json()
                wamid = data.get("messages", [{}])[0].get("id")
                return OutboundResult(
                    success=True,
                    provider=self.provider_name,
                    provider_message_id=wamid,
                    to_phone=to,
                    channel="whatsapp",
                    segments_count=1,
                    cost_estimate_usd=0.015,
                    status="sent",
                )
            return OutboundResult(
                success=False,
                provider=self.provider_name,
                to_phone=to,
                channel="whatsapp",
                status="failed",
                error_message=resp.text,
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
        clean_to = to.replace("+", "").strip()
        if settings.DEMO_MODE or self.token.startswith("dummy_"):
            return OutboundResult(
                success=True,
                provider=self.provider_name,
                provider_message_id=f"wamid.media.{clean_to[-4:]}",
                to_phone=to,
                channel="whatsapp",
                segments_count=1,
                cost_estimate_usd=0.02,
                status="sent",
            )

        url = f"https://graph.facebook.com/v20.0/{self.phone_number_id}/messages"
        headers = {"Authorization": f"Bearer {self.token}", "Content-Type": "application/json"}
        payload = {
            "messaging_product": "whatsapp",
            "recipient_type": "individual",
            "to": clean_to,
            "type": media_type,
            media_type: {"link": media_url},
        }
        if caption and media_type in ["image", "document", "video"]:
            payload[media_type]["caption"] = caption

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, json=payload, headers=headers)
            if resp.status_code in [200, 201]:
                data = resp.json()
                wamid = data.get("messages", [{}])[0].get("id")
                return OutboundResult(
                    success=True,
                    provider=self.provider_name,
                    provider_message_id=wamid,
                    to_phone=to,
                    channel="whatsapp",
                    segments_count=1,
                    cost_estimate_usd=0.02,
                    status="sent",
                )
            return OutboundResult(
                success=False,
                provider=self.provider_name,
                to_phone=to,
                channel="whatsapp",
                status="failed",
                error_message=resp.text,
            )

    def parse_inbound(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> InboundMessageDTO:
        try:
            entry = payload.get("entry", [{}])[0]
            change = entry.get("changes", [{}])[0]
            val = change.get("value", {})
            msg = val.get("messages", [{}])[0]
            metadata = val.get("metadata", {})
            
            from_phone = f"+{msg.get('from', '')}"
            to_phone = f"+{metadata.get('display_phone_number', '')}"
            msg_id = msg.get("id", f"wamid.{from_phone[-4:]}")
            msg_type = msg.get("type", "text")

            body: Optional[str] = None
            media_id: Optional[str] = None
            lat: Optional[float] = None
            lon: Optional[float] = None

            if msg_type == "text":
                body = msg.get("text", {}).get("body")
            elif msg_type == "location":
                loc = msg.get("location", {})
                lat = float(loc.get("latitude", 0.0))
                lon = float(loc.get("longitude", 0.0))
            elif msg_type == "image":
                img = msg.get("image", {})
                media_id = img.get("id")
                body = img.get("caption")
            elif msg_type == "audio":
                aud = msg.get("audio", {})
                media_id = aud.get("id")
                msg_type = "voice"
            elif msg_type == "interactive":
                inter = msg.get("interactive", {})
                if inter.get("type") == "button_reply":
                    body = inter.get("button_reply", {}).get("id")
                elif inter.get("type") == "list_reply":
                    body = inter.get("list_reply", {}).get("id")

            return InboundMessageDTO(
                provider=self.provider_name,
                provider_message_id=msg_id,
                from_phone=from_phone,
                to_phone=to_phone,
                channel="whatsapp",
                message_type=msg_type,
                body=body,
                media_id=media_id,
                latitude=lat,
                longitude=lon,
                raw_payload=payload,
            )
        except Exception as exc:
            logger.warning(f"Failed to parse Meta webhook: {exc}")
            return InboundMessageDTO(
                provider=self.provider_name,
                provider_message_id="wamid.err",
                from_phone="+0000000000",
                to_phone="+0000000000",
                channel="whatsapp",
                message_type="text",
                body="",
                raw_payload=payload,
            )

    async def download_media(self, media_id_or_url: str) -> bytes:
        if settings.DEMO_MODE or self.token.startswith("dummy_"):
            from app.messaging.providers.simulator import SimulatorProvider
            return await SimulatorProvider().download_media(media_id_or_url)

        headers = {"Authorization": f"Bearer {self.token}"}
        async with httpx.AsyncClient(timeout=30.0) as client:
            # 1. Fetch media URL from Graph API
            meta_res = await client.get(f"https://graph.facebook.com/v20.0/{media_id_or_url}", headers=headers)
            meta_res.raise_for_status()
            download_url = meta_res.json().get("url")
            if not download_url:
                raise ValueError("No download URL returned by Meta")

            # 2. Download binary bytes
            bin_res = await client.get(download_url, headers=headers)
            bin_res.raise_for_status()
            return bin_res.content
