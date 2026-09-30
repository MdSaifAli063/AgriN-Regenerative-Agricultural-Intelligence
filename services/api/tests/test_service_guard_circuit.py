import asyncio
import os
import sys
import time
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "src")))

from app.core.config import settings
from app.services.service_guard import ExternalServiceGuard, CircuitBreakerOpenException


@pytest.fixture(autouse=True)
def preserve_demo_mode():
    orig = settings.DEMO_MODE
    yield
    settings.DEMO_MODE = orig



@pytest.mark.asyncio
async def test_circuit_trips_to_open_after_threshold():
    """Validates that consecutive failures cause state transition from CLOSED to OPEN."""
    settings.DEMO_MODE = False  # Raise exceptions instead of masking with fallback

    guard = ExternalServiceGuard(
        service_name="TestWeatherAPI",
        failure_threshold=2,
        max_retries=0,
        timeout_seconds=0.5,
        recovery_timeout=10.0,
    )

    async def broken_call():
        raise ConnectionError("Upstream server 503")

    # Attempt 1
    with pytest.raises(ConnectionError):
        await guard.execute(broken_call)
    assert guard.state == "CLOSED"
    assert guard.failure_count == 1

    # Attempt 2 - reaches threshold of 2
    with pytest.raises(ConnectionError):
        await guard.execute(broken_call)
    assert guard.state == "OPEN"


@pytest.mark.asyncio
async def test_circuit_fast_fail_in_open_state():
    """Validates that calls in OPEN state do not invoke target function and fast-fail or return fallback."""
    settings.DEMO_MODE = True

    guard = ExternalServiceGuard(
        service_name="TestOpenCircuitService",
        fallback_factory=lambda: {"fallback": True, "value": "demo_cached"},
        failure_threshold=1,
        max_retries=0,
        recovery_timeout=30.0,
    )

    call_counter = 0

    async def flaky_service():
        nonlocal call_counter
        call_counter += 1
        raise TimeoutError("Socket timeout")

    # First call fails and trips breaker to OPEN
    res1 = await guard.execute(flaky_service)
    assert res1["fallback"] is True
    assert guard.state == "OPEN"
    assert call_counter == 1

    # Second call should fast-fail into fallback without calling flaky_service again
    res2 = await guard.execute(flaky_service)
    assert res2["fallback"] is True
    assert call_counter == 1  # Function was NOT called


@pytest.mark.asyncio
async def test_circuit_half_open_recovery_to_closed():
    """Validates transition from OPEN -> HALF_OPEN -> CLOSED on successful probe call."""
    settings.DEMO_MODE = False

    guard = ExternalServiceGuard(
        service_name="TestRecoveringService",
        failure_threshold=1,
        max_retries=0,
        recovery_timeout=0.05,  # 50ms recovery window for testing
    )

    # Trip the circuit to OPEN
    async def initial_failure():
        raise RuntimeError("Service temporarily down")

    with pytest.raises(RuntimeError):
        await guard.execute(initial_failure)
    assert guard.state == "OPEN"

    # Wait for recovery timeout to elapse
    await asyncio.sleep(0.06)

    # Now the service has recovered
    async def recovered_service():
        return {"status": "recovered_live_data"}

    res = await guard.execute(recovered_service)
    assert res["status"] == "recovered_live_data"
    assert guard.state == "CLOSED"
    assert guard.failure_count == 0
