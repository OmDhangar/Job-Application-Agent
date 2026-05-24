"""
src/enrichment/candidate_profiler.py

Candidate Profiler — builds and caches a full structured candidate profile
from resume text using local LLM. Zero Gemini cost.

This is the canonical source of truth for:
- identity extraction
- skill normalisation
- career trajectory analysis
- voice fingerprinting
"""
from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field, asdict

from src.ai.router import AIRouter, TaskComplexity

logger = logging.getLogger(__name__)

_SYSTEM = (
    "You are a senior career coach. Analyse resumes and return structured JSON. "
    "Return ONLY valid JSON — no markdown fences, no preamble, no explanation."
)

_PROFILE_PROMPT = """
Build a complete candidate profile from this resume.

Return JSON with EXACTLY these keys:
{{
  "name": "string",
  "email": "string or null",
  "location": "string or null",
  "years_experience": float,
  "strongest_domain": "backend|frontend|fullstack|ml|data|devops|research|mobile|other",
  "core_skills": ["list of verified technical skills"],
  "soft_skills": ["list of verified soft skills"],
  "companies_worked": ["exact company names"],
  "titles_held": ["exact job titles"],
  "education": [
    {{"degree": "...", "institution": "...", "year": "...", "gpa": "... or null"}}
  ],
  "project_titles": ["exact project names"],
  "achievements": ["quantified achievements with numbers"],
  "publications": ["publication titles or null"],
  "certifications": ["certifications or null"],
  "voice_markers": ["3 phrases that characterise their writing style"],
  "career_trajectory": "ascending|lateral|early",
  "genuine_differentiators": ["2-3 honest differentiators"],
  "estimated_seniority": "intern|junior|mid|senior|staff|principal"
}}

RESUME:
{resume}
"""


@dataclass
class CandidateProfile:
    name: str = ""
    email: str | None = None
    location: str | None = None
    years_experience: float = 0.0
    strongest_domain: str = "fullstack"
    core_skills: list[str] = field(default_factory=list)
    soft_skills: list[str] = field(default_factory=list)
    companies_worked: list[str] = field(default_factory=list)
    titles_held: list[str] = field(default_factory=list)
    education: list[dict] = field(default_factory=list)
    project_titles: list[str] = field(default_factory=list)
    achievements: list[str] = field(default_factory=list)
    publications: list[str] = field(default_factory=list)
    certifications: list[str] = field(default_factory=list)
    voice_markers: list[str] = field(default_factory=list)
    career_trajectory: str = "early"
    genuine_differentiators: list[str] = field(default_factory=list)
    estimated_seniority: str = "mid"

    def to_dict(self) -> dict:
        return asdict(self)

    def to_identity_summary(self) -> str:
        """Human-readable summary for prompts."""
        return (
            f"{self.name} | {self.estimated_seniority} {self.strongest_domain} engineer | "
            f"{self.years_experience:.1f}yr exp | "
            f"Skills: {', '.join(self.core_skills[:8])} | "
            f"Companies: {', '.join(self.companies_worked)} | "
            f"Projects: {', '.join(self.project_titles[:4])}"
        )


class CandidateProfiler:
    def __init__(self, router: AIRouter) -> None:
        self.router = router

    async def profile(self, resume_text: str) -> CandidateProfile:
        """
        Extract full structured profile from resume text.
        Cached by resume hash — runs once per unique resume.
        """
        cache_key = f"profile:{hashlib.sha256(resume_text[:1000].encode()).hexdigest()}"
        raw = await self.router.route(
            prompt=_PROFILE_PROMPT.format(resume=resume_text[:4000]),
            complexity=TaskComplexity.EXTRACTION,
            cache_key=cache_key,
            system=_SYSTEM,
        )
        return self._parse(raw)

    def _parse(self, raw: str) -> CandidateProfile:
        try:
            clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
            data = json.loads(clean)
            return CandidateProfile(
                name=data.get("name", ""),
                email=data.get("email"),
                location=data.get("location"),
                years_experience=float(data.get("years_experience", 0)),
                strongest_domain=data.get("strongest_domain", "fullstack"),
                core_skills=_safe_list(data.get("core_skills")),
                soft_skills=_safe_list(data.get("soft_skills")),
                companies_worked=_safe_list(data.get("companies_worked")),
                titles_held=_safe_list(data.get("titles_held")),
                education=data.get("education") or [],
                project_titles=_safe_list(data.get("project_titles")),
                achievements=_safe_list(data.get("achievements")),
                publications=_safe_list(data.get("publications")),
                certifications=_safe_list(data.get("certifications")),
                voice_markers=_safe_list(data.get("voice_markers")),
                career_trajectory=data.get("career_trajectory", "early"),
                genuine_differentiators=_safe_list(data.get("genuine_differentiators")),
                estimated_seniority=data.get("estimated_seniority", "mid"),
            )
        except Exception as e:
            logger.warning("CandidateProfiler parse failed: %s", e)
            return CandidateProfile()


def _safe_list(val) -> list:
    if val is None:
        return []
    if isinstance(val, list):
        return [str(v) for v in val if v]
    return []