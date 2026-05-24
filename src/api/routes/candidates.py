"""
src/api/routes/candidates.py
"""
from __future__ import annotations
from typing import Annotated
from uuid import UUID
from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession
from src.database.connection import get_db
from src.schemas.candidate import CandidateCreate, CandidateRead

router = APIRouter()


@router.post("/", response_model=dict, status_code=201)
async def create_candidate(
    body: CandidateCreate, db: AsyncSession = Depends(get_db)
):
    from src.database.models.candidates import Candidate
    existing = await db.execute(
        __import__("sqlalchemy").select(Candidate).where(Candidate.email == body.email)
    )
    if existing.scalar_one_or_none():
        raise HTTPException(409, f"Candidate with email {body.email} already exists")
    cand = Candidate(**body.model_dump())
    db.add(cand)
    await db.flush()
    return {"id": str(cand.id), "name": cand.name, "email": cand.email}


@router.post("/{candidate_id}/upload-resume")
async def upload_resume(
    candidate_id: UUID,
    resume: Annotated[UploadFile, File()],
    db: AsyncSession = Depends(get_db),
):
    """
    Upload and parse resume for a candidate.
    Extracts plain text + stores it; triggers embedding via queue.
    """
    from sqlalchemy import select, update
    from src.database.models.candidates import Candidate
    from src.tailoring.parser import ResumeParser

    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    cand = result.scalar_one_or_none()
    if not cand:
        raise HTTPException(404, "Candidate not found")

    raw = await resume.read()
    parser = ResumeParser()
    plain_text, _ = parser.extract(raw, resume.filename or "resume.pdf")

    await db.execute(
        update(Candidate).where(Candidate.id == candidate_id).values(resume_raw=plain_text)
    )
    return {"status": "uploaded", "chars_extracted": len(plain_text)}


@router.get("/{candidate_id}", response_model=dict)
async def get_candidate(candidate_id: UUID, db: AsyncSession = Depends(get_db)):
    from sqlalchemy import select
    from src.database.models.candidates import Candidate
    result = await db.execute(select(Candidate).where(Candidate.id == candidate_id))
    cand = result.scalar_one_or_none()
    if not cand:
        raise HTTPException(404, "Candidate not found")
    return {"id": str(cand.id), "name": cand.name, "email": cand.email,
            "skills": cand.skills, "years_experience": cand.years_experience}