"""
src/tracking/tracker.py  —  Application lifecycle management.
src/tracking/analytics.py — Outcome analytics and feedback signals.
"""
from __future__ import annotations

import logging
from uuid import UUID
logger = logging.getLogger(__name__)


# ─── Analytics ────────────────────────────────────────────────────────────────

class ApplicationAnalytics:
    def __init__(self, app_repo) -> None:
        self.repo = app_repo

    async def funnel(self, candidate_id: UUID) -> dict:
        apps = await self.repo.list_by_candidate(candidate_id)
        counts: dict[str, int] = {}
        for a in apps:
            counts[a.status] = counts.get(a.status, 0) + 1

        total = len(apps)
        replied = counts.get("replied", 0) + counts.get("interviewing", 0) + counts.get("offered", 0)
        interviewed = counts.get("interviewing", 0) + counts.get("offered", 0)

        return {
            "total_applications": total,
            "by_status": counts,
            "reply_rate": round(replied / total * 100, 1) if total else 0,
            "interview_rate": round(interviewed / total * 100, 1) if total else 0,
            "offer_rate": round(counts.get("offered", 0) / total * 100, 1) if total else 0,
        }

    async def top_performing_sources(self, candidate_id: UUID) -> list[dict]:
        """Which job sources produced replies / interviews?"""
        apps = await self.repo.list_with_jobs(candidate_id)
        source_stats: dict[str, dict] = {}
        for a, job in apps:
            src = job.source
            if src not in source_stats:
                source_stats[src] = {"total": 0, "positive": 0}
            source_stats[src]["total"] += 1
            if a.status in ("replied", "interviewing", "offered"):
                source_stats[src]["positive"] += 1
        return [
            {
                "source": src,
                "total": v["total"],
                "positive": v["positive"],
                "conversion_rate": round(v["positive"] / v["total"] * 100, 1),
            }
            for src, v in sorted(
                source_stats.items(),
                key=lambda x: x[1]["positive"] / max(x[1]["total"], 1),
                reverse=True,
            )
        ]