# ─── HackerNews "Who is Hiring" ───────────────────────────────────────────────
from __future__ import annotations

import asyncio
import logging
import re
from datetime import datetime, timezone
from typing import AsyncIterator
 
import httpx
 
from src.adapters.base import AbstractJobAdapter, CanonicalJob
 
logger = logging.getLogger(__name__)

class HackerNewsAdapter(AbstractJobAdapter):
    """
    Parses the monthly HN 'Ask HN: Who is Hiring?' thread via Algolia API.
    """
    source_name = "hackernews"
    _SEARCH = "https://hn.algolia.com/api/v1/search_by_date"
    _ITEM   = "https://hacker-news.firebaseio.com/v0/item/{id}.json"
 
    def __init__(self, http: httpx.AsyncClient):
        self.http = http
 
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        try:
            # Find the latest "Who is Hiring" thread
            r = await self.http.get(
                self._SEARCH,
                params={"query": "Ask HN: Who is Hiring?", "tags": "story,ask_hn"},
                timeout=10,
            )
            r.raise_for_status()
            hits = r.json().get("hits", [])
            if not hits:
                return
            thread_id = hits[0]["objectID"]
 
            # Get all top-level comments (job posts)
            tr = await self.http.get(self._ITEM.format(id=thread_id), timeout=10)
            tr.raise_for_status()
            kids = tr.json().get("kids", [])[:50]  # top 50 posts
 
            # Fetch comments concurrently
            async def fetch(kid_id: int):
                try:
                    cr = await self.http.get(self._ITEM.format(id=kid_id), timeout=8)
                    return cr.json()
                except:
                    return None
 
            comments = await asyncio.gather(*[fetch(k) for k in kids])
            for comment in comments:
                if comment and comment.get("text"):
                    job = self._transform(comment)
                    if job:
                        yield job
        except Exception as e:
            logger.error("HackerNews: %s", e)
 
    def _transform(self, raw: dict) -> CanonicalJob | None:
        text = raw.get("text", "")
        if not text or len(text) < 100:
            return None
        # Strip HTML
        plain = re.sub(r"<[^>]+>", " ", text)
        # Try to extract company name (usually first word before | or :)
        first_line = plain.split("\n")[0].strip()
        company = re.split(r"[|:]", first_line)[0].strip()[:60]
        return CanonicalJob(
            title=first_line[:120],
            company_name=company or "Unknown",
            source=self.source_name,
            source_url=f"https://news.ycombinator.com/item?id={raw.get('id')}",
            source_id=str(raw.get("id", "")),
            description=plain,
            remote_type="remote" if "remote" in plain.lower() else None,
            raw_metadata=raw,
        )
 
    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self._SEARCH, params={"query": "test"}, timeout=5)
            return r.status_code == 200
        except:
            return False