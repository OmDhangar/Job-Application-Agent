# ─── Ashby ────────────────────────────────────────────────────────────────────
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator
 
import httpx
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)
class AshbyAdapter(AbstractJobAdapter):
    """Ashby public postings API."""
    source_name = "ashby"
    _BASE = "https://jobs.ashbyhq.com/api/non-user-graphql"
 
    def __init__(self, slugs: list[str], http: httpx.AsyncClient):
        self.slugs = slugs
        self.http = http
 
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for slug in self.slugs:
            try:
                payload = {
                    "operationName": "ApiJobBoardWithTeams",
                    "variables": {"organizationHostedJobsPageName": slug},
                    "query": (
                        "query ApiJobBoardWithTeams($organizationHostedJobsPageName:String!)"
                        "{jobBoard(organizationHostedJobsPageName:$organizationHostedJobsPageName)"
                        "{jobPostings{id title isRemote locationName employmentType "
                        "descriptionHtml publishedAt externalLink}}}"
                    ),
                }
                r = await self.http.post(self._BASE, json=payload, timeout=15)
                r.raise_for_status()
                postings = (
                    r.json()
                    .get("data", {})
                    .get("jobBoard", {})
                    .get("jobPostings", [])
                )
                for raw in postings:
                    yield self._transform(raw, slug)
            except Exception as e:
                logger.error("Ashby[%s]: %s", slug, e)
 
    def _transform(self, raw: dict, slug: str) -> CanonicalJob:
        # Strip HTML from description
        desc = re.sub(r"<[^>]+>", " ", raw.get("descriptionHtml", ""))
        return CanonicalJob(
            title=raw.get("title", ""),
            company_name=slug.replace("-", " ").title(),
            source=self.source_name,
            source_url=raw.get("externalLink", f"https://jobs.ashbyhq.com/{slug}"),
            source_id=raw.get("id"),
            description=desc,
            location=raw.get("locationName"),
            remote_type="remote" if raw.get("isRemote") else None,
            employment_type=raw.get("employmentType"),
            posted_at=datetime.fromisoformat(raw["publishedAt"].replace("Z", "+00:00"))
                      if raw.get("publishedAt") else None,
            company_domain=f"{slug}.com",
            raw_metadata=raw,
        )
 
    async def health_check(self) -> bool:
        return True