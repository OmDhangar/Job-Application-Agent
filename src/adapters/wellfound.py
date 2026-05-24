"""
src/adapters/wellfound.py  —  Wellfound (formerly AngelList Talent) adapter.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import AsyncIterator

import httpx

from src.adapters.base import AbstractJobAdapter, CanonicalJob
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


# ─── Wellfound ────────────────────────────────────────────────────────────────

class WellfoundAdapter(AbstractJobAdapter):
    """
    Wellfound public job search.
    Uses the undocumented JSON endpoint that powers their public job board.
    Rate limit: ~30 req/min — throttle to 1 req/2s.
    """
    source_name = "wellfound"
    _BASE = "https://wellfound.com/role/l"

    def __init__(self, roles: list[str], http: httpx.AsyncClient):
        """
        roles: list of role slugs, e.g. ["software-engineer", "backend-engineer"]
        """
        self.roles = roles
        self.http = http
        self._throttle = settings.scraper_throttle_ms / 1000

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for role in self.roles:
            try:
                async for job in self._scrape_role(role):
                    yield job
                await asyncio.sleep(self._throttle)
            except Exception as e:
                logger.error("Wellfound[%s]: %s", role, e)

    async def _scrape_role(self, role: str) -> AsyncIterator[CanonicalJob]:
        """
        Wellfound's public API returns job data as JSON embedded in page.
        Fallback: scrape the /role page HTML and extract listings.
        """
        url = f"https://wellfound.com/api/v2/tagged_jobs?slug={role}&page=1&per_page=20"
        try:
            r = await self.http.get(url, timeout=15)
            if r.status_code == 200:
                data = r.json()
                jobs = data.get("jobs", data.get("results", []))
                for raw in jobs:
                    job = self._transform(raw)
                    if job:
                        yield job
                return
        except Exception:
            pass

        # Fallback: HTML scraping
        html_url = f"{self._BASE}/{role}"
        try:
            r = await self.http.get(html_url, timeout=15, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            # Extract job cards from HTML
            matches = re.findall(
                r'"title":"([^"]+)".*?"company_name":"([^"]+)".*?"angellist_url":"([^"]+)"',
                r.text, re.DOTALL
            )
            for title, company, url in matches[:15]:
                yield CanonicalJob(
                    title=title, company_name=company,
                    source=self.source_name,
                    source_url=f"https://wellfound.com{url}" if url.startswith("/") else url,
                    description="",
                )
        except Exception as e:
            logger.error("Wellfound HTML fallback [%s]: %s", role, e)

    def _transform(self, raw: dict) -> CanonicalJob | None:
        title = raw.get("title") or raw.get("job_type", "")
        if not title:
            return None
        company = raw.get("startup", {}) or {}
        return CanonicalJob(
            title=title,
            company_name=company.get("name", raw.get("company_name", "")),
            source=self.source_name,
            source_url=raw.get("job_url", raw.get("angellist_url", "")),
            source_id=str(raw.get("id", "")),
            description=raw.get("description", ""),
            location=raw.get("location", ""),
            remote_type="remote" if raw.get("remote", False) else None,
            salary_min=raw.get("salary_min"),
            salary_max=raw.get("salary_max"),
            tech_stack=raw.get("skills", []),
            company_domain=company.get("company_url", "").replace("https://", "").split("/")[0],
            raw_metadata=raw,
        )

    async def health_check(self) -> bool:
        try:
            r = await self.http.get("https://wellfound.com", timeout=5)
            return r.status_code == 200
        except Exception:
            return False


