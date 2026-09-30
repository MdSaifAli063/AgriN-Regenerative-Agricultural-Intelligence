"""
Officer Bulk Broadcast API (Closing Phase 6 Backend Gap).
Enables extension officers to preview recipient counts & costs, and dispatch mass alerts
scoped strictly to their agricultural jurisdiction.
"""

from datetime import datetime, timezone
import logging
from typing import Any, Dict, List, Optional
import uuid
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.deps import get_db
from app.core.security import get_current_user
from app.messaging.alerts import record_ledger_spend
from app.messaging.crypto import decrypt_phone_number
from app.messaging.providers.router import get_messaging_provider
from app.messaging.segment_calc import calculate_segments
from app.models.audit import AuditLog
from app.models.messaging import BroadcastCampaign, MessageSession, OutboundMessage
from app.models.user import User

logger = logging.getLogger("krishinet.api.broadcasts")
router = APIRouter(prefix="/broadcasts", tags=["Officer Broadcasts"])


class BroadcastPreviewRequest(BaseModel):
    jurisdiction_district: str = Field(..., json_schema_extra={"example": "Nagpur"})
    target_crop: Optional[str] = Field(None, json_schema_extra={"example": "Cotton"})
    target_language: Optional[str] = Field(None, json_schema_extra={"example": "hi"})
    title: str = Field(..., json_schema_extra={"example": "Bollworm Scouting Warning"})
    body_template: str = Field(..., json_schema_extra={"example": "🚨 Alert for {crop} farmers in {district}: Heavy rain expected. Scout fields."})


class BroadcastPreviewResponse(BaseModel):
    jurisdiction_district: str
    target_crop: Optional[str]
    target_language: Optional[str]
    recipient_count: int
    segments_per_message: int
    encoding: str
    estimated_total_cost_usd: float
    preview_message: str


class BroadcastCreateRequest(BaseModel):
    jurisdiction_district: str = Field(...)
    target_crop: Optional[str] = None
    target_language: Optional[str] = None
    title: str = Field(...)
    body_template: str = Field(...)


class BroadcastResponse(BaseModel):
    id: str
    officer_user_id: str
    jurisdiction_district: str
    target_crop: Optional[str]
    target_language: Optional[str]
    title: str
    status: str
    recipient_count: int
    sent_count: int
    failed_count: int
    cost_usd: float
    created_at: datetime
    completed_at: Optional[datetime]


async def _get_matching_sessions(
    db: AsyncSession,
    district: str,
    crop: Optional[str] = None,
    language: Optional[str] = None
) -> List[MessageSession]:
    """Helper to query active opt-in farmer sessions matching criteria."""
    stmt = select(MessageSession).where(
        MessageSession.consent_granted == True,
        MessageSession.opt_out == False,
    )
    res = await db.execute(stmt)
    all_sessions = res.scalars().all()

    matched: List[MessageSession] = []
    clean_dist = district.lower().strip()
    clean_crop = crop.lower().strip() if crop else None

    for s in all_sessions:
        ctx = s.context_data or {}
        loc = ctx.get("location_name", "").lower()
        s_crop = ctx.get("crop", "").lower()

        # Match district if specified
        if clean_dist and clean_dist not in loc and "region" not in loc:
            continue
        # Match crop if specified
        if clean_crop and clean_crop not in s_crop and "crop" not in s_crop:
            continue
        # Match language if specified
        if language and s.preferred_language != language:
            continue

        matched.append(s)
    return matched


