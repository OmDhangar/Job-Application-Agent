"""
src/queues/workers/embedding_worker.py
Consumes jobs.embed → generates BGE embedding → stores in pgvector.
This is GPU-bound. Run as single-replica worker on the machine with the GPU.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.queues.consumer import QueueConsumer
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# Lazy-loaded — avoids loading 400MB model unless this worker is actually started
_embedder = None


def get_embedder():
    global _embedder
    if _embedder is None:
        from src.matching.embedder import LocalEmbedder
        from src.ai.cache import InferenceCache
        _embedder = LocalEmbedder(
            model_name=settings.embedding_model,
            cache=InferenceCache(),
            device=settings.embedding_device,
        )
    return _embedder


async def handle_embed(payload: dict) -> None:
    """
    payload: {"job_id": str, "text": str}
    """
    job_id = payload.get("job_id")
    text = payload.get("text", "")
    if not text or not job_id:
        logger.warning("Skipping embed — missing job_id or text")
        return

    embedder = get_embedder()
    vec = embedder.embed(text)

    # Persist to DB
    from src.database.connection import get_session
    from src.database.models.jobs import Embedding
    import uuid

    async with get_session() as session:
        emb = Embedding(
            entity_type="job",
            entity_id=UUID(job_id),
            embedding_model=settings.embedding_model,
            vector=vec.tolist(),
            chunk_text=text[:500],
        )
        session.add(emb)
    logger.info("Embedded job %s (%d dims)", job_id, len(vec))


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Embedding worker starting — model=%s device=%s",
                settings.embedding_model, settings.embedding_device)
    consumer = QueueConsumer(settings.rabbitmq_url, "jobs.embed")
    await consumer.run(handle_embed, prefetch=1)   # GPU: 1 at a time


if __name__ == "__main__":
    asyncio.run(main())