"""
Country-Aware Provider Router and Resolution Engine.
Selects the appropriate provider based on Sovereign Node Country, recipient prefix, and DEMO_MODE.
"""

from typing import Dict, Optional
from app.core.config import settings
from app.messaging.providers.africas_talking import AfricasTalkingProvider
from app.messaging.providers.base import MessagingProvider
from app.messaging.providers.meta import MetaCloudProvider
from app.messaging.providers.simulator import SimulatorProvider
from app.messaging.providers.twilio import TwilioProvider

# Singleton simulator instance for demo state preservation and inspection
_simulator_instance = SimulatorProvider()

# Country to preferred provider mapping
COUNTRY_PROVIDER_MAP: Dict[str, str] = {
    "IND": "twilio",
    "BRA": "meta",
    "ZAF": "africastalking",
    "ETH": "africastalking",
    "EGY": "africastalking",
    "RUS": "twilio",
    "CHN": "twilio",
}


def get_simulator_provider() -> SimulatorProvider:
    """Returns the singleton SimulatorProvider instance."""
    return _simulator_instance


def get_messaging_provider(
    country_code: Optional[str] = None,
    preferred_provider: Optional[str] = None
) -> MessagingProvider:
    """
    Resolves the appropriate MessagingProvider implementation.
    If DEMO_MODE is active and no explicit real provider configured, returns SimulatorProvider.
    """
    if preferred_provider == "simulator" or (settings.DEMO_MODE and preferred_provider is None and settings.MESSAGING_DEFAULT_PROVIDER == "simulator"):
        return _simulator_instance

    target_country = country_code or settings.NODE_COUNTRY
    provider_name = preferred_provider or COUNTRY_PROVIDER_MAP.get(target_country, settings.MESSAGING_DEFAULT_PROVIDER)

    if provider_name == "twilio":
        return TwilioProvider()
    elif provider_name == "meta":
        return MetaCloudProvider()
    elif provider_name == "africastalking":
        return AfricasTalkingProvider()
    elif provider_name == "simulator":
        return _simulator_instance

    # Fallback to simulator
    return _simulator_instance
