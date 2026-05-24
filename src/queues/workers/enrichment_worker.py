"""
src/queues/workers/enrichment_worker.py
Consumes jobs.enrich → runs JD analysis + company enrichment → publishes jobs.embed
"""
from __future__ import annotations

import asyncio
import logging

from src.queues.consumer import QueueConsumer
from src.queues.publisher import QueuePublisher
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


async def handle_enrich(payload: dict) -> None:
    """
    payload: {"job_id": str, "source": str}
    Steps:
      1. Load job from DB
      2. Run JD analysis (local LLM, cached)
      3. Run company enrichment (local LLM, cached)
      4. Update job record with extracted tech_stack, seniority, etc.
      5. Publish to jobs.embed for vector generation
    """
    job_id = payload.get("job_id")
    if not job_id:
        return

    from src.database.connection import get_session
    from src.database.repositories.job_repo import JobRepository
    from src.ai.router import AIRouter
    from src.ai.local_llm import OllamaClient
    from src.ai.gemini_client import GeminiClient
    from src.ai.cache import InferenceCache
    from src.enrichment.jd_analyzer import JDAnalyzer
    from src.enrichment.company_enricher import CompanyEnricher
    import httpx
    from uuid import UUID

    cache = InferenceCache()
    http = httpx.AsyncClient()
    local = OllamaClient(http)
    cloud = GeminiClient()
    router = AIRouter(cache=cache, local=local, cloud=cloud)
    jd_analyzer = JDAnalyzer(router)
    company_enricher = CompanyEnricher(router)

    async with get_session() as session:
        repo = JobRepository(session)
        job = await repo.get(UUID(job_id))
        if not job or job.enriched:
            return

        # Analyze JD
        if job.description:
            jd = await jd_analyzer.analyze(job.description)
            job.tech_stack = job.tech_stack or jd.tech_stack
            job.seniority = job.seniority or jd.seniority

        # Enrich company
        if job.company and job.company.domain:
            profile = await company_enricher.enrich(
                job.company.name,
                job.company.domain,
                context=job.description[:500] if job.description else "",
            )
            job.company.tech_stack = profile.tech_stack
            job.company.hiring_urgency = profile.hiring_urgency

        job.enriched = True
        job.opportunity_score = 5.0   # base score; updated after semantic ranking

    # Publish embedding task
    publisher = await QueuePublisher.connect(settings.rabbitmq_url)
    text = f"{job.title}\n{job.description or ''}"
    await publisher.publish("jobs.embed", {"job_id": job_id, "text": text[:2000]})
    logger.info("Enriched + queued embed for job %s", job_id)

    await http.aclose()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    consumer = QueueConsumer(settings.rabbitmq_url, "jobs.enrich")
    await consumer.run(handle_enrich, prefetch=5)


if __name__ == "__main__":
    asyncio.run(main())