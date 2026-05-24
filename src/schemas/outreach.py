# ─── Outreach Schemas ─────────────────────────────────────────────────────────
from __future__ import annotations
from datetime import datetime
from typing import Optional
from uuid import UUID
from pydantic import BaseModel, Field

class OutreachCreate(BaseModel):
    application_id: Optional[UUID] = None
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


class OutreachGenerateRequest(BaseModel):
    candidate_id: UUID
    application_id: UUID
    company_name: str
    company_domain: str
    job_title: str
    candidate_summary: str
    tech_stack: list[str] = Field(default_factory=list)
    recent_news: Optional[str] = None
    recipient_name: Optional[str] = None
    recipient_email: Optional[str] = None


class OutreachStatusUpdate(BaseModel):
    status: str   # sent | opened | replied