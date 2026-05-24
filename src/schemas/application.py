"""
src/schemas/application.py  —  Application-specific Pydantic schemas.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field


# ─── Application Schemas ──────────────────────────────────────────────────────

class ApplicationCreate(BaseModel):
    candidate_id: UUID
    job_id: UUID
    notes: Optional[str] = None


class ApplicationRead(BaseModel):
    id: UUID
    candidate_id: UUID
    job_id: UUID
    status: str
    tailored_resume: Optional[str] = None
    resume_version: int
    ats_score: Optional[float] = None
    authenticity_score: Optional[float] = None
    recruiter_score: Optional[float] = None
    interview_probability: Optional[float] = None
    applied_at: Optional[datetime] = None
    last_activity: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


class ApplicationWithScores(ApplicationRead):
    job_title: Optional[str] = None
    company_name: Optional[str] = None
    source: Optional[str] = None


class FunnelAnalytics(BaseModel):
    total_applications: int
    by_status: dict[str, int]
    reply_rate: float
    interview_rate: float
    offer_rate: float


