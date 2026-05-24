# ─── Deduplicator ─────────────────────────────────────────────────────────────

from __future__ import annotations
 
import asyncio
import logging
from datetime import datetime
 
import redis.asyncio as aioredis
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)

class Deduplicator:
    _KEY = "ingestion:seen"
    _TTL = 60 * 60 * 24 * 3   # 3 days

    def __init__(self, redis: aioredis.Redis) -> None:
        self._r = redis

    async def is_duplicate(self, fp: str) -> bool:
        return bool(await self._r.sismember(self._KEY, fp))

    async def mark_seen(self, fp: str) -> None:
        await self._r.sadd(self._KEY, fp)
        await self._r.expire(self._KEY, self._TTL)

    async def reset(self) -> None:
        await self._r.delete(self._KEY)
        logger.info("Deduplicator reset")