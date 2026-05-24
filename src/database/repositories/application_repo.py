"""
src/database/repositories/application_repo.py

Asynchronous data access repository for Application ORM models.
"""
from __future__ import annotations

import logging
from datetime import datetime, timezone, timedelta
from uuid import UUID
from typing import Any, List, Optional

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, **kwargs) -> Any:
        from src.database.models.candidates import Application
        app = Application(**kwargs)
        self.db.add(app)
        await self.db.flush()
        return app

    async def get(self, application_id: UUID) -> Optional[Any]:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).where(Application.id == application_id)
        )
        return result.scalar_one_or_none()

    async def get_by_candidate_and_job(self, candidate_id: UUID, job_id: UUID) -> Optional[Any]:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).where(
                Application.candidate_id == candidate_id,
                Application.job_id == job_id
            )
        )
        return result.scalar_one_or_none()

    async def update(self, application_id: UUID, **kwargs) -> Optional[Any]:
        from src.database.models.candidates import Application
        await self.db.execute(
            update(Application).where(Application.id == application_id).values(**kwargs)
        )
        return await self.get(application_id)

    async def list_all(self, limit: int = 100, offset: int = 0) -> list[Any]:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def list_by_candidate(self, candidate_id: UUID, limit: int = 50) -> list[Any]:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application)
            .where(Application.candidate_id == candidate_id)
            .limit(limit)
        )
        return result.scalars().all()

    async def list_by_status(self, status: str) -> list[Any]:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).where(Application.status == status)
        )
        return result.scalars().all()

    async def stale(self, days: int = 7) -> list[Any]:
        """
        Retrieve active applications that have not had any activity in N days.
        """
        from src.database.models.candidates import Application
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        result = await self.db.execute(
            select(Application).where(
                Application.status.in_(["applied", "replied", "interviewing"]),
                Application.last_activity <= cutoff
            )
        )
        return result.scalars().all()

    async def delete(self, application_id: UUID) -> bool:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            delete(Application).where(Application.id == application_id)
        )
        return result.rowcount > 0
