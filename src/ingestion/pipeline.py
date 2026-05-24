
from __future__ import annotations

import asyncio
import logging
from datetime import datetime

import redis.asyncio as aioredis

from src.adapters.base import AbstractJobAdapter, CanonicalJob

logger = logging.getLogger(__name__)


# ─── Ingestion Pipeline ───────────────────────────────────────────────────────

class IngestionPipeline:
    """
    Runs all adapters concurrently, deduplicates via Redis,
    persists to DB, publishes enrichment tasks to queue.
    """

    def __init__(
        self,
        adapters: list[AbstractJobAdapter],
        deduplicator: Deduplicator,
        job_repo,            # JobRepository (imported at runtime to avoid circular)
        publisher,           # QueuePublisher
    ) -> None:
        self.adapters = adapters
        self.dedup = deduplicator
        self.repo = job_repo
        self.publisher = publisher

    async def run(self) -> dict[str, int]:
        stats: dict[str, int] = {a.source_name: 0 for a in self.adapters}
        await asyncio.gather(
            *[self._drain(a, stats) for a in self.adapters],
            return_exceptions=True,
        )
        logger.info("Ingestion complete: %s", stats)
        return stats

    async def _drain(self, adapter: AbstractJobAdapter, stats: dict) -> None:
        try:
            async for job in adapter.scrape():
                if await self.dedup.is_duplicate(job.fingerprint):
                    continue
                try:
                    record = await self.repo.upsert(job)
                    await self.publisher.publish(
                        "jobs.enrich",
                        {"job_id": str(record.id), "source": job.source},
                    )
                    await self.dedup.mark_seen(job.fingerprint)
                    stats[adapter.source_name] += 1
                except Exception as e:
                    logger.error("Persist failed [%s]: %s", adapter.source_name, e)
        except Exception as e:
            logger.error("Adapter %s crashed: %s", adapter.source_name, e)


