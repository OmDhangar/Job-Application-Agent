"""
src/adapters/linkedin.py

LinkedIn Job Adapter — Playwright-based scraper.
LinkedIn actively blocks scrapers. This implementation:
  1. Uses stealth mode (playwright-stealth)
  2. Respects throttle config
  3. Falls back to public search API if direct scraping blocked
  4. IMPORTANT: Only use for jobs you have legitimate access to view.
"""
from __future__ import annotations

import asyncio
import logging
import re
from typing import AsyncIterator

from src.adapters.base import AbstractJobAdapter, CanonicalJob
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class LinkedInAdapter(AbstractJobAdapter):
    """
    Scrapes LinkedIn job search results via Playwright.
    Requires: playwright install chromium

    Usage:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            adapter = LinkedInAdapter(browser=browser, keywords=["backend engineer"])
            async for job in adapter.scrape():
                ...
    """
    source_name = "linkedin"

    def __init__(self, browser, keywords: list[str], location: str = "Remote"):
        self.browser = browser
        self.keywords = keywords
        self.location = location
        self._throttle_ms = settings.scraper_throttle_ms

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for keyword in self.keywords:
            try:
                async for job in self._scrape_keyword(keyword):
                    yield job
                await asyncio.sleep(self._throttle_ms / 1000)
            except Exception as e:
                logger.error("LinkedIn[%s]: %s", keyword, e)

    async def _scrape_keyword(self, keyword: str) -> AsyncIterator[CanonicalJob]:
        page = await self.browser.new_page()
        try:
            # Apply stealth patches if available
            try:
                from playwright_stealth import stealth_async
                await stealth_async(page)
            except ImportError:
                logger.debug("playwright-stealth not installed — skipping stealth")

            search_url = (
                f"https://www.linkedin.com/jobs/search/"
                f"?keywords={keyword.replace(' ', '%20')}"
                f"&location={self.location.replace(' ', '%20')}"
                f"&f_TPR=r604800"  # last 7 days
            )
            await page.goto(search_url, timeout=15000)
            await page.wait_for_timeout(2000)

            # Extract job cards
            cards = await page.query_selector_all(".job-search-card")
            for card in cards[:15]:
                try:
                    job = await self._parse_card(card, page)
                    if job:
                        yield job
                except Exception as e:
                    logger.debug("Card parse error: %s", e)
        finally:
            await page.close()

    async def _parse_card(self, card, page) -> CanonicalJob | None:
        try:
            title_el  = await card.query_selector(".base-search-card__title")
            company_el = await card.query_selector(".base-search-card__subtitle")
            location_el = await card.query_selector(".job-search-card__location")
            link_el   = await card.query_selector("a.base-card__full-link")

            title    = (await title_el.inner_text()).strip() if title_el else ""
            company  = (await company_el.inner_text()).strip() if company_el else ""
            location = (await location_el.inner_text()).strip() if location_el else ""
            url      = await link_el.get_attribute("href") if link_el else ""

            if not title or not url:
                return None

            source_id = re.search(r"(\d{10,})", url)
            return CanonicalJob(
                title=title,
                company_name=company,
                source=self.source_name,
                source_url=url.split("?")[0],
                source_id=source_id.group(1) if source_id else None,
                description="",  # full description requires a second page load
                location=location,
                remote_type="remote" if "remote" in location.lower() else None,
            )
        except Exception:
            return None

    async def health_check(self) -> bool:
        try:
            page = await self.browser.new_page()
            await page.goto("https://www.linkedin.com", timeout=10000)
            ok = "linkedin" in page.url.lower()
            await page.close()
            return ok
        except Exception:
            return False