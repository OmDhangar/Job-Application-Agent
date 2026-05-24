"""
src/schemas/candidate.py  —  Candidate, Application, and Outreach schemas.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, EmailStr, Field


# ─── Candidate ────────────────────────────────────────────────────────────────

class CandidateCreate(BaseModel):
    name: str
    email: EmailStr
    phone: Optional[str] = None
    location: Optional[str] = None
    linkedin_url: Optional[str] = None
    github_url: Optional[str] = None
    portfolio_url: Optional[str] = None
    target_roles: list[str] = Field(default_factory=list)


class CandidateRead(CandidateCreate):
    id: UUID
    skills: list[str] = Field(default_factory=list)
    years_experience: Optional[float] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class IdentityProfile(BaseModel):
    """AI-extracted identity — stored in candidates.identity_profile JSONB."""
    name: str
    years_experience: float
    core_skills: list[str]
    companies_worked: list[str]
    degrees: list[str]
    project_titles: list[str]
    voice_markers: list[str]   # characteristic phrases that reflect writing style
    strongest_domain: str      # backend | ml | fullstack | etc.


# ─── Application ──────────────────────────────────────────────────────────────

APPLICATION_STATUSES = [
    "discovered", "applied", "replied",
    "interviewing", "offered", "rejected", "ghosted"
]

class ApplicationCreate(BaseModel):
    candidate_id: UUID
    job_id: UUID
    notes: Optional[str] = None


class ApplicationRead(ApplicationCreate):
    id: UUID
    status: str
    ats_score: Optional[float] = None
    authenticity_score: Optional[float] = None
    recruiter_score: Optional[float] = None
    interview_probability: Optional[float] = None
    resume_version: int
    applied_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


class ApplicationStatusUpdate(BaseModel):
    status: str
    notes: Optional[str] = None


# ─── Outreach ─────────────────────────────────────────────────────────────────

class OutreachCreate(BaseModel):
    application_id: UUID
    candidate_id: UUID
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None
    recipient_role: Optional[str] = None
    channel: str = "email"
    subject: Optional[str] = None
    body: Optional[str] = None
    personalization_signals: dict = Field(default_factory=dict)


class OutreachRead(OutreachCreate):
    id: UUID
    status: str
    sent_at: Optional[datetime] = None
    opened_at: Optional[datetime] = None
    replied_at: Optional[datetime] = None
    created_at: datetime
    model_config = {"from_attributes": True}


# ─── Tailoring ────────────────────────────────────────────────────────────────

class TailoringRequest(BaseModel):
    job_description: str
    candidate_email: Optional[str] = None
    output_format: str = Field("latex", pattern="^(latex|markdown)$")


class ResumeScores(BaseModel):
    ats_score: float
    authenticity_score: float
    recruiter_readability: float
    technical_credibility: float
    interview_probability: float
    composite: float


class TailoringResult(BaseModel):
    tailored_resume: str           # LaTeX or Markdown string
    output_format: str             # "latex" | "markdown"
    has_pdf: bool                  # True when PDF compiled successfully
    strategy: dict
    audit: dict
    critique: str
    scores: ResumeScores
    job_id: str