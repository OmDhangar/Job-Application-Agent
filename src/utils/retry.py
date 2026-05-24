"""
src/utils/retry.py

Async retry decorator with exponential back-off and jitter.
Used by adapters, AI clients, and queue workers for resilient operation.
"""
from __future__ import annotations

import asyncio
import functools
import logging
import random
from typing import Any, Callable, Sequence, Type

logger = logging.getLogger(__name__)

# Exceptions that should always be retried
TRANSIENT_EXCEPTIONS: tuple[Type[Exception], ...] = (
    ConnectionError,
    TimeoutError,
    asyncio.TimeoutError,
)


def async_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable: Sequence[Type[Exception]] = TRANSIENT_EXCEPTIONS,
    on_retry: Callable[[Exception, int], Any] | None = None,
):
    """
    Decorator that retries an async function on specified exceptions.

    Args:
        max_attempts:   Total attempts (first try + retries).
        base_delay:     Initial delay in seconds before the first retry.
        max_delay:      Cap for the back-off delay.
        backoff_factor: Multiplier applied to delay after each retry.
        retryable:      Exception classes that trigger a retry.
        on_retry:       Optional callback(exc, attempt) called before sleeping.
    """

    def decorator(func):
        @functools.wraps(func)
        async def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return await func(*args, **kwargs)
                except tuple(retryable) as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        logger.error(
                            "%s failed after %d attempts: %s",
                            func.__qualname__,
                            max_attempts,
                            exc,
                        )
                        raise

                    jitter = random.uniform(0, delay * 0.5)
                    sleep_time = min(delay + jitter, max_delay)

                    if on_retry:
                        on_retry(exc, attempt)

                    logger.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_time,
                    )
                    await asyncio.sleep(sleep_time)
                    delay *= backoff_factor

            # Should never reach here, but just in case
            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator


def sync_retry(
    max_attempts: int = 3,
    base_delay: float = 1.0,
    max_delay: float = 30.0,
    backoff_factor: float = 2.0,
    retryable: Sequence[Type[Exception]] = TRANSIENT_EXCEPTIONS,
):
    """Synchronous version of async_retry for blocking code paths."""
    import time

    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            delay = base_delay
            last_exc: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except tuple(retryable) as exc:
                    last_exc = exc
                    if attempt == max_attempts:
                        raise
                    jitter = random.uniform(0, delay * 0.5)
                    sleep_time = min(delay + jitter, max_delay)
                    logger.warning(
                        "%s attempt %d/%d failed (%s), retrying in %.1fs",
                        func.__qualname__,
                        attempt,
                        max_attempts,
                        exc,
                        sleep_time,
                    )
                    time.sleep(sleep_time)
                    delay *= backoff_factor

            raise last_exc  # type: ignore[misc]

        return wrapper

    return decorator
