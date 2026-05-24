"""src/ai/cache.py"""
from __future__ import annotations
import logging
import redis.asyncio as aioredis
import redis as syncredis
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

TTL_EMBED   = 60 * 60 * 24 * 30
TTL_JD      = 60 * 60 * 24
TTL_COMPANY = 60 * 60 * 24 * 7


class InferenceCache:
    def __init__(self) -> None:
        self._a = aioredis.from_url(settings.redis_url, decode_responses=True)
        self._s = syncredis.from_url(settings.redis_url, decode_responses=True)

    async def get(self, key: str) -> str | None:
        try:
            return await self._a.get(f"inf:{key}")
        except Exception:
            return None

    async def set(self, key: str, value: str, ttl: int = TTL_JD) -> None:
        if ttl == 0:
            return
        try:
            await self._a.setex(f"inf:{key}", ttl, value)
        except Exception:
            pass

    def get_sync(self, key: str) -> bytes | None:
        try:
            v = self._s.get(f"inf:{key}")
            return v.encode() if isinstance(v, str) else v
        except Exception:
            return None

    def set_sync(self, key: str, value: bytes, ttl: int = TTL_EMBED) -> None:
        try:
            self._s.setex(f"inf:{key}", ttl, value)
        except Exception:
            pass