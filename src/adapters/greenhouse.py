"""
src/adapters/greenhouse.py  —  Greenhouse public JSON API adapter.
Endpoint: https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true
"""
from __future__ import annotations
import httpx, logging
from datetime import datetime
from typing import AsyncIterator
from src.adapters.base import AbstractJobAdapter, CanonicalJob

logger = logging.getLogger(__name__)

class GreenhouseAdapter(AbstractJobAdapter):
    source_name = "greenhouse"
    _BASE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs?content=true"

    def __init__(self, boards: list[str], http: httpx.AsyncClient):
        self.boards = boards
        self.http = http

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for board in self.boards:
            url = self._BASE.format(board=board)
            try:
                r = await self.http.get(url, timeout=15)
                r.raise_for_status()
                for raw in r.json().get("jobs", []):
                    yield self._transform(raw, board)
            except Exception as e:
                logger.error("Greenhouse[%s]: %s", board, e)

    def _transform(self, raw: dict, board: str) -> CanonicalJob:
        loc = raw.get("location", {}).get("name", "")
        return CanonicalJob(
            title=raw.get("title", ""),
            company_name=board.replace("-", " ").title(),
            source=self.source_name,
            source_url=raw.get("absolute_url", ""),
            source_id=str(raw.get("id", "")),
            description=raw.get("content", ""),
            location=loc,
            remote_type="remote" if "remote" in loc.lower() else None,
            posted_at=datetime.fromisoformat(raw["updated_at"].replace("Z", "+00:00"))
                      if raw.get("updated_at") else None,
            company_domain=f"{board}.com",
            raw_metadata=raw,
        )

    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self._BASE.format(board="stripe"), timeout=5)
            return r.status_code in (200, 404)
        except:
            return False