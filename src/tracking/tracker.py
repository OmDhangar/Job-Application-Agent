from __future__ import annotations

import logging
from datetime import datetime, timezone
from uuid import UUID

logger = logging.getLogger(__name__)

VALID_TRANSITIONS: dict[str, list[str]] = {
    "discovered":   ["applied", "rejected"],
    "applied":      ["replied", "rejected", "ghosted"],
    "replied":      ["interviewing", "rejected"],
    "interviewing": ["offered", "rejected", "ghosted"],
    "offered":      ["rejected"],
    "rejected":     [],
    "ghosted":      ["replied"],   # they might reply late
}


class ApplicationTracker:
    def __init__(self, app_repo) -> None:
        self.repo = app_repo

    async def transition(
        self,
        application_id: UUID,
        new_status: str,
        notes: str | None = None,
    ) -> dict:
        app = await self.repo.get(application_id)
        if not app:
            raise ValueError(f"Application {application_id} not found")

        current = app.status
        allowed = VALID_TRANSITIONS.get(current, [])
        if new_status not in allowed:
            raise ValueError(
                f"Invalid transition: {current} → {new_status}. "
                f"Allowed: {allowed}"
            )

        updates = {
            "status": new_status,
            "last_activity": datetime.now(timezone.utc),
        }
        if notes:
            updates["notes"] = notes
        if new_status == "applied":
            updates["applied_at"] = datetime.now(timezone.utc)

        updated = await self.repo.update(application_id, **updates)
        logger.info("Application %s: %s → %s", application_id, current, new_status)
        return {"id": str(application_id), "old_status": current, "new_status": new_status}

    async def flag_for_followup(self, days_since_apply: int = 7) -> list[dict]:
        """Return applications that haven't moved in N days."""
        return await self.repo.stale(days=days_since_apply)