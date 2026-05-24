"""
src/queues/workers/ingestion_worker.py
Listens to jobs.raw → transforms → persists → publishes to jobs.enrich
"""
from __future__ import annotations
import asyncio, logging, os
from src.queues.consumer import QueueConsumer
from src.queues.publisher import QueuePublisher
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


async def handle_ingestion(payload: dict) -> None:
    logger.info("Ingestion job: %s", payload)
    # payload: {"source": str, "raw_payload_id": str}
    # In production: load raw payload from DB, run adapter transform, upsert job
    pass


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    consumer = QueueConsumer(settings.rabbitmq_url, "jobs.raw")
    await consumer.run(handle_ingestion, prefetch=10)


if __name__ == "__main__":
    asyncio.run(main())