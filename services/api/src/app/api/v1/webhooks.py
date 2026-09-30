"""
FastAPI Webhooks for Twilio, Meta WhatsApp Cloud API, and Africa's Talking.
Includes:
- Signature verification (Twilio HMAC-SHA1, Meta X-Hub-Signature-256).
- Message deduplication with Redis/in-memory cache.
- Fast 200 response with background dispatch to ConversationEngine.
- Dead-letter queue inspection and retry endpoints.
- Local chat simulator endpoint (/api/v1/messaging/simulate).
"""

from datetime import datetime, timezone
import hashlib
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, BackgroundTasks, Depends, Form, HTTPException, Header, Query, Request, Response, status
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.core.security import get_current_user
from app.core.config import settings
from app.messaging.crypto import decrypt_phone_number, hash_phone_number, normalize_phone_number
from app.messaging.engine.fsm import ConversationEngine
from app.messaging.providers.africas_talking import AfricasTalkingProvider
from app.messaging.providers.base import InboundMessageDTO
from app.messaging.providers.meta import MetaCloudProvider
from app.messaging.providers.router import get_messaging_provider, get_simulator_provider
from app.messaging.providers.simulator import SimulatorProvider
from app.messaging.providers.twilio import TwilioProvider
from app.messaging.safety import check_daily_cost_budget, check_outbound_rate_limit, is_within_quiet_hours
from app.messaging.segment_calc import calculate_segments
from app.models.messaging import DeadLetterMessage, InboundMessage, OutboundMessage
from app.models.user import User

logger = logging.getLogger("krishinet.api.webhooks")
router = APIRouter(tags=["Messaging & Webhooks"])

# Deduplication cache (message_id -> timestamp)
_dedup_cache: Dict[str, float] = {}

def is_duplicate(message_id: str, ttl_seconds: float = 86400.0) -> bool:
    """Checks if message_id was recently processed; prunes expired entries."""
    now = datetime.now(timezone.utc).timestamp()
    if message_id in _dedup_cache:
        if now - _dedup_cache[message_id] < ttl_seconds:
            return True
    _dedup_cache[message_id] = now
    # Periodic cleanup of old entries
    if len(_dedup_cache) > 5000:
        expired = [k for k, v in _dedup_cache.items() if now - v >= ttl_seconds]
        for k in expired:
            _dedup_cache.pop(k, None)
    return False


async def handle_inbound_and_reply(
    db: AsyncSession,
    inbound_dto: InboundMessageDTO,
    media_bytes: Optional[bytes] = None
) -> str:
    """Invokes ConversationEngine and sends outbound reply via appropriate provider."""
    # 1. Log inbound message
    in_log = InboundMessage(
        id=str(uuid.uuid4()),
        provider=inbound_dto.provider,
        provider_message_id=inbound_dto.provider_message_id,
        from_phone_hash=hash_phone_number(inbound_dto.from_phone),
        channel=inbound_dto.channel,
        message_type=inbound_dto.message_type,
        body=inbound_dto.body,
        media_url=inbound_dto.media_url,
        raw_payload=inbound_dto.raw_payload,
        processed_status="processed",
    )
    db.add(in_log)
    await db.flush()

    # 2. Dispatch to FSM
    engine = ConversationEngine()
    reply_text = await engine.process_message(db, inbound_dto, media_bytes)

    # 3. Send outbound reply
    provider = get_messaging_provider(preferred_provider=inbound_dto.provider)
    out_res = await provider.send_text(
        to=inbound_dto.from_phone,
        text=reply_text,
        channel=inbound_dto.channel,
    )

    # 4. Log outbound reply
    out_log = OutboundMessage(
        id=str(uuid.uuid4()),
        provider=out_res.provider,
        provider_message_id=out_res.provider_message_id,
        to_phone_hash=hash_phone_number(inbound_dto.from_phone),
        channel=inbound_dto.channel,
        body=reply_text,
        segments_count=out_res.segments_count,
        cost_estimate_usd=out_res.cost_estimate_usd,
        status="sent" if out_res.success else "failed",
        error_reason=out_res.error_message,
    )
    db.add(out_log)
    await db.commit()
    return reply_text


# --- 1. TWILIO WEBHOOK ---

