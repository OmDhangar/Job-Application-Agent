"""
src/matching/semantic_search.py  —  pgvector nearest-neighbour job search.
Delegates heavy lifting to Postgres IVFFlat index — no Python loops needed.
"""
from __future__ import annotations

import logging
from typing import Any

import numpy as np
from sqlalchemy import text
from sqlalchemy.ext.asyncio import async_sessionmaker

logger = logging.getLogger(__name__)


class SemanticJobSearch:
    """
    Finds the k jobs whose embeddings are closest (cosine) to a query vector.
    Requires pgvector extension + IVFFlat index on embeddings.vector.

    SQL hint: CREATE INDEX ... USING ivfflat (vector vector_cosine_ops) WITH (lists=100);
    """

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.sf = session_factory

    async def find_similar(
        self,
        query_vec: np.ndarray,
        top_k: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> list[dict]:
        filters = filters or {}
        remote_only: bool = filters.get("remote_only", False)
        seniority: str | None = filters.get("seniority")

        # pgvector expects "[f1,f2,...,fn]" string literal
        vec_str = "[" + ",".join(f"{v:.6f}" for v in query_vec.tolist()) + "]"

        sql = text("""
            SELECT
                j.id::text                                         AS id,
                j.title,
                j.source,
                j.location,
                j.remote_type,
                j.seniority,
                j.tech_stack,
                j.salary_min,
                j.salary_max,
                j.opportunity_score,
                j.posted_at,
                EXTRACT(EPOCH FROM (NOW() - j.posted_at)) / 86400  AS days_since_posted,
                e.vector                                            AS embedding,
                1 - (e.vector <=> CAST(:vec AS vector))            AS cosine_similarity
            FROM embeddings e
            JOIN jobs j ON j.id = e.entity_id
            WHERE e.entity_type = 'job'
              AND (:remote_only = FALSE OR j.remote_type = 'remote')
              AND (CAST(:seniority AS text) IS NULL   OR j.seniority   = :seniority)
            ORDER BY e.vector <=> CAST(:vec AS vector)
            LIMIT :k
        """)

        async with self.sf() as session:
            result = await session.execute(
                sql,
                {
                    "vec": vec_str,
                    "k": top_k,
                    "remote_only": remote_only,
                    "seniority": seniority,
                },
            )
            rows = result.fetchall()

        return [dict(r._mapping) for r in rows]


class SemanticCandidateSearch:
    """Inverse lookup: given a job embedding, find similar candidate profiles."""

    def __init__(self, session_factory: async_sessionmaker) -> None:
        self.sf = session_factory

    async def find_similar(self, job_vec: np.ndarray, top_k: int = 5) -> list[dict]:
        vec_str = "[" + ",".join(f"{v:.6f}" for v in job_vec.tolist()) + "]"
        sql = text("""
            SELECT
                c.id::text,
                c.name,
                c.email,
                c.skills,
                c.years_experience,
                1 - (e.vector <=> CAST(:vec AS vector)) AS cosine_similarity
            FROM embeddings e
            JOIN candidates c ON c.id = e.entity_id
            WHERE e.entity_type = 'candidate'
            ORDER BY e.vector <=> CAST(:vec AS vector)
            LIMIT :k
        """)
        async with self.sf() as session:
            result = await session.execute(sql, {"vec": vec_str, "k": top_k})
        return [dict(r._mapping) for r in result.fetchall()]