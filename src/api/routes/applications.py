"""
src/api/routes/applications.py
"""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import get_db
from src.schemas.candidate import ApplicationCreate, ApplicationStatusUpdate

router = APIRouter()


@router.post("/", status_code=201)
async def create_application(body: ApplicationCreate, db: AsyncSession = Depends(get_db)):
    from src.database.models.candidates import Application
    app = Application(candidate_id=body.candidate_id, job_id=body.job_id, notes=body.notes)
    db.add(app)
    await db.flush()
    return {"id": str(app.id), "status": app.status}


@router.patch("/{app_id}/status")
async def update_status(
    app_id: UUID, body: ApplicationStatusUpdate, db: AsyncSession = Depends(get_db)
):
    from src.database.models.candidates import Application
    from src.tracking.tracker import ApplicationTracker, VALID_TRANSITIONS
    from src.database.repositories.job_repo import ApplicationRepository

    repo = ApplicationRepository(db)
    tracker = ApplicationTracker(repo)
    try:
        return await tracker.transition(app_id, body.status, body.notes)
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.get("/candidate/{candidate_id}")
async def list_by_candidate(candidate_id: UUID, db: AsyncSession = Depends(get_db)):
    from src.database.models.candidates import Application
    result = await db.execute(
        select(Application).where(Application.candidate_id == candidate_id)
    )
    apps = result.scalars().all()
    return [
        {"id": str(a.id), "job_id": str(a.job_id), "status": a.status,
         "ats_score": a.ats_score, "interview_probability": a.interview_probability,
         "applied_at": str(a.applied_at), "created_at": str(a.created_at)}
        for a in apps
    ]


@router.get("/{app_id}/analytics")
async def application_analytics(candidate_id: UUID, db: AsyncSession = Depends(get_db)):
    from src.database.repositories.job_repo import ApplicationRepository
    from src.tracking.analytics import ApplicationAnalytics
    repo = ApplicationRepository(db)
    analytics = ApplicationAnalytics(repo)
    return await analytics.funnel(candidate_id)