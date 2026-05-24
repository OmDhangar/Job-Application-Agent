"""
src/matching/ranker.py  —  Multi-signal job ranker.
"""
from __future__ import annotations

from dataclasses import dataclass
import numpy as np


@dataclass
class JobScore:
    job_id: str
    semantic_score: float
    skill_overlap: float
    seniority_match: float
    recency_bonus: float
    composite: float


class JobRanker:
    """
    Combines four signals into a composite score.
    All arithmetic — zero LLM cost.

    Weights are tunable; defaults favour semantic similarity
    and skill overlap over recency.
    """
    WEIGHTS = {
        "semantic":  0.45,
        "skill":     0.30,
        "seniority": 0.15,
        "recency":   0.10,
    }

    def __init__(self, embedder) -> None:
        self.embedder = embedder

    def rank(
        self,
        candidate_vec: np.ndarray,
        candidate_skills: set[str],
        candidate_seniority: str,
        jobs: list[dict],
    ) -> list[JobScore]:
        scores: list[JobScore] = []
        for job in jobs:
            raw_vec = job.get("embedding")
            if raw_vec is None:
                continue
            if isinstance(raw_vec, str):
                import json
                raw_vec = json.loads(raw_vec)
            jvec = np.array(raw_vec, dtype=np.float32)

            # ── Semantic similarity (cosine; vecs are L2-normalised) ──
            semantic = float(np.dot(candidate_vec, jvec))

            # ── Jaccard skill overlap ──────────────────────────────────
            jskills  = {s.lower() for s in (job.get("tech_stack") or [])}
            cskills  = {s.lower() for s in candidate_skills}
            union    = cskills | jskills
            overlap  = len(cskills & jskills) / len(union) if union else 0.0

            # ── Seniority alignment ───────────────────────────────────
            seniority = 1.0 if job.get("seniority") == candidate_seniority else 0.3

            # ── Recency (decay over 60 days) ──────────────────────────
            days = float(job.get("days_since_posted", 30))
            recency = max(0.0, 1.0 - days / 60.0)

            w = self.WEIGHTS
            composite = (
                w["semantic"]  * semantic
                + w["skill"]   * overlap
                + w["seniority"] * seniority
                + w["recency"] * recency
            )
            scores.append(
                JobScore(
                    job_id=job["id"],
                    semantic_score=round(semantic, 4),
                    skill_overlap=round(overlap, 4),
                    seniority_match=seniority,
                    recency_bonus=round(recency, 4),
                    composite=round(composite, 4),
                )
            )
        return sorted(scores, key=lambda s: s.composite, reverse=True)