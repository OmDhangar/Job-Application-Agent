# ─── Lever ────────────────────────────────────────────────────────────────────
from __future__ import annotations
 
import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator
 
import httpx
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)

class LeverAdapter(AbstractJobAdapter):
    """Lever public postings: https://api.lever.co/v0/postings/{company}?mode=json"""
    source_name = "lever"
    _BASE = "https://api.lever.co/v0/postings/{company}?mode=json"
 
    def __init__(self, companies: list[str], http: httpx.AsyncClient):
        self.companies = companies
        self.http = http
 
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for company in self.companies:
            try:
                r = await self.http.get(self._BASE.format(company=company), timeout=15)
                r.raise_for_status()
                for raw in r.json():
                    yield self._transform(raw, company)
            except Exception as e:
                logger.error("Lever[%s]: %s", company, e)
 
    def _transform(self, raw: dict, company: str) -> CanonicalJob:
        cats = raw.get("categories", {})
        return CanonicalJob(
            title=raw.get("text", ""),
            company_name=company.replace("-", " ").title(),
            source=self.source_name,
            source_url=raw.get("hostedUrl", ""),
            source_id=raw.get("id"),
            description=raw.get("descriptionPlain", ""),
            location=cats.get("location"),
            remote_type=cats.get("commitment", "").lower() or None,
            seniority=cats.get("level"),
            posted_at=datetime.fromtimestamp(raw["createdAt"] / 1000, tz=timezone.utc)
                      if raw.get("createdAt") else None,
            company_domain=f"{company}.com",
            raw_metadata=raw,
        )
 
    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self._BASE.format(company="figma"), timeout=5)
            return r.status_code in (200, 404)
        except:
            return False
 