"""Provider resilience primitives (retry + circuit breaker)."""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from typing import Callable, TypeVar

T = TypeVar("T")

logger = logging.getLogger(__name__)


@dataclass
class CircuitState:
    failures: int = 0
    opened_at: float | None = None


_CIRCUITS: dict[str, CircuitState] = {}


def _sleep_backoff(base_seconds: float, attempt: int) -> None:
    time.sleep(base_seconds * (2 ** attempt))


def execute_with_resilience(
    provider_name: str,
    operation: Callable[[], T],
    *,
    retries: int = 2,
    backoff_seconds: float = 0.2,
    failure_threshold: int = 3,
    reset_timeout_seconds: float = 60.0,
) -> T | None:
    """Execute provider operation with retry and circuit-breaker semantics."""
    state = _CIRCUITS.setdefault(provider_name, CircuitState())
    now = time.time()

    if state.opened_at and (now - state.opened_at) < reset_timeout_seconds:
        logger.warning("circuit open for provider=%s", provider_name)
        return None
    if state.opened_at and (now - state.opened_at) >= reset_timeout_seconds:
        state.opened_at = None
        state.failures = 0

    for attempt in range(retries + 1):
        try:
            result = operation()
            state.failures = 0
            state.opened_at = None
            return result
        except Exception as exc:
            state.failures += 1
            logger.warning(
                "provider call failed provider=%s attempt=%s/%s error=%s",
                provider_name,
                attempt + 1,
                retries + 1,
                exc,
            )
            if state.failures >= failure_threshold:
                state.opened_at = time.time()
                logger.error("circuit opened for provider=%s failures=%s", provider_name, state.failures)
                return None
            if attempt < retries:
                _sleep_backoff(backoff_seconds, attempt)

    return None
