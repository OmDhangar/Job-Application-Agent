# ─── Scheduler ────────────────────────────────────────────────────────────────
from __future__ import annotations
 
import asyncio
import logging
from datetime import datetime
 
import redis.asyncio as aioredis
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)

from src.ingestion.pipeline import IngestionPipeline

def build_scheduler(pipeline: IngestionPipeline):
    """
    Build an APScheduler that runs the pipeline on a cron.
    Import and start this in the worker entrypoint.
    """
    from apscheduler.schedulers.asyncio import AsyncIOScheduler
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        pipeline.run,
        trigger="cron",
        hour="*/4",   # every 4 hours
        id="ingestion",
        replace_existing=True,
        misfire_grace_time=300,
    )
    return scheduler