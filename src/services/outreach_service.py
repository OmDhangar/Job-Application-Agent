# ─── Outreach Service ─────────────────────────────────────────────────────────
from __future__ import annotations

import logging
from uuid import UUID

import numpy as np

logger = logging.getLogger(__name__)

class OutreachService:
    def __init__(self, personalizer, contact_finder, outreach_repo) -> None:
        self.personalizer = personalizer
        self.contacts = contact_finder
        self.repo = outreach_repo

    async def generate_for_application(
        self,
        application_id: UUID,
        candidate_summary: str,
        company_name: str,
        company_domain: str,
        job_title: str,
        tech_stack: list[str],
        recent_news: str | None = None,
    ) -> dict:
        from src.outreach.personalizer import PersonalizationSignals

        # Find contacts
        contacts = await self.contacts.find(company_domain, company_name)
        primary = contacts[0] if contacts else {}

        signals = PersonalizationSignals(
            company_name=company_name,
            job_title=job_title,
            tech_stack=tech_stack,
            recent_news=recent_news,
            candidate_connection=f"Relevant background for {job_title} role",
            recipient_name=primary.get("name"),
            recipient_role=primary.get("role"),
        )

        draft = await self.personalizer.generate(signals, candidate_summary)

        # Persist draft
        record = await self.repo.create(
            application_id=application_id,
            recipient_email=primary.get("email"),
            recipient_name=primary.get("name"),
            subject=draft.subject,
            body=draft.body,
            personalization_signals=signals.__dict__,
        )
        return {
            "id": str(record.id),
            "subject": draft.subject,
            "body": draft.body,
            "word_count": draft.word_count,
            "recipient": primary,
        }