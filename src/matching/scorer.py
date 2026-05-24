"""
src/matching/scorer.py

Opportunity Scorer — assigns a composite score (0-10) to each job
relative to a candidate profile. Runs entirely locally. Zero LLM cost.

This is distinct from ResumeScorer (which scores tailored resumes).
OpportunityScorer scores raw job opportunities for prioritisation.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class OpportunityScore:
    job_id: str
    semantic_similarity: float    # 0-1  from pgvector cosine
    skill_overlap: float          # 0-1  Jaccard
    seniority_match: float        # 0-1  binary + partial
    recency: float                # 0-1  decay over 60 days
    company_quality: float        # 0-1  stage + hiring urgency heuristic
    salary_fit: float             # 0-1  within candidate range (1.0 if unknown)
    composite: float              # 0-10 weighted final
    tier: str                     # A|B|C — application priority

    def __str__(self) -> str:
        return (
            f"OpportunityScore({self.job_id[:8]}… "
            f"composite={self.composite:.2f} tier={self.tier})"
        )


class OpportunityScorer:
    """
    Weights are tuned to maximise interview conversion based on common
    recruiting patterns. Adjust via environment or config if needed.
    """

    WEIGHTS = {
        "semantic":   0.35,
        "skill":      0.25,
        "seniority":  0.15,
        "recency":    0.10,
        "company":    0.10,
        "salary":     0.05,
    }

    # Tier thresholds (composite 0-10)
    TIER_A = 7.0   # Strong match — tailor and apply immediately
    TIER_B = 5.0   # Decent match — apply if time allows
    # Below TIER_B → Tier C (long shot or poor fit)

    # Company stage quality proxies
    STAGE_QUALITY = {
        "series_b":  0.9,
        "series_a":  0.85,
        "seed":      0.75,
        "growth":    0.80,
        "public":    0.70,
        "unknown":   0.50,
    }

    def score_job(
        self,
        job: dict,
        candidate_skills: list[str],
        candidate_seniority: str,
        candidate_salary_min: int | None = None,
        candidate_salary_max: int | None = None,
    ) -> OpportunityScore:
        # ── Semantic similarity (pre-computed, passed in) ─────────────────────
        semantic = float(job.get("cosine_similarity", 0.0))

        # ── Skill overlap (Jaccard) ───────────────────────────────────────────
        jskills = {s.lower() for s in (job.get("tech_stack") or [])}
        cskills = {s.lower() for s in candidate_skills}
        union = jskills | cskills
        skill = len(jskills & cskills) / len(union) if union else 0.0

        # ── Seniority match ───────────────────────────────────────────────────
        job_seniority = (job.get("seniority") or "").lower()
        seniority = self._seniority_score(candidate_seniority.lower(), job_seniority)

        # ── Recency (linear decay over 60 days) ──────────────────────────────
        days = float(job.get("days_since_posted") or 30)
        recency = max(0.0, 1.0 - days / 60.0)

        # ── Company quality ───────────────────────────────────────────────────
        stage = (job.get("company_stage") or "unknown").lower()
        urgency = float(job.get("hiring_urgency") or 5) / 10.0
        company = (self.STAGE_QUALITY.get(stage, 0.5) * 0.6) + (urgency * 0.4)

        # ── Salary fit ────────────────────────────────────────────────────────
        salary = self._salary_fit(
            job.get("salary_min"), job.get("salary_max"),
            candidate_salary_min, candidate_salary_max,
        )

        # ── Composite (0-1) → scale to 0-10 ──────────────────────────────────
        w = self.WEIGHTS
        raw = (
            w["semantic"]  * semantic
            + w["skill"]   * skill
            + w["seniority"] * seniority
            + w["recency"] * recency
            + w["company"] * company
            + w["salary"]  * salary
        )
        composite = round(raw * 10, 2)

        tier = (
            "A" if composite >= self.TIER_A else
            "B" if composite >= self.TIER_B else
            "C"
        )

        return OpportunityScore(
            job_id=str(job.get("id", "")),
            semantic_similarity=round(semantic, 4),
            skill_overlap=round(skill, 4),
            seniority_match=round(seniority, 4),
            recency=round(recency, 4),
            company_quality=round(company, 4),
            salary_fit=round(salary, 4),
            composite=composite,
            tier=tier,
        )

    def score_batch(
        self,
        jobs: list[dict],
        candidate_skills: list[str],
        candidate_seniority: str,
        candidate_salary_min: int | None = None,
        candidate_salary_max: int | None = None,
    ) -> list[OpportunityScore]:
        scores = [
            self.score_job(j, candidate_skills, candidate_seniority,
                           candidate_salary_min, candidate_salary_max)
            for j in jobs
        ]
        return sorted(scores, key=lambda s: s.composite, reverse=True)

    # ─── Helpers ─────────────────────────────────────────────────────────────

    _SENIORITY_LEVELS = ["intern", "junior", "mid", "senior", "staff", "principal"]

    def _seniority_score(self, candidate: str, job: str) -> float:
        try:
            ci = self._SENIORITY_LEVELS.index(candidate)
            ji = self._SENIORITY_LEVELS.index(job)
            diff = abs(ci - ji)
            if diff == 0:
                return 1.0
            if diff == 1:
                return 0.6   # one level off — stretch/reach
            return 0.2       # two+ levels — poor fit
        except ValueError:
            return 0.5       # unknown seniority — neutral

    def _salary_fit(
        self,
        job_min: int | None, job_max: int | None,
        cand_min: int | None, cand_max: int | None,
    ) -> float:
        if job_min is None and job_max is None:
            return 1.0   # no salary info — don't penalise
        if cand_min is None and cand_max is None:
            return 1.0   # candidate has no preference — fits any

        job_mid = ((job_min or 0) + (job_max or job_min or 0)) / 2
        cand_mid = ((cand_min or 0) + (cand_max or cand_min or 0)) / 2

        if cand_mid == 0 or job_mid == 0:
            return 0.8

        ratio = min(job_mid, cand_mid) / max(job_mid, cand_mid)
        return max(0.0, ratio)