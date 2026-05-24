"""
src/enrichment/company_enricher.py

Enriches a company record with tech stack, stage, hiring urgency,
engineering culture signals. Uses local LLM + optional web scraping.
Results cached in Redis for 7 days.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from src.ai.router import AIRouter, TaskComplexity

logger = logging.getLogger(__name__)


@dataclass
class CompanyProfile:
    name: str
    domain: str
    stage: str = "unknown"                    # seed|series_a|series_b|growth|public
    headcount_range: str = "unknown"          # 1-10|11-50|51-200|201-500|500+
    tech_stack: list[str] = field(default_factory=list)
    engineering_culture: dict = field(default_factory=dict)
    hiring_urgency: int = 5                   # 0-10
    recent_signals: list[str] = field(default_factory=list)  # funding, launches, etc.
    key_contacts: list[dict] = field(default_factory=list)   # name, role, linkedin


_SYSTEM = "You are a startup analyst. Return ONLY valid JSON. No preamble."
_PROMPT = """
Analyze this company based on available information and return JSON:
- stage: seed|series_a|series_b|growth|public|unknown
- headcount_range: 1-10|11-50|51-200|201-500|500+|unknown
- tech_stack: array of technologies (infer from job postings if needed)
- engineering_culture: dict with keys remote_friendly(bool), eng_blog(str|null), 
  work_style(string), values(array)
- hiring_urgency: integer 0-10 (10=very urgent, based on number of open roles)
- recent_signals: array of strings (funding, product launches, acquisitions)

COMPANY NAME: {name}
DOMAIN: {domain}
ADDITIONAL CONTEXT:
{context}
"""


class CompanyEnricher:
    def __init__(self, router: AIRouter) -> None:
        self.router = router

    async def enrich(
        self,
        name: str,
        domain: str,
        context: str = "",
    ) -> CompanyProfile:
        key = f"company:{hashlib.sha256(f'{domain}{name}'.encode()).hexdigest()}"
        raw = await self.router.route(
            prompt=_PROMPT.format(name=name, domain=domain, context=context[:1500]),
            complexity=TaskComplexity.CLASSIFICATION,
            cache_key=key,
            system=_SYSTEM,
        )
        return self._parse(raw, name, domain)

    def _parse(self, raw: str, name: str, domain: str) -> CompanyProfile:
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
            data = json.loads(clean)
            return CompanyProfile(
                name=name,
                domain=domain,
                stage=data.get("stage", "unknown"),
                headcount_range=data.get("headcount_range", "unknown"),
                tech_stack=data.get("tech_stack", []),
                engineering_culture=data.get("engineering_culture", {}),
                hiring_urgency=int(data.get("hiring_urgency", 5)),
                recent_signals=data.get("recent_signals", []),
            )
        except Exception as e:
            logger.warning("Company enrichment parse failed: %s", e)
            return CompanyProfile(name=name, domain=domain)