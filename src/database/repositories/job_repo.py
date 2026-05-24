"""
src/database/repositories/job_repo.py  —  Job data access layer.
"""
from __future__ import annotations

import logging
from uuid import UUID

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from src.adapters.base import CanonicalJob

logger = logging.getLogger(__name__)


class JobRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def upsert(self, job: CanonicalJob):
        from src.database.models.jobs import Job, Company
        # Upsert company
        company = await self._get_or_create_company(job.company_name, job.company_domain)

        # Check existing by fingerprint
        existing = await self.db.execute(
            select(Job).where(Job.fingerprint == job.fingerprint)
        )
        record = existing.scalar_one_or_none()
        if record:
            return record

        record = Job(
            company_id=company.id if company else None,
            title=job.title,
            source=job.source,
            source_id=job.source_id,
            source_url=job.source_url,
            location=job.location,
            remote_type=job.remote_type,
            employment_type=job.employment_type,
            seniority=job.seniority,
            description=job.description,
            tech_stack=job.tech_stack,
            requirements=job.requirements,
            salary_min=job.salary_min,
            salary_max=job.salary_max,
            salary_currency=job.salary_currency,
            posted_at=job.posted_at,
            fingerprint=job.fingerprint,
            raw_metadata=job.raw_metadata,
        )
        self.db.add(record)
        await self.db.flush()
        return record

    async def get(self, job_id: UUID):
        from src.database.models.jobs import Job
        result = await self.db.execute(select(Job).where(Job.id == job_id))
        return result.scalar_one_or_none()

    async def mark_enriched(self, job_id: UUID, score: float) -> None:
        from src.database.models.jobs import Job
        await self.db.execute(
            update(Job)
            .where(Job.id == job_id)
            .values(enriched=True, opportunity_score=score)
        )

    async def _get_or_create_company(self, name: str, domain: str | None):
        from src.database.models.jobs import Company
        if domain:
            result = await self.db.execute(
                select(Company).where(Company.domain == domain)
            )
            existing = result.scalar_one_or_none()
            if existing:
                return existing
        company = Company(name=name, domain=domain)
        self.db.add(company)
        await self.db.flush()
        return company


class ApplicationRepository:
    def __init__(self, session: AsyncSession) -> None:
        self.db = session

    async def create(self, candidate_id: UUID, job_id: UUID, notes: str | None = None):
        from src.database.models.candidates import Application
        app = Application(candidate_id=candidate_id, job_id=job_id, notes=notes)
        self.db.add(app)
        await self.db.flush()
        return app

    async def get(self, app_id: UUID):
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).where(Application.id == app_id)
        )
        return result.scalar_one_or_none()

    async def update(self, app_id: UUID, **kwargs):
        from src.database.models.candidates import Application
        await self.db.execute(
            update(Application).where(Application.id == app_id).values(**kwargs)
        )
        return await self.get(app_id)

    async def list_by_candidate(self, candidate_id: UUID) -> list:
        from src.database.models.candidates import Application
        result = await self.db.execute(
            select(Application).where(Application.candidate_id == candidate_id)
        )
        return result.scalars().all()

    async def stale(self, days: int = 7) -> list[dict]:
        from sqlalchemy import text
        result = await self.db.execute(
            text("""
                SELECT id::text, status, applied_at
                FROM applications
                WHERE status IN ('applied','interviewing')
                  AND last_activity < NOW() - INTERVAL ':days days'
            """),
            {"days": days},
        )
        return [dict(r._mapping) for r in result]

    async def list_with_jobs(self, candidate_id: UUID) -> list:
        from src.database.models.candidates import Application
        from src.database.models.jobs import Job
        from sqlalchemy.orm import joinedload
        result = await self.db.execute(
            select(Application)
            .options(joinedload(Application.job))
            .where(Application.candidate_id == candidate_id)
        )
        apps = result.scalars().all()
        return [(a, a.job) for a in apps if a.job]