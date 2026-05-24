"""
src/enrichment/jd_analyzer.py

Job description intent analysis.
Uses local LLM + Redis cache — typically zero Gemini cost for this step.
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from src.ai.router import AIRouter, TaskComplexity

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a technical recruiter analyzing a job description. "
    "Return ONLY valid JSON. No markdown fences. No preamble."
)
_PROMPT = """
Extract from this job description and return JSON with exactly these keys:
- role_type: one of backend|frontend|fullstack|ml|data|devops|research|mobile|other
- seniority: one of intern|junior|mid|senior|staff|principal
- required_skills: array of strings (explicitly required technical skills)
- preferred_skills: array of strings (nice-to-have)
- tech_stack: array of strings (all technologies mentioned)
- ats_keywords: array of exact phrases an ATS would match
- hiring_intent: string — 1 sentence: what problem does this role solve?
- culture_signals: array of strings — values or work style clues

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
        key = f"jd:{hashlib.sha256(jd_text.encode()).hexdigest()}"
        raw = await self.router.route(
            prompt=_PROMPT.format(jd=jd_text[:4000]),
            complexity=TaskComplexity.EXTRACTION,
            cache_key=key,
            system=_SYSTEM,
        )
        return self._parse(raw)

    def _parse(self, raw: str) -> JDAnalysis:
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
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
            logger.warning("JD parse failed: %s", e)
            return JDAnalysis()