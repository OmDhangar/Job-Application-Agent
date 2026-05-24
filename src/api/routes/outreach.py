"""
src/api/routes/outreach.py
"""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_email_personalizer, get_contact_finder
from src.database.connection import get_db
from src.outreach.personalizer import PersonalizationSignals

router = APIRouter()


@router.post("/generate")
async def generate_email(
    application_id: UUID,
    company_name: str,
    company_domain: str,
    job_title: str,
    candidate_summary: str,
    tech_stack: list[str] = [],
    recent_news: str | None = None,
    personalizer=Depends(get_email_personalizer),
    contact_finder=Depends(get_contact_finder),
    db: AsyncSession = Depends(get_db),
):
    contacts = await contact_finder.find(company_domain, company_name)
    primary = contacts[0] if contacts else {}

    signals = PersonalizationSignals(
        company_name=company_name,
        job_title=job_title,
        tech_stack=tech_stack,
        recent_news=recent_news,
        candidate_connection=f"Strong background for {job_title} role",
        recipient_name=primary.get("name"),
        recipient_role=primary.get("role"),
    )

    draft = await personalizer.generate(signals, candidate_summary)

    # Save to DB
    from src.database.models.candidates import Outreach
    record = Outreach(
        application_id=application_id,
        candidate_id=UUID("00000000-0000-0000-0000-000000000000"),  # replace with real
        recipient_email=primary.get("email"),
        recipient_name=primary.get("name"),
        subject=draft.subject,
        body=draft.body,
        personalization_signals=signals.__dict__,
    )
    db.add(record)
    await db.flush()

    return {
        "id": str(record.id),
        "subject": draft.subject,
        "body": draft.body,
        "word_count": draft.word_count,
        "suggested_recipient": primary,
    }