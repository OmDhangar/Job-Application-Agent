"""
src/services/tracking_service.py

Business service for tracking application lifecycles and compiling metrics.
"""
from __future__ import annotations

import logging
from uuid import UUID
from typing import Any, Dict, List

from src.tracking.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


class TrackingService:
    def __init__(self, tracker: ApplicationTracker, app_repo: Any) -> None:
        self.tracker = tracker
        self.repo = app_repo

    async def transition_status(
        self,
        application_id: UUID,
        new_status: str,
        notes: str | None = None,
    ) -> dict[str, str]:
        """
        Transition application lifecycle status and record notes.
        """
        logger.info("Transitioning application %s to status: %s", application_id, new_status)
        return await self.tracker.transition(application_id, new_status, notes=notes)

    async def get_stale_applications(self, days_since_apply: int = 7) -> list[Any]:
        """
        Identify applications that have not been updated for N days.
        """
        return await self.tracker.flag_for_followup(days_since_apply=days_since_apply)

    async def get_funnel_analytics(self) -> dict[str, Any]:
        """
        Calculate job application funnel performance metrics.
        """
        apps = await self.repo.list_all()
        total_discovered = len(apps)
        if total_discovered == 0:
            return {
                "total_discovered": 0,
                "total_applied": 0,
                "total_interviewing": 0,
                "total_offered": 0,
                "apply_rate": 0.0,
                "interview_rate": 0.0,
                "offer_rate": 0.0,
            }

        applied = [a for a in apps if a.status not in ("discovered",)]
        interviewing = [a for a in apps if a.status in ("interviewing", "offered")]
        offered = [a for a in apps if a.status == "offered"]

        total_applied = len(applied)
        total_interviewing = len(interviewing)
        total_offered = len(offered)

        return {
            "total_discovered": total_discovered,
            "total_applied": total_applied,
            "total_interviewing": total_interviewing,
            "total_offered": total_offered,
            "apply_rate": round((total_applied / total_discovered) * 100.0, 2),
            "interview_rate": round((total_interviewing / total_applied) * 100.0, 2) if total_applied > 0 else 0.0,
            "offer_rate": round((total_offered / total_applied) * 100.0, 2) if total_applied > 0 else 0.0,
        }
