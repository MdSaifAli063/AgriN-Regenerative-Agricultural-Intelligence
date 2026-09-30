"""Messaging gateway package exports."""

from app.messaging.crypto import (
    decrypt_phone_number,
    encrypt_phone_number,
    hash_phone_number,
    normalize_phone_number,
)
from app.messaging.providers import (
    AfricasTalkingProvider,
    DeliveryStatusDTO,
    InboundMessageDTO,
    MessagingProvider,
    MetaCloudProvider,
    OutboundResult,
    SimulatorProvider,
    TwilioProvider,
    get_messaging_provider,
    get_simulator_provider,
)
from app.messaging.safety import (
    check_daily_cost_budget,
    check_outbound_rate_limit,
    is_opt_in_keyword,
    is_opt_out_keyword,
    is_within_quiet_hours,
    sanitize_inbound_text,
)
from app.messaging.segment_calc import calculate_segments, shorten_to_segments
from app.messaging.engine import (
    ConversationEngine,
    SUPPORTED_LOCALES,
    detect_language_heuristic,
    geocode_place_name,
    get_message,
    strip_exif,
)
from app.messaging.alerts import (
    dispatch_morning_digests,
    dispatch_outbreak_alert,
    dispatch_weather_alert,
    purge_expired_message_bodies,
)

__all__ = [
    "MessagingProvider",
    "InboundMessageDTO",
    "OutboundResult",
    "DeliveryStatusDTO",
    "TwilioProvider",
    "MetaCloudProvider",
    "AfricasTalkingProvider",
    "SimulatorProvider",
    "get_messaging_provider",
    "get_simulator_provider",
    "normalize_phone_number",
    "hash_phone_number",
    "encrypt_phone_number",
    "decrypt_phone_number",
    "calculate_segments",
    "shorten_to_segments",
    "is_opt_out_keyword",
    "is_opt_in_keyword",
    "is_within_quiet_hours",
    "check_outbound_rate_limit",
    "check_daily_cost_budget",
    "sanitize_inbound_text",
    "ConversationEngine",
    "detect_language_heuristic",
    "strip_exif",
    "geocode_place_name",
    "SUPPORTED_LOCALES",
    "get_message",
    "dispatch_morning_digests",
    "dispatch_weather_alert",
    "dispatch_outbreak_alert",
    "purge_expired_message_bodies",
]