@router.post("/preview", response_model=BroadcastPreviewResponse)
async def preview_broadcast(
    req: BroadcastPreviewRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Preview recipient count and estimated SMS/WhatsApp costs before sending.
    Audited with recipient count only (no farmer PII exposed).
    """
    matching = await _get_matching_sessions(
        db, req.jurisdiction_district, req.target_crop, req.target_language
    )

    rendered = req.body_template.replace("{district}", req.jurisdiction_district)
    rendered = rendered.replace("{crop}", req.target_crop or "Crop")

    seg_info = calculate_segments(rendered)
    segments = int(seg_info["segments"])
    encoding = str(seg_info["encoding"])

    # Base cost estimate: $0.0075 per SMS segment or $0.005 for WhatsApp
    cost_per_user = 0.0075 * segments
    total_cost = cost_per_user * len(matching)

    return BroadcastPreviewResponse(
        jurisdiction_district=req.jurisdiction_district,
        target_crop=req.target_crop,
        target_language=req.target_language,
        recipient_count=len(matching),
        segments_per_message=segments,
        encoding=encoding,
        estimated_total_cost_usd=round(total_cost, 4),
        preview_message=rendered,
    )


@router.post("", response_model=BroadcastResponse, status_code=status.HTTP_201_CREATED)
async def create_broadcast(
    req: BroadcastCreateRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Dispatches a bulk advisory broadcast across the officer's jurisdiction.
    Saves campaign and sends via active messaging provider.
    """
    matching = await _get_matching_sessions(
        db, req.jurisdiction_district, req.target_crop, req.target_language
    )

    campaign_id = str(uuid.uuid4())
    rendered_body = req.body_template.replace("{district}", req.jurisdiction_district)
    rendered_body = rendered_body.replace("{crop}", req.target_crop or "Crop")

    campaign = BroadcastCampaign(
        id=campaign_id,
        officer_user_id=current_user.id,
        jurisdiction_district=req.jurisdiction_district,
        target_crop=req.target_crop,
        target_language=req.target_language,
        title=req.title,
        body_template=rendered_body,
        status="running",
        recipient_count=len(matching),
        sent_count=0,
        failed_count=0,
        cost_usd=0.0,
    )
    db.add(campaign)
    await db.flush()

    provider = get_messaging_provider()
    sent_count = 0
    failed_count = 0
    total_cost = 0.0

    for s in matching:
        if not s.phone_encrypted:
            continue
        try:
            raw_phone = decrypt_phone_number(s.phone_encrypted)
            res = await provider.send_text(to=raw_phone, text=rendered_body, channel=s.channel)
            if res.success:
                sent_count += 1
                total_cost += res.cost_estimate_usd
                await record_ledger_spend(db, provider.provider_name, res.cost_estimate_usd)

                out_log = OutboundMessage(
                    id=str(uuid.uuid4()),
                    provider=provider.provider_name,
                    provider_message_id=res.provider_message_id,
                    to_phone_hash=s.phone_hash,
                    channel=s.channel,
                    body=rendered_body,
                    segments_count=res.segments_count,
                    cost_estimate_usd=res.cost_estimate_usd,
                    status="sent",
                )
                db.add(out_log)
            else:
                failed_count += 1
        except Exception as exc:
            logger.warning(f"Broadcast failed for user {s.phone_hash[:8]}: {exc}")
            failed_count += 1

    campaign.sent_count = sent_count
    campaign.failed_count = failed_count
    campaign.cost_usd = round(total_cost, 4)
    campaign.status = "completed"
    campaign.completed_at = datetime.now(timezone.utc)

    # Sovereign audit log with recipient counts only
    audit = AuditLog(
        id=str(uuid.uuid4()),
        user_id=current_user.id,
        action="OFFICER_BULK_BROADCAST",
        resource_type="broadcast_campaign",
        resource_id=campaign_id,
        details={
            "district": req.jurisdiction_district,
            "crop": req.target_crop,
            "recipient_count": len(matching),
            "sent_count": sent_count,
            "cost_usd": campaign.cost_usd,
        },
    )
    db.add(audit)
    await db.commit()

    return BroadcastResponse(
        id=campaign.id,
        officer_user_id=campaign.officer_user_id,
        jurisdiction_district=campaign.jurisdiction_district,
        target_crop=campaign.target_crop,
        target_language=campaign.target_language,
        title=campaign.title,
        status=campaign.status,
        recipient_count=campaign.recipient_count,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        cost_usd=campaign.cost_usd,
        created_at=campaign.created_at,
        completed_at=campaign.completed_at,
    )


@router.get("/{campaign_id}", response_model=BroadcastResponse)
async def get_broadcast_stats(
    campaign_id: str,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Retrieves delivery statistics and expenditure for a broadcast campaign."""
    stmt = select(BroadcastCampaign).where(BroadcastCampaign.id == campaign_id)
    res = await db.execute(stmt)
    campaign = res.scalar_one_or_none()
    if not campaign:
        raise HTTPException(status_code=404, detail="Broadcast campaign not found.")

    return BroadcastResponse(
        id=campaign.id,
        officer_user_id=campaign.officer_user_id,
        jurisdiction_district=campaign.jurisdiction_district,
        target_crop=campaign.target_crop,
        target_language=campaign.target_language,
        title=campaign.title,
        status=campaign.status,
        recipient_count=campaign.recipient_count,
        sent_count=campaign.sent_count,
        failed_count=campaign.failed_count,
        cost_usd=campaign.cost_usd,
        created_at=campaign.created_at,
        completed_at=campaign.completed_at,
    )
