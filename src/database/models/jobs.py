"""
src/database/models/jobs.py

SQLAlchemy 2.0 ORM models for jobs and companies.
pgvector column for semantic search.
"""
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Optional

from sqlalchemy import (
    Boolean, Column, DateTime, Float, ForeignKey,
    Integer, String, Text, ARRAY, SmallInteger,
    func,
)
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship, Mapped, mapped_column
from pgvector.sqlalchemy import Vector

from src.database.connection import Base


class Company(Base):
    __tablename__ = "companies"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name: Mapped[str] = mapped_column(String, nullable=False)
    domain: Mapped[Optional[str]] = mapped_column(String, unique=True)
    linkedin_url: Mapped[Optional[str]] = mapped_column(String)
    hq_location: Mapped[Optional[str]] = mapped_column(String)
    stage: Mapped[Optional[str]] = mapped_column(String)
    headcount: Mapped[Optional[int]] = mapped_column(Integer)
    tech_stack: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    engineering_culture: Mapped[Optional[dict]] = mapped_column(JSONB)
    hiring_urgency: Mapped[Optional[int]] = mapped_column(SmallInteger)
    enriched_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    jobs: Mapped[list["Job"]] = relationship("Job", back_populates="company")


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    company_id: Mapped[Optional[uuid.UUID]] = mapped_column(UUID(as_uuid=True), ForeignKey("companies.id"))
    title: Mapped[str] = mapped_column(String, nullable=False)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String)
    source_url: Mapped[Optional[str]] = mapped_column(String)
    location: Mapped[Optional[str]] = mapped_column(String)
    remote_type: Mapped[Optional[str]] = mapped_column(String)    # remote|hybrid|onsite
    employment_type: Mapped[Optional[str]] = mapped_column(String)
    seniority: Mapped[Optional[str]] = mapped_column(String)
    description: Mapped[Optional[str]] = mapped_column(Text)
    requirements: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    tech_stack: Mapped[Optional[list]] = mapped_column(ARRAY(String))
    salary_min: Mapped[Optional[int]] = mapped_column(Integer)
    salary_max: Mapped[Optional[int]] = mapped_column(Integer)
    salary_currency: Mapped[str] = mapped_column(String, default="USD")
    posted_at: Mapped[Optional[datetime]] = mapped_column(DateTime(timezone=True))
    enriched: Mapped[bool] = mapped_column(Boolean, default=False)
    opportunity_score: Mapped[Optional[float]] = mapped_column(Float)
    fingerprint: Mapped[Optional[str]] = mapped_column(String, unique=True)
    raw_metadata: Mapped[Optional[dict]] = mapped_column(JSONB)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    company: Mapped[Optional[Company]] = relationship("Company", back_populates="jobs")
    applications: Mapped[list["Application"]] = relationship("Application", back_populates="job")


class Embedding(Base):
    __tablename__ = "embeddings"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    entity_type: Mapped[str] = mapped_column(String, nullable=False)  # job|candidate|company
    entity_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    embedding_model: Mapped[str] = mapped_column(String, nullable=False)
    vector = Column(Vector(768))   # bge-base-en-v1.5 dim
    chunk_text: Mapped[Optional[str]] = mapped_column(Text)
    chunk_index: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


class RawPayload(Base):
    __tablename__ = "raw_payloads"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    source: Mapped[str] = mapped_column(String, nullable=False)
    source_id: Mapped[Optional[str]] = mapped_column(String)
    payload: Mapped[dict] = mapped_column(JSONB, nullable=False)
    processed: Mapped[bool] = mapped_column(Boolean, default=False)
    error: Mapped[Optional[str]] = mapped_column(Text)
    scraped_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
