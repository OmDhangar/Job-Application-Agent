"""
src/services/job_service.py     —  Job discovery and ranking business logic.
src/services/tailoring_service.py — Tailoring orchestration.
src/services/outreach_service.py  — Outreach generation.
"""
from __future__ import annotations

import logging
from uuid import UUID

import numpy as np

from src.matching.embedder import LocalEmbedder, JobRanker, SemanticJobSearch
from src.schemas.candidate import IdentityProfile
from src.workflows.tailoring import TailoringWorkflow

logger = logging.getLogger(__name__)


# ─── Job Service ─────────────────────────────────────────────────────────────

class JobService:
    def __init__(
        self,
        embedder: LocalEmbedder,
        ranker: JobRanker,
        semantic_search: SemanticJobSearch,
    ) -> None:
        self.embedder = embedder
        self.ranker = ranker
        self.search = semantic_search

    async def find_matching_jobs(
        self,
        candidate_text: str,
        candidate_skills: list[str],
        candidate_seniority: str = "mid",
        top_k: int = 10,
        filters: dict | None = None,
    ) -> list[dict]:
        """
        Full semantic matching pipeline:
        1. Embed candidate profile (local, cached)
        2. pgvector nearest-neighbor retrieval (top_k * 3)
        3. Multi-signal rerank (semantic + skill + seniority + recency)
        4. Return top_k
        """
        vec = self.embedder.embed(candidate_text)

        # Pull 3x more from DB then rerank locally — cheaper than fetching all
        candidates = await self.search.find_similar(vec, top_k=top_k * 3, filters=filters)
        if not candidates:
            return []

        scored = self.ranker.rank(
            candidate_vec=vec,
            candidate_skills=set(candidate_skills),
            candidate_seniority=candidate_seniority,
            jobs=candidates,
        )

        top = scored[:top_k]
        # Merge scores back into job dicts
        score_map = {s.job_id: s for s in top}
        results = []
        for job in candidates:
            if job["id"] in score_map:
                s = score_map[job["id"]]
                results.append({
                    **job,
                    "semantic_score": s.semantic_score,
                    "skill_overlap": s.skill_overlap,
                    "composite_score": s.composite,
                })
        return sorted(results, key=lambda x: x["composite_score"], reverse=True)

