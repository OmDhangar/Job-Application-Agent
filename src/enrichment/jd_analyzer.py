"""
src/enrichment/jd_analyzer.py

Job description intent analyzer. Uses local LLM + Redis caching.
Extracts: role type, required skills, ATS keywords, hiring intent signals.
One of the most-called components — caching is critical.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from src.ai.router import AIRouter, TaskComplexity

logger = logging.getLogger(__name__)

SYSTEM = """
You are a technical recruiter analyzing a job description.
Extract structured information and return ONLY valid JSON. No preamble, no markdown fences.
"""

PROMPT_TEMPLATE = """
Analyze this job description and return a JSON object with exactly these keys:
- role_type: string (one of: backend, frontend, fullstack, ml, data, devops, research, mobile, other)
- seniority: string (intern, junior, mid, senior, staff, principal)
- required_skills: array of strings (technical skills explicitly required)
- preferred_skills: array of strings (nice-to-have)
- tech_stack: array of strings (technologies mentioned)
- ats_keywords: array of strings (exact phrases an ATS would match)
- hiring_intent: string (1 sentence: what problem is this role solving?)
- culture_signals: array of strings (values or work style clues)

JOB DESCRIPTION:
{jd}
"""


@dataclass
class JDAnalysis:
    role_type: str = "other"
    seniority: str = "mid"
    required_skills: list[str] = field(default_factory=list)
    preferred_skills: list[str] = field(default_factory=list)
    tech_stack: list[str] = field(default_factory=list)
    ats_keywords: list[str] = field(default_factory=list)
    hiring_intent: str = ""
    culture_signals: list[str] = field(default_factory=list)


class JDAnalyzer:
    def __init__(self, router: AIRouter) -> None:
        self.router = router

    async def analyze(self, jd_text: str) -> JDAnalysis:
        cache_key = f"jd_analysis:{hashlib.sha256(jd_text.encode()).hexdigest()}"
        prompt = PROMPT_TEMPLATE.format(jd=jd_text[:4000])  # truncate very long JDs

        raw = await self.router.route(
            prompt=prompt,
            complexity=TaskComplexity.EXTRACTION,
            cache_key=cache_key,
            system=SYSTEM,
        )

        return self._parse(raw)

    def _parse(self, raw: str) -> JDAnalysis:
        try:
            # Strip markdown fences if local model added them
            clean = re.sub(r"```(?:json)?", "", raw).strip().rstrip("`")
            data = json.loads(clean)
            return JDAnalysis(
                role_type=data.get("role_type", "other"),
                seniority=data.get("seniority", "mid"),
                required_skills=data.get("required_skills", []),
                preferred_skills=data.get("preferred_skills", []),
                tech_stack=data.get("tech_stack", []),
                ats_keywords=data.get("ats_keywords", []),
                hiring_intent=data.get("hiring_intent", ""),
                culture_signals=data.get("culture_signals", []),
            )
        except Exception as e:
            logger.warning("JD parse failed: %s — returning defaults", e)
            return JDAnalysis()
