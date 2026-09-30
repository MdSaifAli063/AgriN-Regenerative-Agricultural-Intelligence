"""KrishiNet-BRICS - Shared Data Provider Infrastructure.

Provides:
1. Base `DataProvider` interface with provenance tracking.
2. Two-layer caching architecture (Redis L1 cache + database persistence L2).
3. Per-provider rate limiting (specifically tuned for ISRIC SoilGrids 5 req/min).
4. Resilient HTTP client utilities with standard Digital Public Good User-Agent.
"""

import asyncio
import hashlib
import json
import logging
import time
from abc import ABC, abstractmethod
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional, Tuple

import httpx
from pydantic import BaseModel, Field
from redis.asyncio import Redis

from app.core.config import settings

logger = logging.getLogger("krishinet.intel.base")


class ProvenanceMetadata(BaseModel):
    """Sovereign data provenance badge visible to farmers and agronomy researchers."""

    source: str = Field(..., description="Upstream authoritative provider (e.g. ISRIC SoilGrids, Open-Meteo, Sentinel-2)")
    mode: Literal["live", "cache", "demo"] = Field(..., description="Acquisition mode: live API, cached record, or deterministic demo fixture")
    fetched_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat(),
        description="ISO 8601 UTC timestamp of retrieval",
    )
    ttl_seconds: int = Field(default=86400, description="Cache time-to-live in seconds")
    confidence: float = Field(default=0.95, ge=0.0, le=1.0, description="Data confidence index (0.0 - 1.0)")
    notes: Optional[str] = Field(default=None, description="Agronomic caveats or fallback rationale")


class ProviderRateLimiter:
    """Token bucket / sliding window rate limiter ensuring compliance with public API quotas."""

    def __init__(self, provider_name: str, max_requests_per_minute: int = 60):
        self.provider_name = provider_name
        self.max_requests = max_requests_per_minute
        self.timestamps: List[float] = []
        self._lock = asyncio.Lock()

    async def acquire(self) -> None:
        """Blocks until a request token is available within the sliding 60-second window."""
        async with self._lock:
            now = time.time()
            # Prune timestamps older than 60 seconds
            self.timestamps = [t for t in self.timestamps if now - t < 60.0]

            if len(self.timestamps) >= self.max_requests:
                oldest = self.timestamps[0]
                sleep_duration = max(0.1, 60.0 - (now - oldest) + 0.1)
                logger.warning(
                    f"[{self.provider_name}] Rate limit reached ({self.max_requests}/min). "
                    f"Throttling for {sleep_duration:.2f}s..."
                )
                await asyncio.sleep(sleep_duration)
                now = time.time()
                self.timestamps = [t for t in self.timestamps if now - t < 60.0]

            self.timestamps.append(now)


# Provider-specific rate limiters
# SoilGrids has strict rate limits; limit to 5 requests per minute
soilgrids_rate_limiter = ProviderRateLimiter("ISRIC_SoilGrids", max_requests_per_minute=5)
openmeteo_rate_limiter = ProviderRateLimiter("Open_Meteo", max_requests_per_minute=60)
stac_rate_limiter = ProviderRateLimiter("EarthSearch_STAC", max_requests_per_minute=30)


class IntelCache:
    """Two-layer cache manager: Redis (L1) with graceful fallback."""

    def __init__(self):
        self._redis: Optional[Redis] = None

    async def get_redis(self) -> Optional[Redis]:
        if self._redis is None:
            try:
                self._redis = Redis.from_url(
                    settings.REDIS_URL,
                    decode_responses=True,
                    socket_connect_timeout=1.0,
                    socket_timeout=1.0,
                )
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    @staticmethod
    def build_cache_key(provider: str, lat: float, lon: float, bucket: str = "daily") -> str:
        """Builds standardized cache key with rounded coordinate precision (~100m)."""
        rounded_lat = round(lat, 3)
        rounded_lon = round(lon, 3)
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if bucket == "monthly":
            date_token = datetime.now(timezone.utc).strftime("%Y-%m")
        elif bucket == "static":
            date_token = "static"
        else:
            date_token = today

        raw = f"{provider}:{rounded_lat}:{rounded_lon}:{date_token}"
        hashed = hashlib.md5(raw.encode("utf-8")).hexdigest()[:12]
        return f"krishi:intel:{provider}:{rounded_lat}_{rounded_lon}:{date_token}:{hashed}"

    async def get(self, key: str) -> Optional[Dict[str, Any]]:
        r = await self.get_redis()
        if not r:
            return None
        try:
            val = await r.get(key)
            if val:
                data = json.loads(val)
                logger.debug(f"Cache HIT for key: {key}")
                return data
        except Exception:
            pass
        return None

    async def set(self, key: str, value: Dict[str, Any], ttl_seconds: int = 86400) -> None:
        r = await self.get_redis()
        if not r:
            return
        try:
            await r.set(key, json.dumps(value), ex=ttl_seconds)
            logger.debug(f"Cache SET for key: {key} (TTL: {ttl_seconds}s)")
        except Exception:
            pass


intel_cache = IntelCache()


def get_intel_http_client(timeout_seconds: float = 10.0) -> httpx.AsyncClient:
    """Returns an HTTP client configured with respectful Digital Public Good headers."""
    headers = {
        "User-Agent": "KrishiNet-BRICS/1.0 (+https://krishinet.brics.int; Digital Public Good)",
        "Accept": "application/json",
    }
    return httpx.AsyncClient(headers=headers, timeout=timeout_seconds, follow_redirects=True)


class BaseDataProvider(ABC):
    """Abstract base class for environmental data providers."""

    @property
    @abstractmethod
    def provider_name(self) -> str:
        pass

    @property
    @abstractmethod
    def default_ttl_seconds(self) -> int:
        pass

    @abstractmethod
    async def fetch(self, centroid_lat: float, centroid_lon: float, **kwargs) -> Dict[str, Any]:
        """Fetches telemetry data with provenance metadata."""
        pass
