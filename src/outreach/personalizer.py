"""
src/outreach/personalizer.py  —  Cold email generation engine.
src/outreach/contact_finder.py — Recruiter email discovery.
"""
from __future__ import annotations

import logging
import re
from dataclasses import dataclass, field

from src.ai.router import AIRouter, TaskComplexity

logger = logging.getLogger(__name__)


# ─── Data classes ─────────────────────────────────────────────────────────────

@dataclass
class PersonalizationSignals:
    company_name: str
    job_title: str
    tech_stack: list[str] = field(default_factory=list)
    recent_news: str | None = None
    eng_blog_reference: str | None = None
    candidate_connection: str = ""   # why THIS candidate for THIS company
    recipient_name: str | None = None
    recipient_role: str | None = None


@dataclass
class EmailDraft:
    subject: str
    body: str
    personalization_signals: dict
    word_count: int = 0

    def __post_init__(self):
        self.word_count = len(self.body.split())


# ─── Personalizer ─────────────────────────────────────────────────────────────

_EMAIL_SYSTEM = """
You write cold outreach emails that do NOT sound like cold emails.
Rules you never break:
- Never open with "I hope this email finds you well"
- Never say "I came across your job posting"
- Reference one SPECIFIC detail about the company
- Maximum 120 words in the body
- Subject line under 60 characters — no clickbait
- Sound human, not polished

Output format (exactly):
SUBJECT: <subject line>
---
<email body>
"""

_EMAIL_PROMPT = """
Write a cold email from this candidate to {recipient} at {company}.

COMPANY SIGNALS:
{signals}

CANDIDATE SUMMARY:
{candidate_summary}

WHY THIS COMPANY (specific connection):
{connection}

The email should feel like it was written by a person who genuinely knows the company,
not a tool that scraped a job board.
"""


class EmailPersonalizer:
    def __init__(self, router: AIRouter) -> None:
        self.router = router

    async def generate(
        self,
        signals: PersonalizationSignals,
        candidate_summary: str,
    ) -> EmailDraft:
        signal_lines = []
        if signals.recent_news:
            signal_lines.append(f"Recent: {signals.recent_news}")
        if signals.eng_blog_reference:
            signal_lines.append(f"Blog/content: {signals.eng_blog_reference}")
        if signals.tech_stack:
            signal_lines.append(f"Tech: {', '.join(signals.tech_stack[:5])}")
        signal_lines.append(f"Role: {signals.job_title}")

        recipient = f"{signals.recipient_name} ({signals.recipient_role})" \
                    if signals.recipient_name else "the hiring team"

        raw = await self.router.route(
            prompt=_EMAIL_PROMPT.format(
                recipient=recipient,
                company=signals.company_name,
                signals="\n".join(signal_lines),
                candidate_summary=candidate_summary[:500],
                connection=signals.candidate_connection[:300],
            ),
            complexity=TaskComplexity.GENERATION,
            cache_key=None,    # emails are never cached
            system=_EMAIL_SYSTEM,
        )

        subject, body = self._parse(raw)
        return EmailDraft(
            subject=subject,
            body=body,
            personalization_signals=signals.__dict__,
        )

    def _parse(self, text: str) -> tuple[str, str]:
        subject = "Following up on an opportunity"
        body = text
        if "SUBJECT:" in text:
            lines = text.split("\n", 1)
            subject = lines[0].replace("SUBJECT:", "").strip()
            body = text.split("---", 1)[-1].strip() if "---" in text else lines[1].strip()
        return subject, body


