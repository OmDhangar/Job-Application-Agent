"""
src/ingestion/deduplicator.py

Fingerprint-based deduplication.
Two-layer check: Redis bloom filter (fast) → PostgreSQL unique constraint (authoritative).
"""
from __future__ import annotations

import logging

import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


class Deduplicator:
    """
    Uses Redis SET for O(1) duplicate detection during a scraping session.
    The DB unique constraint on `fingerprint` column is the final backstop.
    """

    REDIS_KEY = "ingestion:seen_fingerprints"
    TTL = 60 * 60 * 24 * 3  # 3 days — covers typical scraping cycles

    def __init__(self, redis: aioredis.Redis) -> None:
        self._redis = redis

    async def is_duplicate(self, fingerprint: str) -> bool:
        return bool(await self._redis.sismember(self.REDIS_KEY, fingerprint))

    async def mark_seen(self, fingerprint: str) -> None:
        await self._redis.sadd(self.REDIS_KEY, fingerprint)
        await self._redis.expire(self.REDIS_KEY, self.TTL)

    async def reset(self) -> None:
        """Call before a full re-scrape cycle to force re-evaluation."""
        await self._redis.delete(self.REDIS_KEY)
        logger.info("Deduplicator reset")
