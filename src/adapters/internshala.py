# ─── Internshala ──────────────────────────────────────────────────────────────
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

class InternshalaAdapter(AbstractJobAdapter):
    """
    Internshala adapter — targets Indian internship and fresher job market.
    Uses their public search API (JSON endpoint discovered from XHR).
    """
    source_name = "internshala"
    _SEARCH = "https://internshala.com/internships/search-internships/"

    def __init__(self, keywords: list[str], http: httpx.AsyncClient):
        self.keywords = keywords
        self.http = http
        self._throttle = settings.scraper_throttle_ms / 1000

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for keyword in self.keywords:
            try:
                async for job in self._scrape_keyword(keyword):
                    yield job
                await asyncio.sleep(self._throttle)
            except Exception as e:
                logger.error("Internshala[%s]: %s", keyword, e)

    async def _scrape_keyword(self, keyword: str) -> AsyncIterator[CanonicalJob]:
        params = {"keywords": keyword, "start": 0, "limit": 20}
        headers = {
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": "https://internshala.com/internships",
        }
        try:
            r = await self.http.get(
                "https://internshala.com/internships_json/",
                params=params, headers=headers, timeout=15,
            )
            r.raise_for_status()
            data = r.json()
            for raw in data.get("internships_meta", {}).values():
                job = self._transform(raw)
                if job:
                    yield job
        except Exception as e:
            logger.error("Internshala API [%s]: %s", keyword, e)

    def _transform(self, raw: dict) -> CanonicalJob | None:
        title = raw.get("profile_name", "")
        company = raw.get("company_name", "")
        if not title or not company:
            return None

        slug = raw.get("id", "")
        return CanonicalJob(
            title=title,
            company_name=company,
            source=self.source_name,
            source_url=f"https://internshala.com/internship/detail/{slug}",
            source_id=str(slug),
            description=raw.get("other_detail", ""),
            location=raw.get("location_names", ["Remote"])[0] if raw.get("location_names") else None,
            remote_type="remote" if raw.get("work_from_home") else None,
            employment_type="internship",
            salary_min=self._parse_salary(raw.get("stipend", {}).get("salary", "")),
            tech_stack=[s["name"] for s in raw.get("skill_ids", []) if s.get("name")],
            raw_metadata=raw,
        )

    def _parse_salary(self, salary_str: str) -> int | None:
        if not salary_str:
            return None
        match = re.search(r"(\d[\d,]+)", str(salary_str).replace(",", ""))
        return int(match.group(1)) if match else None

    async def health_check(self) -> bool:
        try:
            r = await self.http.get("https://internshala.com", timeout=5)
            return r.status_code == 200
        except Exception:
            return False