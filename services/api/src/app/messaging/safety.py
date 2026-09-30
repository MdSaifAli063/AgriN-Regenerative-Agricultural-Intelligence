"""
Outbound Safety, Rate Limiting, Quiet Hours, Cost Budget Guard, and Abuse Defenses.
Ensures responsible, privacy-respecting, and cost-controlled communications with farmers.
"""

from datetime import datetime, timezone
import logging
import re
from typing import Dict, List, Optional, Set, Tuple
from app.core.config import settings

logger = logging.getLogger("krishinet.messaging.safety")

# Multilingual opt-out keywords (Standardized and Localized)
OPT_OUT_KEYWORDS: Set[str] = {
    # English
    "stop", "unsubscribe", "cancel", "quit", "end",
    # Hindi / Marathi
    "roko", "band", "rok", "thamba", "रोको", "बंद", "थांबा",
    # Portuguese
    "pare", "parar", "cancelar", "sair",
    # Swahili
    "simama", "acha", "sitisha",
    # Russian
    "стоп", "отписаться",
    # Chinese
    "停止", "退订",
    # Arabic / Persian
    "توقف", "إلغاء", "لغو",
    # Zulu / Afrikaans
    "yekela", "staak",
}

# Multilingual opt-in / restart keywords
OPT_IN_KEYWORDS: Set[str] = {
    "start", "unstop", "subscribe", "shuru", "iniciar", "anza", "старт", "开始", "ابدأ",
}

# Prompt injection signatures to neutralize
INJECTION_PATTERNS = [
    re.compile(r"ignore\s+(all\s+)?(previous|prior)\s+instructions?", re.IGNORECASE),
    re.compile(r"system\s*:", re.IGNORECASE),
    re.compile(r"<system>", re.IGNORECASE),
    re.compile(r"\[INST\]", re.IGNORECASE),
    re.compile(r"you\s+are\s+now\s+in\s+developer\s+mode", re.IGNORECASE),
    re.compile(r"jailbreak", re.IGNORECASE),
]

# URL extraction pattern
URL_PATTERN = re.compile(r"https?://\S+|www\.\S+", re.IGNORECASE)

# In-memory sliding windows for rate-limiting
_user_message_timestamps: Dict[str, List[float]] = {}
_node_message_timestamps: List[float] = []


def is_opt_out_keyword(text: Optional[str]) -> bool:
    """Checks if message matches any international STOP keyword."""
    if not text:
        return False
    clean = text.strip().lower()
    return clean in OPT_OUT_KEYWORDS


def is_opt_in_keyword(text: Optional[str]) -> bool:
    """Checks if message matches any international START keyword."""
    if not text:
        return False
    clean = text.strip().lower()
    return clean in OPT_IN_KEYWORDS


def is_within_quiet_hours(
    current_hour: Optional[int] = None,
    start_hour: Optional[int] = None,
    end_hour: Optional[int] = None
) -> bool:
    """
    Checks if current local hour falls within quiet hours (default: 21:00 to 06:00).
    Night spans across midnight (21 -> 24 -> 6).
    """
    now_h = current_hour if current_hour is not None else datetime.now().hour
    start_h = start_hour if start_hour is not None else settings.MESSAGING_QUIET_HOURS_START
    end_h = end_hour if end_hour is not None else settings.MESSAGING_QUIET_HOURS_END

    if start_h > end_h:
        # Spans midnight: e.g. 21 to 6 -> True if >= 21 OR < 6
        return now_h >= start_h or now_h < end_h
    else:
        # Same day: e.g. 1 to 5
        return start_h <= now_h < end_h


def check_outbound_rate_limit(
    phone_hash: str,
    max_user_per_hour: int = 20,
    max_node_per_minute: int = 500
) -> Tuple[bool, str]:
    """
    Evaluates in-memory sliding window rate limits.
    Returns (allowed, reason).
    """
    now = datetime.now(timezone.utc).timestamp()

    # 1. Per-node throttle
    global _node_message_timestamps
    _node_message_timestamps = [t for t in _node_message_timestamps if now - t < 60.0]
    if len(_node_message_timestamps) >= max_node_per_minute:
        return False, "Node outbound messaging rate limit exceeded (500 msg/min)."

    # 2. Per-user throttle
    user_ts = _user_message_timestamps.setdefault(phone_hash, [])
    user_ts = [t for t in user_ts if now - t < 3600.0]
    _user_message_timestamps[phone_hash] = user_ts

    if len(user_ts) >= max_user_per_hour:
        return False, "Farmer outbound rate limit exceeded (20 msg/hour)."

    # Record dispatch
    _node_message_timestamps.append(now)
    user_ts.append(now)
    return True, "OK"


def check_daily_cost_budget(
    daily_spend_usd: float,
    budget_limit_usd: Optional[float] = None
) -> Tuple[bool, str]:
    """
    Evaluates kill switch and daily cost ceiling.
    """
    if settings.MESSAGING_KILL_SWITCH:
        return False, "Messaging Kill Switch is ACTIVE by sovereign node policy."

    limit = budget_limit_usd if budget_limit_usd is not None else settings.NODE_DAILY_MESSAGING_BUDGET_USD
    if daily_spend_usd >= limit:
        return False, f"Daily messaging budget exhausted (${daily_spend_usd:.2f} >= ${limit:.2f})."

    return True, "OK"


def sanitize_inbound_text(text: Optional[str], max_length: int = 500) -> str:
    """
    Sanitizes user input to prevent prompt injection and remove malicious links.
    1. Truncates length.
    2. Strips URL hyperlinks.
    3. Replaces prompt injection markers with safe placeholder.
    """
    if not text:
        return ""

    sanitized = text.strip()[:max_length]
    # Remove hyperlinks
    sanitized = URL_PATTERN.sub("[link removed]", sanitized)

    # Neutralize injection patterns
    for pat in INJECTION_PATTERNS:
        sanitized = pat.sub("[filtered]", sanitized)

    return sanitized.strip()
