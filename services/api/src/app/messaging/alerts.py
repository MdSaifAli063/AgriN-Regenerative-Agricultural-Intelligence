"""
Proactive Messaging Alerts, Automated Celery Beat Tasks, and Data Retention Purge.
Handles:
1. Daily morning action digest dispatches.
2. Severe agro-climate risk warnings (frost, storm, heat) with quiet-hours bypass.
3. Pest & disease outbreak alerts from Phase 5 surveillance.
4. Data minimisation message retention purging (deleting bodies older than 30 days).
"""

from datetime import datetime, timedelta, timezone
import logging
import uuid
from typing import Any, Dict, List, Optional
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.config import settings
from app.messaging.crypto import decrypt_phone_number
from app.messaging.providers.router import get_messaging_provider
from app.messaging.safety import (
    check_daily_cost_budget,
    check_outbound_rate_limit,
    is_within_quiet_hours,
)
from app.models.messaging import (
    InboundMessage,
    MessageSession,
    MessagingCostLedger,
    OutboundMessage,
)

logger = logging.getLogger("krishinet.messaging.alerts")


async def get_today_spent_usd(db: AsyncSession) -> float:
    """Calculates total dollars spent on outbound messages today."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stmt = select(func.sum(MessagingCostLedger.cost_usd)).where(
        MessagingCostLedger.date == today_str
    )
    res = await db.execute(stmt)
    total = res.scalar() or 0.0
    return float(total)


async def record_ledger_spend(db: AsyncSession, provider: str, cost: float) -> None:
    """Increments the daily cost ledger."""
    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    stmt = select(MessagingCostLedger).where(
        MessagingCostLedger.date == today_str,
        MessagingCostLedger.provider == provider,
    )
    res = await db.execute(stmt)
    entry = res.scalar_one_or_none()
    if entry:
        entry.cost_usd += cost
        entry.message_count += 1
    else:
        entry = MessagingCostLedger(
            id=str(uuid.uuid4()),
            date=today_str,
            provider=provider,
            message_count=1,
            cost_usd=cost,
        )
        db.add(entry)
    await db.flush()


async def dispatch_morning_digests(
    db: AsyncSession,
    force: bool = False
) -> Dict[str, Any]:
    """
    Sends morning 'What to do today' digest to opt-in farmers.
    Respects quiet hours and cost budget guard.
    """
    if is_within_quiet_hours() and not force:
        logger.info("Morning digest deferred: currently within quiet hours.")
        return {"status": "deferred_quiet_hours", "dispatched_count": 0}

    today_spend = await get_today_spent_usd(db)
    budget_ok, reason = check_daily_cost_budget(today_spend)
    if not budget_ok:
        logger.warning(f"Morning digest skipped: {reason}")
        return {"status": "budget_exhausted", "dispatched_count": 0, "reason": reason}

    # Query active opt-in sessions
    stmt = select(MessageSession).where(
        MessageSession.consent_granted == True,
        MessageSession.opt_out == False,
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    dispatched = 0
    total_cost = 0.0

    for s in sessions:
        if not s.phone_encrypted:
            continue

        rate_ok, _ = check_outbound_rate_limit(s.phone_hash)
        if not rate_ok:
            continue

        raw_phone = decrypt_phone_number(s.phone_encrypted)
        provider = get_messaging_provider()
        crop = s.context_data.get("crop", "Crop")
        loc = s.context_data.get("location_name", "Region")

        msg = (
            f"🌾 Good morning farmer! For your {crop} field in {loc}:\n"
            f"• Priority: Check foliar health and prepare bio-spray.\n"
            f"• Weather: 31°C, low rain probability (10%).\n"
            f"• Spray Window: OPEN (06:30 - 09:30 AM).\n\n"
            f"Reply 1 for full advice, 2 for Leaf Doctor, 9 for Menu."
        )

        out_res = await provider.send_text(to=raw_phone, text=msg, channel=s.channel)
        if out_res.success:
            dispatched += 1
            total_cost += out_res.cost_estimate_usd
            await record_ledger_spend(db, provider.provider_name, out_res.cost_estimate_usd)

            out_log = OutboundMessage(
                id=str(uuid.uuid4()),
                provider=provider.provider_name,
                provider_message_id=out_res.provider_message_id,
                to_phone_hash=s.phone_hash,
                channel=s.channel,
                body=msg,
                segments_count=out_res.segments_count,
                cost_estimate_usd=out_res.cost_estimate_usd,
                status="sent",
            )
            db.add(out_log)

    await db.commit()
    return {"status": "success", "dispatched_count": dispatched, "cost_usd": total_cost}


async def dispatch_weather_alert(
    db: AsyncSession,
    district: str,
    hazard_type: str,
    severity: str,
    recommendation: str
) -> Dict[str, Any]:
    """
    Emergency agro-climate risk warning (frost, heat wave, severe storm).
    Bypasses quiet hours because it protects crop loss.
    """
    stmt = select(MessageSession).where(
        MessageSession.consent_granted == True,
        MessageSession.opt_out == False,
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    alert_text = (
        f"🚨 *CRITICAL WEATHER ALERT ({severity.upper()})*\n"
        f"• Hazard: *{hazard_type.upper()}* detected for {district} region.\n"
        f"• Recommendation: {recommendation}\n"
        f"• Action: Inspect drainage and protect young seedlings.\n\n"
        f"Reply 1 for updated agronomic plan."
    )

    dispatched = 0
    provider = get_messaging_provider()

    for s in sessions:
        if not s.phone_encrypted:
            continue
        # Filter matching location if specified
        loc = s.context_data.get("location_name", "").lower()
        if district.lower() not in loc and "region" not in loc:
            continue

        raw_phone = decrypt_phone_number(s.phone_encrypted)
        out_res = await provider.send_text(to=raw_phone, text=alert_text, channel=s.channel)
        if out_res.success:
            dispatched += 1
            await record_ledger_spend(db, provider.provider_name, out_res.cost_estimate_usd)
            out_log = OutboundMessage(
                id=str(uuid.uuid4()),
                provider=provider.provider_name,
                provider_message_id=out_res.provider_message_id,
                to_phone_hash=s.phone_hash,
                channel=s.channel,
                body=alert_text,
                segments_count=out_res.segments_count,
                cost_estimate_usd=out_res.cost_estimate_usd,
                status="sent",
            )
            db.add(out_log)

    await db.commit()
    return {"status": "dispatched", "recipients": dispatched}


async def dispatch_outbreak_alert(
    db: AsyncSession,
    district: str,
    crop: str,
    disease_name: str,
    risk_level: str
) -> Dict[str, Any]:
    """Pest/disease surveillance warning to farmers growing the susceptible crop in the district."""
    stmt = select(MessageSession).where(
        MessageSession.consent_granted == True,
        MessageSession.opt_out == False,
    )
    res = await db.execute(stmt)
    sessions = res.scalars().all()

    alert_text = (
        f"🚨 *PEST / DISEASE SURVEILLANCE WARNING ({risk_level.upper()})*\n"
        f"• Outbreak Alert: *{disease_name}* detected in {district} district.\n"
        f"• Susceptible Crop: {crop}\n"
        f"• Protective Action: Scout field borders immediately. Apply organic preventive bio-agent.\n\n"
        f"Reply 2 to send a leaf photo for instant Leaf Doctor diagnosis."
    )

    dispatched = 0
    provider = get_messaging_provider()

    for s in sessions:
        if not s.phone_encrypted:
            continue
        c = s.context_data.get("crop", "").lower()
        if crop.lower() not in c and "crop" not in c:
            continue

        raw_phone = decrypt_phone_number(s.phone_encrypted)
        out_res = await provider.send_text(to=raw_phone, text=alert_text, channel=s.channel)
        if out_res.success:
            dispatched += 1
            await record_ledger_spend(db, provider.provider_name, out_res.cost_estimate_usd)
            out_log = OutboundMessage(
                id=str(uuid.uuid4()),
                provider=provider.provider_name,
                provider_message_id=out_res.provider_message_id,
                to_phone_hash=s.phone_hash,
                channel=s.channel,
                body=alert_text,
                segments_count=out_res.segments_count,
                cost_estimate_usd=out_res.cost_estimate_usd,
                status="sent",
            )
            db.add(out_log)

    await db.commit()
    return {"status": "dispatched", "recipients": dispatched}


async def purge_expired_message_bodies(
    db: AsyncSession,
    retention_days: Optional[int] = None
) -> int:
    """
    Data Minimisation Beat Task:
    Purges message bodies and raw payloads older than retention_days (default 30 days).
    Retains timestamps, status, costs, and phone hashes for audit and billing.
    """
    days = retention_days if retention_days is not None else settings.MESSAGING_RETENTION_DAYS
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)

    # 1. Purge inbound message bodies
    stmt_in = (
        update(InboundMessage)
        .where(InboundMessage.received_at < cutoff, InboundMessage.body != None)
        .values(body=None, media_url=None, raw_payload={})
    )
    res_in = await db.execute(stmt_in)
    purged_in = res_in.rowcount

    # 2. Purge outbound message bodies
    stmt_out = (
        update(OutboundMessage)
        .where(OutboundMessage.created_at < cutoff, OutboundMessage.body != None)
        .values(body=None)
    )
    res_out = await db.execute(stmt_out)
    purged_out = res_out.rowcount

    await db.commit()
    total_purged = (purged_in or 0) + (purged_out or 0)
    logger.info(f"Purged {total_purged} expired message bodies older than {days} days.")
    return total_purged
