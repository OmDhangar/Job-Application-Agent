"""
src/schemas/job.py  —  Pydantic v2 schemas for job-related API I/O.
"""
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, HttpUrl, Field


class JobBase(BaseModel):
    title: str
    source: str
    source_url: Optional[str] = None
    location: Optional[str] = None
    remote_type: Optional[str] = None          # remote | hybrid | onsite
    employment_type: Optional[str] = None      # full_time | contract | internship
    seniority: Optional[str] = None
    description: Optional[str] = None
    tech_stack: list[str] = Field(default_factory=list)
    requirements: list[str] = Field(default_factory=list)
    salary_min: Optional[int] = None
    salary_max: Optional[int] = None
    salary_currency: str = "USD"
    posted_at: Optional[datetime] = None


class JobCreate(JobBase):
    company_name: str
    company_domain: Optional[str] = None
    source_id: Optional[str] = None
    fingerprint: Optional[str] = None
    raw_metadata: dict = Field(default_factory=dict)


class JobRead(JobBase):
    id: UUID
    company_id: Optional[UUID] = None
    opportunity_score: Optional[float] = None
    enriched: bool = False
    created_at: datetime

    model_config = {"from_attributes": True}


class JobSearchRequest(BaseModel):
    query: str
    seniority: Optional[str] = None
    remote_only: bool = False
    top_k: int = Field(10, ge=1, le=50)


class JobSearchResult(BaseModel):
    job: JobRead
    semantic_score: float
    skill_overlap: float
    composite_score: float