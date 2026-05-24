"""
src/ai/cache.py

Redis-backed inference result cache.
Prevents duplicate LLM calls — the single biggest cost saver.
"""
from __future__ import annotations

import logging
from typing import Any

import redis.asyncio as aioredis
import redis as syncredis

from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# TTLs (seconds)
TTL_EMBEDDING  = 60 * 60 * 24 * 30   # 30 days  — embeddings rarely invalidate
TTL_JD_ANALYSIS = 60 * 60 * 24        # 24 hours — JD intent is stable
TTL_COMPANY    = 60 * 60 * 24 * 7     # 7 days   — company intel
TTL_GENERATION = 0                     # never cache — tailored resumes are per-request


class InferenceCache:
    def __init__(self) -> None:
        self._async = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._sync  = syncredis.from_url(settings.redis_url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        try:
            return await self._async.get(f"inference:{key}")
        except Exception as e:
            logger.debug("Cache GET error: %s", e)
            return None

    async def set(self, key: str, value: str, ttl: int = TTL_JD_ANALYSIS) -> None:
        if ttl == 0:
            return  # Explicitly non-cacheable
        try:
            await self._async.setex(f"inference:{key}", ttl, value)
        except Exception as e:
            logger.debug("Cache SET error: %s", e)

    def get_sync(self, key: str) -> bytes | None:
        """For embedding pipeline which runs synchronously."""
        try:
            v = self._sync.get(f"inference:{key}")
            return v.encode() if isinstance(v, str) else v
        except Exception:
            return None

    def set_sync(self, key: str, value: bytes, ttl: int = TTL_EMBEDDING) -> None:
        try:
            self._sync.setex(f"inference:{key}", ttl, value)
        except Exception:
            pass

    async def invalidate(self, key: str) -> None:
        await self._async.delete(f"inference:{key}")
