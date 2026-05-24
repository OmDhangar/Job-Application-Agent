"""
src/workflows/outreach.py  —  Cold email generation crew (CrewAI).
"""
from __future__ import annotations
import logging
from crewai import Crew, Task
from src.agents.base import build_cold_email_agent, build_company_research_agent

logger = logging.getLogger(__name__)


def build_outreach_crew(company_name: str, job_title: str, candidate_summary: str) -> Crew:
    """Assembles a two-agent crew: company research → email generation."""
    research_agent = build_company_research_agent()
    email_agent = build_cold_email_agent()

    research_task = Task(
        description=(
            f"Research '{company_name}' thoroughly: recent news, product launches, "
            f"engineering blog posts, tech stack, hiring urgency, and company culture signals. "
            f"Focus on anything that would make an email feel genuinely tailored."
        ),
        expected_output=(
            "Structured JSON with: recent_news (str), tech_stack (list), "
            "eng_blog_references (list), culture_signals (list), hiring_context (str)."
        ),
        agent=research_agent,
    )

    email_task = Task(
        description=(
            f"Using the company research above, write a cold outreach email "
            f"from this candidate to {company_name} for the {job_title} role.\n\n"
            f"CANDIDATE: {candidate_summary}\n\n"
            "Rules: under 120 words, no template openers, reference one specific "
            "company detail, include a single clear call-to-action."
        ),
        expected_output=(
            "SUBJECT: <subject line>\n---\n<email body max 120 words>"
        ),
        agent=email_agent,
        context=[research_task],
    )

    return Crew(
        agents=[research_agent, email_agent],
        tasks=[research_task, email_task],
        verbose=False,
    )