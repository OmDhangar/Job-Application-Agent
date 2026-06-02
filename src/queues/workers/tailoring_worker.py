"""
src/queues/workers/tailoring_worker.py

Consumes tailoring.request → runs the multi-phase TailoringWorkflow →
updates application record with tailored resume and multi-dimensional scores.
"""
from __future__ import annotations

import asyncio
import logging
from uuid import UUID

from src.queues.consumer import QueueConsumer
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


async def handle_tailoring(payload: dict) -> None:
    """
    payload: {
        "application_id": str,
        "resume_text": str,
        "job_description": str,
        "job_id": str
    }
    """
    app_id_str = payload.get("application_id")
    resume_text = payload.get("resume_text")
    job_description = payload.get("job_description")
    job_id_str = payload.get("job_id")

    if not all([app_id_str, resume_text, job_description, job_id_str]):
        logger.error("Missing required tailoring parameters in payload: %s", payload)
        return

    from src.database.connection import get_session
    from src.database.models.candidates import Application
    from src.ai.router import AIRouter
    from src.ai.local_llm import OllamaClient
    from src.ai.gemini_client import GeminiClient
    from src.ai.cache import InferenceCache
    from src.enrichment.jd_analyzer import JDAnalyzer
    from src.tailoring.strategy_generator import StrategyGenerator
    from src.tailoring.scorer import ResumeScorer
    from src.workflows.tailoring import TailoringWorkflow
    import httpx

    logger.info("Initializing tailoring services for application: %s", app_id_str)
    
    cache = InferenceCache()
    http_client = httpx.AsyncClient(timeout=httpx.Timeout(timeout=300.0, connect=10.0))
    local = OllamaClient(http_client)
    cloud = GeminiClient()
    router = AIRouter(cache=cache, local=local, cloud=cloud)
    
    jd_analyzer = JDAnalyzer(router)
    strategy = StrategyGenerator()
    scorer = ResumeScorer()
    
    workflow = TailoringWorkflow(
        ai_router=router,
        jd_analyzer=jd_analyzer,
        strategy_generator=strategy,
        scorer=scorer,
    )

    try:
        logger.info("Running TailoringWorkflow for app: %s", app_id_str)
        result = await workflow.run(
            resume_text=resume_text,
            job_description=job_description,
            job_id=job_id_str,
        )

        logger.info("Saving tailoring results to DB for app: %s", app_id_str)
        async with get_session() as session:
            # Query application
            app_id = UUID(app_id_str)
            app = await session.get(Application, app_id)
            if not app:
                logger.error("Application %s not found in database", app_id_str)
                await http_client.aclose()
                return

            scores = result["scores"]
            app.tailored_resume = result["tailored_resume"]
            app.ats_score = scores.ats_score
            app.authenticity_score = scores.authenticity_score
            app.recruiter_score = scores.recruiter_readability
            app.interview_probability = scores.interview_probability
            app.status = "tailored"
            app.notes = (app.notes or "") + "\nResume tailored successfully. Critique summary:\n" + result["critique"][:500]
            
            session.add(app)
            
        logger.info("Tailoring worker completed successfully for app: %s", app_id_str)

    except Exception as e:
        logger.exception("Tailoring execution failed for app %s: %s", app_id_str, e)
        async with get_session() as session:
            app_id = UUID(app_id_str)
            app = await session.get(Application, app_id)
            if app:
                app.notes = (app.notes or "") + f"\nTailoring failed: {str(e)}"
                session.add(app)

    finally:
        await http_client.aclose()


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    logger.info("Tailoring worker starting...")
    consumer = QueueConsumer(settings.rabbitmq_url, "tailoring.request")
    await consumer.run(handle_tailoring, prefetch=1)  # LLM/parsing tasks: 1 at a time


if __name__ == "__main__":
    asyncio.run(main())
