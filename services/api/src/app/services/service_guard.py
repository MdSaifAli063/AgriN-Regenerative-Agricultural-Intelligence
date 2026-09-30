import asyncio
import functools
import logging
import time
from typing import Any, Callable, Dict, Optional, TypeVar
from app.core.config import settings

logger = logging.getLogger("krishinet.guard")
T = TypeVar("T")


class CircuitBreakerOpenException(Exception):
    pass


class ExternalServiceGuard:
    """
    Resilience guardian for upstream external APIs (STAC, SoilGrids, Open-Meteo, Gemini).
    Features:
    1. Circuit Breaker (CLOSED -> OPEN -> HALF-OPEN -> CLOSED)
    2. Timeout protection
    3. Exponential backoff retry
    4. Deterministic Mock Fallback in Demo Mode
    """

    def __init__(
        self,
        service_name: str,
        fallback_factory: Optional[Callable[..., Any]] = None,
        timeout_seconds: float = 4.0,
        max_retries: int = 2,
        backoff_factor: float = 0.2,
        failure_threshold: int = 3,
        recovery_timeout: float = 30.0,
    ):
        self.service_name = service_name
        self.fallback_factory = fallback_factory
        self.timeout_seconds = timeout_seconds
        self.max_retries = max_retries
        self.backoff_factor = backoff_factor
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout

        # Circuit Breaker State
        self.state: str = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        self.failure_count: int = 0
        self.last_state_change: float = time.time()

    def _check_circuit(self) -> None:
        now = time.time()
        if self.state == "OPEN":
            if now - self.last_state_change > self.recovery_timeout:
                logger.info(f"[{self.service_name}] Circuit transitioning to HALF_OPEN")
                self.state = "HALF_OPEN"
                self.last_state_change = now
            else:
                raise CircuitBreakerOpenException(
                    f"Circuit breaker for '{self.service_name}' is OPEN. Fast failing."
                )

    def _record_success(self) -> None:
        self.failure_count = 0
        if self.state != "CLOSED":
            logger.info(f"[{self.service_name}] Circuit recovered to CLOSED")
            self.state = "CLOSED"
            self.last_state_change = time.time()

    def _record_failure(self) -> None:
        self.failure_count += 1
        if self.failure_count >= self.failure_threshold:
            logger.warning(
                f"[{self.service_name}] Failure threshold reached ({self.failure_count}). Tripping to OPEN."
            )
            self.state = "OPEN"
            self.last_state_change = time.time()

    async def execute(self, func: Callable[..., Any], *args: Any, **kwargs: Any) -> Any:
        # Check circuit state
        try:
            self._check_circuit()
        except CircuitBreakerOpenException:
            if settings.DEMO_MODE and self.fallback_factory:
                logger.info(f"[{self.service_name}] Circuit OPEN - returning Demo Fallback data.")
                if asyncio.iscoroutinefunction(self.fallback_factory):
                    return await self.fallback_factory(*args, **kwargs)
                return self.fallback_factory(*args, **kwargs)
            raise

        attempts = 0
        last_exception = None

        while attempts <= self.max_retries:
            try:
                # Execute with strict timeout
                if asyncio.iscoroutinefunction(func):
                    result = await asyncio.wait_for(func(*args, **kwargs), timeout=self.timeout_seconds)
                else:
                    result = func(*args, **kwargs)

                self._record_success()
                return result

            except Exception as e:
                attempts += 1
                last_exception = e
                logger.warning(
                    f"[{self.service_name}] Attempt {attempts} failed with {type(e).__name__}: {str(e)}"
                )
                if attempts <= self.max_retries:
                    await asyncio.sleep(self.backoff_factor * (2 ** (attempts - 1)))

        # All retries exhausted
        self._record_failure()

        # In DEMO_MODE, gracefully invoke fallback instead of throwing error
        if settings.DEMO_MODE and self.fallback_factory:
            logger.info(
                f"[{self.service_name}] Upstream failed. Gracefully serving DEMO_MODE mock data."
            )
            if asyncio.iscoroutinefunction(self.fallback_factory):
                return await self.fallback_factory(*args, **kwargs)
            return self.fallback_factory(*args, **kwargs)

        raise last_exception or RuntimeError(f"Service call to {self.service_name} failed.")


def guarded_service(
    service_name: str,
    fallback_factory: Optional[Callable[..., Any]] = None,
    timeout_seconds: float = 4.0,
    max_retries: int = 2,
):
    """Decorator syntax for ExternalServiceGuard."""
    guard = ExternalServiceGuard(
        service_name=service_name,
        fallback_factory=fallback_factory,
        timeout_seconds=timeout_seconds,
        max_retries=max_retries,
    )

    def decorator(fn: Callable[..., Any]):
        @functools.wraps(fn)
        async def wrapper(*args: Any, **kwargs: Any):
            return await guard.execute(fn, *args, **kwargs)

        return wrapper

    return decorator
