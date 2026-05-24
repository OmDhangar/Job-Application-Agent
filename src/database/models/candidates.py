"""
src/database/models/candidates.py

ORM models for candidates, applications, and outreach.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, DateTime, Float, ForeignKey,
    Integer, String, Text, ARRAY, func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column

from src.database.connection import Base


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    email: Mapped[str] = mapped_column(String, unique=True, nullable=False)
    phone: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String)
    github_url: Mapped[Optional[str]] = mapped_column(String)
    portfolio_url: Mapped[Optional[str]] = mapped_column(String)
    resume_raw: Mapped[Optional[str]] = mapped_column(Text)
    resume_structured: Mapped[Optional[dict]] = mapped_column(JSONB)
    identity_profile: Mapped[Optional[dict]] = mapped_column(JSONB)
    skills: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    years_experience: Mapped[Optional[float]] = mapped_column(Float)
    target_roles: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    applications: Mapped[list["Application"]] = relationship("Application", back_populates="candidate")


class Application(Base):
    __tablename__ = "applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    job_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("jobs.id"))

    # Status lifecycle: discovered → applied → replied → interviewing → offered → rejected | ghosted
    status: Mapped[str] = mapped_column(String, default="discovered")

    tailored_resume: Mapped[Optional[str]] = mapped_column(Text)
    resume_version: Mapped[int] = mapped_column(Integer, default=1)

    # Scores (0-100)
    ats_score: Mapped[Optional[float]] = mapped_column(Float)
    authenticity_score: Mapped[Optional[float]] = mapped_column(Float)
    recruiter_score: Mapped[Optional[float]] = mapped_column(Float)
    interview_probability: Mapped[Optional[float]] = mapped_column(Float)

    applied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    last_activity: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    notes: Mapped[Optional[str]] = mapped_column(Text)
    metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    candidate: Mapped["Candidate"] = relationship("Candidate", back_populates="applications")
    job: Mapped["Job"] = relationship("Job", back_populates="applications")  # type: ignore[name-defined]
    outreach_records: Mapped[list["Outreach"]] = relationship("Outreach", back_populates="application")


class Outreach(Base):
    __tablename__ = "outreach"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    application_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("applications.id"))
    candidate_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("candidates.id"))
    recipient_name: Mapped[Optional[str]] = mapped_column(String)
    recipient_email: Mapped[Optional[str]] = mapped_column(String)
    recipient_role: Mapped[Optional[str]] = mapped_column(String)
    channel: Mapped[str] = mapped_column(String, default="email")  # email | linkedin
    subject: Mapped[Optional[str]] = mapped_column(String)
    body: Mapped[Optional[str]] = mapped_column(Text)
    personalization_signals: Mapped[Optional[dict]] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String, default="drafted")  # drafted | sent | opened | replied
    sent_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    opened_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    replied_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    application: Mapped[Optional["Application"]] = relationship("Application", back_populates="outreach_records")
