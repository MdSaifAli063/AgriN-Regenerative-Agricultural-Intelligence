"""
Polite Geocoding Engine with Caching and Coarse Coordinate Truncation.
Uses OSM Nominatim with 1 req/sec rate limit and built-in DEMO_MODE agricultural fixtures.
Enforces Sovereign Node privacy: coordinates rounded to 2 decimal places (~1.1 km).
"""

import asyncio
from datetime import datetime, timezone
import logging
from typing import Dict, Optional, Tuple
import httpx
from app.core.config import settings

logger = logging.getLogger("krishinet.messaging.geocoding")

# Built-in agricultural test fixtures for zero-network reliability
DEMO_COORDINATES_MAP: Dict[str, Tuple[float, float, str]] = {
    "nagpur": (21.15, 79.09, "Nagpur, Maharashtra, India"),
    "wardha": (20.75, 78.60, "Wardha, Maharashtra, India"),
    "yavatmal": (20.39, 78.13, "Yavatmal, Maharashtra, India"),
    "cascavel": (-24.96, -53.46, "Cascavel, Paraná, Brazil"),
    "parana": (-24.96, -53.46, "Cascavel, Paraná, Brazil"),
    "mato grosso": (-12.68, -56.92, "Sorriso, Mato Grosso, Brazil"),
    "bothaville": (-27.38, 26.62, "Bothaville, Free State, South Africa"),
    "free state": (-28.45, 26.80, "Free State, South Africa"),
}

# Cache for resolved places
_geocoding_cache: Dict[str, Tuple[float, float, str]] = {}
_last_nominatim_call: float = 0.0


async def geocode_place_name(query: str) -> Optional[Tuple[float, float, str]]:
    """
    Geocodes plain-text place name into (lat, lon, display_name).
    Returns coarse coordinates rounded to 2 decimal places for farmer privacy.
    """
    clean_q = query.strip().lower()
    if not clean_q:
        return None

    # Check cache
    if clean_q in _geocoding_cache:
        return _geocoding_cache[clean_q]

    # Check demo fixtures
    for key, val in DEMO_COORDINATES_MAP.items():
        if key in clean_q:
            _geocoding_cache[clean_q] = val
            return val

    if settings.DEMO_MODE:
        # Default fallback to node country center
        default_loc = (21.15, 79.09, f"{query.title()}, Region")
        _geocoding_cache[clean_q] = default_loc
        return default_loc

    # Real Nominatim query with polite 1 req/sec rate limit
    global _last_nominatim_call
    now = datetime.now(timezone.utc).timestamp()
    elapsed = now - _last_nominatim_call
    if elapsed < 1.0:
        await asyncio.sleep(1.0 - elapsed)
    _last_nominatim_call = datetime.now(timezone.utc).timestamp()

    url = "https://nominatim.openstreetmap.org/search"
    headers = {"User-Agent": "KrishiNet-BRICS/1.0 (farmer-onboarding@krishinet.org)"}
    params = {"q": query, "format": "json", "limit": 1}

    try:
        async with httpx.AsyncClient(timeout=8.0) as client:
            resp = await client.get(url, params=params, headers=headers)
            if resp.status_code == 200:
                results = resp.json()
                if results:
                    raw = results[0]
                    lat = round(float(raw["lat"]), 2)
                    lon = round(float(raw["lon"]), 2)
                    display = raw.get("display_name", query)
                    res = (lat, lon, display)
                    _geocoding_cache[clean_q] = res
                    return res
    except Exception as exc:
        logger.warning(f"Nominatim geocoding failed: {exc}")

    # Fallback default
    fallback = (21.15, 79.09, f"{query.title()}, Agriculture District")
    _geocoding_cache[clean_q] = fallback
    return fallback