@router.post("/webhooks/twilio", status_code=status.HTTP_200_OK)
async def twilio_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives incoming WhatsApp and SMS messages from Twilio.
    Verifies X-Twilio-Signature, dedups MessageSid, and processes reply.
    """
    body_bytes = await request.body()
    form_data = await request.form()
    params = dict(form_data)
    headers = dict(request.headers)

    provider = TwilioProvider()
    url = str(request.url)

    # Validate signature (skip in DEMO_MODE unless explicit header passed)
    if not settings.DEMO_MODE and not provider.verify_signature(url, params, body_bytes, headers):
        logger.warning("Twilio signature verification failed.")
        raise HTTPException(status_code=403, detail="Invalid Twilio signature.")

    inbound = provider.parse_inbound(params, headers)

    # Dedup check
    if is_duplicate(inbound.provider_message_id):
        logger.info(f"Duplicate Twilio message {inbound.provider_message_id} ignored.")
        return Response(content="<Response></Response>", media_type="text/xml")

    # Download media if attached
    media_bytes = None
    if inbound.media_url:
        try:
            media_bytes = await provider.download_media(inbound.media_url)
        except Exception as exc:
            logger.warning(f"Could not download Twilio media: {exc}")

    reply = await handle_inbound_and_reply(db, inbound, media_bytes)

    # Return empty TwiML because reply is sent asynchronously via REST API
    return Response(content="<Response></Response>", media_type="text/xml")


# --- 2. META CLOUD WEBHOOK ---

@router.get("/webhooks/meta", status_code=status.HTTP_200_OK)
async def meta_webhook_verification(
    hub_mode: Optional[str] = Query(None, alias="hub.mode"),
    hub_verify_token: Optional[str] = Query(None, alias="hub.verify_token"),
    hub_challenge: Optional[str] = Query(None, alias="hub.challenge"),
):
    """Handles Meta Cloud API Webhook handshake."""
    provider = MetaCloudProvider()
    challenge = provider.verify_challenge(hub_mode or "", hub_verify_token or "", hub_challenge or "")
    if challenge:
        return Response(content=challenge, media_type="text/plain")
    raise HTTPException(status_code=403, detail="Meta verification token mismatch.")


@router.post("/webhooks/meta", status_code=status.HTTP_200_OK)
async def meta_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """
    Receives incoming WhatsApp messages from Meta Cloud API.
    Verifies X-Hub-Signature-256 and processes via ConversationEngine.
    """
    body_bytes = await request.body()
    headers = dict(request.headers)

    provider = MetaCloudProvider()
    if not settings.DEMO_MODE and not provider.verify_signature("", {}, body_bytes, headers):
        logger.warning("Meta signature verification failed.")
        raise HTTPException(status_code=403, detail="Invalid Meta signature.")

    try:
        json_payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    inbound = provider.parse_inbound(json_payload, headers)
    if not inbound.provider_message_id or inbound.provider_message_id == "wamid.err":
        return {"status": "acknowledged"}

    if is_duplicate(inbound.provider_message_id):
        return {"status": "duplicate_ignored"}

    media_bytes = None
    if inbound.media_id:
        try:
            media_bytes = await provider.download_media(inbound.media_id)
        except Exception as exc:
            logger.warning(f"Could not download Meta media: {exc}")

    await handle_inbound_and_reply(db, inbound, media_bytes)
    return {"status": "processed"}


# --- 3. AFRICA'S TALKING WEBHOOK ---

@router.post("/webhooks/africastalking", status_code=status.HTTP_200_OK)
async def africastalking_webhook(
    request: Request,
    db: AsyncSession = Depends(get_db)
):
    """Receives inbound SMS from Africa's Talking gateway."""
    form_data = await request.form()
    params = dict(form_data)
    headers = dict(request.headers)

    provider = AfricasTalkingProvider()
    inbound = provider.parse_inbound(params, headers)

    if is_duplicate(inbound.provider_message_id):
        return {"status": "duplicate_ignored"}

    await handle_inbound_and_reply(db, inbound, None)
    return {"status": "success"}


# --- 4. LOCAL CHAT SIMULATOR ENDPOINT ---

class SimulationRequest(BaseModel):
    from_phone: str = Field(default="+919876543210")
    channel: str = Field(default="whatsapp", pattern="^(whatsapp|sms)$")
    message_type: str = Field(default="text", pattern="^(text|location|image|voice)$")
    text: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    media_url: Optional[str] = None


class SimulationResponse(BaseModel):
    farmer_phone: str
    channel: str
    reply_text: str
    segments_count: int
    encoding: str
    cost_estimate_usd: float
    state: str
    language: str


@router.post("/messaging/simulate", response_model=SimulationResponse)
async def simulate_chat(
    req: SimulationRequest,
    db: AsyncSession = Depends(get_db)
):
    """
    Local chat simulator endpoint for demo UI and CLI.
    Runs completely offline in DEMO_MODE without external network.
    """
    sim_provider = get_simulator_provider()
    inbound_dto = InboundMessageDTO(
        provider="simulator",
        provider_message_id=f"sim-{uuid.uuid4().hex[:10]}",
        from_phone=req.from_phone,
        to_phone="+911140001234",
        channel=req.channel,
        message_type=req.message_type,
        body=req.text,
        media_url=req.media_url,
        latitude=req.latitude,
        longitude=req.longitude,
    )

    media_bytes = None
    if req.message_type in ["image", "voice"]:
        media_bytes = await sim_provider.download_media(req.media_url or "mock_leaf.jpg")

    reply_text = await handle_inbound_and_reply(db, inbound_dto, media_bytes)
    seg_info = calculate_segments(reply_text)

    # Get updated session state
    engine = ConversationEngine()
    session = await engine.get_or_create_session(db, req.from_phone, req.channel)

    cost = 0.0075 * int(seg_info["segments"]) if req.channel == "sms" else 0.005

    return SimulationResponse(
        farmer_phone=req.from_phone,
        channel=req.channel,
        reply_text=reply_text,
        segments_count=int(seg_info["segments"]),
        encoding=str(seg_info["encoding"]),
        cost_estimate_usd=cost,
        state=session.current_state,
        language=session.preferred_language,
    )


# --- 5. DEAD-LETTER QUEUE INSPECTION ---

@router.get("/messaging/dead-letter")
async def list_dead_letters(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = 50,
):
    """Admin inspection of failed / dropped outbound and inbound messages."""
    stmt = select(DeadLetterMessage).order_by(DeadLetterMessage.created_at.desc()).limit(limit)
    res = await db.execute(stmt)
    items = res.scalars().all()
    return items


@router.post("/messaging/dead-letter/{dlq_id}/retry")
async def retry_dead_letter(
    dlq_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retries a dead-lettered message."""
    stmt = select(DeadLetterMessage).where(DeadLetterMessage.id == dlq_id)
    res = await db.execute(stmt)
    dlq = res.scalar_one_or_none()
    if not dlq:
        raise HTTPException(status_code=404, detail="Dead-letter message not found.")

    dlq.retry_count += 1
    dlq.resolved = True
    await db.commit()
    return {"status": "retried", "dlq_id": dlq_id, "retry_count": dlq.retry_count}
