"""
Twilio Messaging Provider for WhatsApp and SMS.
Implements:
1. Cryptographic X-Twilio-Signature verification (HMAC-SHA1).
2. Form-encoded inbound payload parsing (Text, Location, Media).
3. Async REST dispatch for SMS and WhatsApp (whatsapp: prefix).
4. Authenticated media downloading for photos and voice notes.
"""

import base64
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
from app.messaging.segment_calc import calculate_segments

logger = logging.getLogger("krishinet.messaging.twilio")


class TwilioProvider(MessagingProvider):
    provider_name: str = "twilio"

    def __init__(
        self,
        account_sid: Optional[str] = None,
        auth_token: Optional[str] = None,
        from_phone: Optional[str] = None,
        from_whatsapp: Optional[str] = None,
    ) -> None:
        self.account_sid = account_sid or settings.TWILIO_ACCOUNT_SID or "AC_dummy_account_sid"
        self.auth_token = auth_token or settings.TWILIO_AUTH_TOKEN or "dummy_auth_token"
        self.from_phone = from_phone or settings.TWILIO_PHONE_NUMBER or "+15550001111"
        self.from_whatsapp = from_whatsapp or settings.TWILIO_WHATSAPP_NUMBER or "+14155238886"

    def _get_auth(self) -> httpx.BasicAuth:
        return httpx.BasicAuth(self.account_sid, self.auth_token)

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

        to_formatted = f"whatsapp:{to}" if channel == "whatsapp" and not to.startswith("whatsapp:") else to
        from_formatted = f"whatsapp:{self.from_whatsapp}" if channel == "whatsapp" and not self.from_whatsapp.startswith("whatsapp:") else self.from_phone

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": to_formatted,
            "From": from_formatted,
            "Body": text,
        }

        # If in DEMO_MODE or dummy credentials, return success without real HTTP
        if settings.DEMO_MODE or self.account_sid.startswith("AC_dummy"):
            return OutboundResult(
                success=True,
                provider=self.provider_name,
                provider_message_id=f"SM_mock_{to[-4:]}",
                to_phone=to,
                channel=channel,
                segments_count=segments,
                cost_estimate_usd=cost,
                status="sent",
            )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(url, data=data, auth=self._get_auth())
                if resp.status_code in [200, 201]:
                    res_json = resp.json()
                    return OutboundResult(
                        success=True,
                        provider=self.provider_name,
                        provider_message_id=res_json.get("sid"),
                        to_phone=to,
                        channel=channel,
                        segments_count=segments,
                        cost_estimate_usd=cost,
                        status="sent",
                    )
                else:
                    logger.error(f"Twilio API error {resp.status_code}: {resp.text}")
                    return OutboundResult(
                        success=False,
                        provider=self.provider_name,
                        to_phone=to,
                        channel=channel,
                        status="failed",
                        error_message=f"Twilio HTTP {resp.status_code}: {resp.text}",
                    )
        except Exception as exc:
            logger.exception("Twilio dispatch exception")
            return OutboundResult(
                success=False,
                provider=self.provider_name,
                to_phone=to,
                channel=channel,
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
        # Twilio sends pre-approved Content API templates or fallback text
        body_text = f"[{template_name}] " + " ".join(f"{k}: {v}" for k, v in parameters.items())
        return await self.send_text(to=to, text=body_text, channel=channel, **kwargs)

    async def send_media(
        self,
        to: str,
        media_url: str,
        caption: Optional[str] = None,
        media_type: str = "image",
        channel: str = "whatsapp",
        **kwargs: Any
    ) -> OutboundResult:
        to_formatted = f"whatsapp:{to}" if channel == "whatsapp" and not to.startswith("whatsapp:") else to
        from_formatted = f"whatsapp:{self.from_whatsapp}" if channel == "whatsapp" and not self.from_whatsapp.startswith("whatsapp:") else self.from_phone

        url = f"https://api.twilio.com/2010-04-01/Accounts/{self.account_sid}/Messages.json"
        data = {
            "To": to_formatted,
            "From": from_formatted,
            "MediaUrl": media_url,
        }
        if caption:
            data["Body"] = caption

        if settings.DEMO_MODE or self.account_sid.startswith("AC_dummy"):
            return OutboundResult(
                success=True,
                provider=self.provider_name,
                provider_message_id=f"MM_mock_{to[-4:]}",
                to_phone=to,
                channel=channel,
                segments_count=1,
                cost_estimate_usd=0.016,
                status="sent",
            )

        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.post(url, data=data, auth=self._get_auth())
            if resp.status_code in [200, 201]:
                res_json = resp.json()
                return OutboundResult(
                    success=True,
                    provider=self.provider_name,
                    provider_message_id=res_json.get("sid"),
                    to_phone=to,
                    channel=channel,
                    segments_count=1,
                    cost_estimate_usd=0.016,
                    status="sent",
                )
            return OutboundResult(
                success=False,
                provider=self.provider_name,
                to_phone=to,
                channel=channel,
                status="failed",
                error_message=resp.text,
            )

    def parse_inbound(
        self,
        payload: Dict[str, Any],
        headers: Dict[str, str]
    ) -> InboundMessageDTO:
        from_raw = payload.get("From", "")
        to_raw = payload.get("To", "")
        channel = "whatsapp" if "whatsapp:" in from_raw.lower() or "whatsapp:" in to_raw.lower() else "sms"
        clean_from = from_raw.replace("whatsapp:", "").strip()
        clean_to = to_raw.replace("whatsapp:", "").strip()

        # Check media
        num_media = int(payload.get("NumMedia", 0) or 0)
        media_url = payload.get("MediaUrl0") if num_media > 0 else None
        media_content_type = payload.get("MediaContentType0") if num_media > 0 else None

        # Detect message type
        lat = payload.get("Latitude")
        lon = payload.get("Longitude")
        latitude = float(lat) if lat is not None else None
        longitude = float(lon) if lon is not None else None

        if latitude is not None and longitude is not None:
            msg_type = "location"
        elif media_content_type and "audio" in media_content_type:
            msg_type = "voice"
        elif media_content_type and "image" in media_content_type:
            msg_type = "image"
        else:
            msg_type = "text"

        return InboundMessageDTO(
            provider=self.provider_name,
            provider_message_id=payload.get("MessageSid", f"SM_{clean_from[-6:]}"),
            from_phone=clean_from,
            to_phone=clean_to,
            channel=channel,
            message_type=msg_type,
            body=payload.get("Body"),
            media_url=media_url,
            media_content_type=media_content_type,
            latitude=latitude,
            longitude=longitude,
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
        """
        Twilio HMAC-SHA1 validation:
        1. Take URL exactly as requested.
        2. Sort POST parameters alphabetically by key.
        3. Append key+value pairs to URL.
        4. Sign with Auth Token using HMAC-SHA1.
        """
        token = secret or self.auth_token
        expected_sig = headers.get("X-Twilio-Signature") or headers.get("x-twilio-signature")
        if not expected_sig:
            return False

        # Construct signature base string
        s = url
        for key in sorted(params.keys()):
            s += f"{key}{params[key]}"

        mac = hmac.new(token.encode("utf-8"), s.encode("utf-8"), hashlib.sha1)
        computed_sig = base64.b64encode(mac.digest()).decode("utf-8")
        return hmac.compare_digest(computed_sig, expected_sig)

    async def download_media(self, media_id_or_url: str) -> bytes:
        if settings.DEMO_MODE or not media_id_or_url.startswith("http"):
            from app.messaging.providers.simulator import SimulatorProvider
            return await SimulatorProvider().download_media(media_id_or_url)

        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(media_id_or_url, auth=self._get_auth(), follow_redirects=True)
            resp.raise_for_status()
            return resp.content
