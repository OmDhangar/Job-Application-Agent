"""
src/database/repositories/candidate_repo.py  —  Candidate data access layer.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

logger = logging.getLogger(__name__)


class CandidateRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, **kwargs):
        from src.database.models.candidates import Candidate
        cand = Candidate(**kwargs)
        self.db.add(cand)
        await self.db.flush()
        return cand

    async def get(self, candidate_id: UUID):
        from src.database.models.candidates import Candidate
        result = await self.db.execute(
            select(Candidate).where(Candidate.id == candidate_id)
        )
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        from src.database.models.candidates import Candidate
        result = await self.db.execute(
            select(Candidate).where(Candidate.email == email)
        )
        return result.scalar_one_or_none()

    async def update(self, candidate_id: UUID, **kwargs):
        from src.database.models.candidates import Candidate
        await self.db.execute(
            update(Candidate).where(Candidate.id == candidate_id).values(**kwargs)
        )
        return await self.get(candidate_id)

    async def update_resume(
        self,
        candidate_id: UUID,
        resume_raw: str,
        resume_structured: dict | None = None,
        identity_profile: dict | None = None,
        skills: list[str] | None = None,
        years_experience: float | None = None,
    ):
        updates: dict = {"resume_raw": resume_raw}
        if resume_structured:
            updates["resume_structured"] = resume_structured
        if identity_profile:
            updates["identity_profile"] = identity_profile
        if skills:
            updates["skills"] = skills
        if years_experience is not None:
            updates["years_experience"] = years_experience
        return await self.update(candidate_id, **updates)

    async def update_identity_profile(self, candidate_id: UUID, profile_dict: dict):
        """Store the AI-extracted identity profile for fast retrieval."""
        return await self.update(
            candidate_id,
            identity_profile=profile_dict,
            skills=profile_dict.get("core_skills", []),
            years_experience=profile_dict.get("years_experience"),
        )

    async def list_all(self, limit: int = 50, offset: int = 0) -> list:
        from src.database.models.candidates import Candidate
        result = await self.db.execute(
            select(Candidate).offset(offset).limit(limit)
        )
        return result.scalars().all()

    async def delete(self, candidate_id: UUID) -> bool:
        from src.database.models.candidates import Candidate
        from sqlalchemy import delete
        result = await self.db.execute(
            delete(Candidate).where(Candidate.id == candidate_id)
        )
        return result.rowcount > 0