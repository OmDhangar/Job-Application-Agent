# ─── YC Jobs ──────────────────────────────────────────────────────────────────
from __future__ import annotations
 
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator
 
import httpx
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)
 
class YCJobsAdapter(AbstractJobAdapter):
    """
    YC Work at a Startup — public JSON API.
    https://www.workatastartup.com/jobs  (JSON endpoint)
    """
    source_name = "yc_jobs"
    _BASE = "https://www.workatastartup.com/jobs.json"
 
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
 
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        try:
            r = await self.http.get(self._BASE, timeout=20)
            r.raise_for_status()
            jobs = r.json()
            if isinstance(jobs, dict):
                jobs = jobs.get("jobs", [])
            for raw in jobs:
                yield self._transform(raw)
        except Exception as e:
            logger.error("YC Jobs: %s", e)
            return
 
    def _transform(self, raw: dict) -> CanonicalJob:
        company = raw.get("company", {})
        return CanonicalJob(
            title=raw.get("title", ""),
            company_name=company.get("name", ""),
            source=self.source_name,
            source_url=raw.get("url", ""),
            source_id=str(raw.get("id", "")),
            description=raw.get("description", ""),
            location=raw.get("location", ""),
            remote_type="remote" if raw.get("remote") else None,
            employment_type=raw.get("job_type"),
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            tech_stack=raw.get("tags", []),
            company_domain=company.get("url", "").replace("https://", "").split("/")[0],
            raw_metadata=raw,
        )
 
    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self._BASE, timeout=5)
            return r.status_code == 200
        except:
            return False
 