import asyncio
import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.core.config import settings
from app.services.service_guard import ExternalServiceGuard, guarded_service


@pytest.mark.asyncio
async def test_guard_success():
    """Validates that a working primary function returns immediately without invoking fallback."""
    guard = ExternalServiceGuard(
        service_name="TestGoodService",
        fallback_factory=lambda: {"status": "fallback"},
    )

    async def good_call():
        return {"status": "real_data", "value": 42}

    result = await guard.execute(good_call)
    assert result["status"] == "real_data"
    assert result["value"] == 42
    assert guard.state == "CLOSED"


@pytest.mark.asyncio
async def test_guard_fallback_when_primary_raises():
    """Proves that when the primary external call raises an exception, the fallback is safely returned."""
    # Ensure DEMO_MODE is True
    settings.DEMO_MODE = True

    guard = ExternalServiceGuard(
        service_name="FailingExternalWeatherAPI",
        fallback_factory=lambda: {
            "status": "demo_fallback",
            "temp_c": 28.5,
            "provider": "Mock Weather Cache",
        },
        timeout_seconds=1.0,
        max_retries=1,
        backoff_factor=0.01,
    )

    async def failing_network_call():
        raise ConnectionError("DNS resolution failed: api.open-meteo.com unreachable")

    result = await guard.execute(failing_network_call)
    assert result["status"] == "demo_fallback"
    assert result["temp_c"] == 28.5
    assert result["provider"] == "Mock Weather Cache"


@pytest.mark.asyncio
async def test_guard_decorator_syntax():
    """Validates decorator syntax with automatic fallback."""
    settings.DEMO_MODE = True

    @guarded_service(
        service_name="MockSatelliteSTAC",
        fallback_factory=lambda: {"ndvi": 0.65, "source": "Cached STAC Fallback"},
        timeout_seconds=0.5,
        max_retries=1,
    )
    async def flaky_satellite_fetch():
        raise TimeoutError("Copernicus STAC timed out after 30s")

    result = await flaky_satellite_fetch()
    assert result["ndvi"] == 0.65
    assert result["source"] == "Cached STAC Fallback"
