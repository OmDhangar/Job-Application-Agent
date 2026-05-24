"""
src/agents/company_research.py

Company Research Agent — deep-dives into a target company before tailoring.
Feeds signals into the cold email and resume strategy pipelines.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_company_research_agent


def create_company_research_task(agent: Agent, company_name: str, company_url: str) -> Task:
    return Task(
        description=(
            f"Research '{company_name}' ({company_url}) thoroughly.\n\n"
            "Gather:\n"
            "1. FUNDING STAGE — seed / Series A / B / growth / public, "
            "and approximate last round size if public\n"
            "2. HEADCOUNT — estimate from LinkedIn or news\n"
            "3. TECH STACK — infer from job postings, GitHub, StackShare, or engineering blog\n"
            "4. ENGINEERING CULTURE — remote policy, shipping cadence, on-call, tech debt attitude\n"
            "5. RECENT SIGNALS — product launches, funding, acquisitions, layoffs (last 6 months)\n"
            "6. HIRING URGENCY — how many open engineering roles? Growing fast?\n"
            "7. KEY CONTACTS — names + LinkedIn URLs of: CTO, VP Eng, or hiring managers "
            "(do NOT invent, only include what you find)\n"
            "8. ENGINEERING BLOG — URL if it exists, and 1-2 notable recent posts\n\n"
            "Be factual. If you can't find something, say 'not found' — do not guess."
        ),
        expected_output=(
            "Structured JSON:\n"
            "{\n"
            '  "stage": "series_b",\n'
            '  "headcount_estimate": "200-500",\n'
            '  "tech_stack": ["Python", "Kubernetes", "Postgres"],\n'
            '  "engineering_culture": {"remote": true, "eng_blog": "https://...", "shipping_cadence": "weekly"},\n'
            '  "recent_signals": ["Raised $40M Series B Jan 2025", "Launched X product"],\n'
            '  "hiring_urgency": 8,\n'
            '  "key_contacts": [{"name": "...", "role": "VP Engineering", "linkedin": "..."}],\n'
            '  "eng_blog_reference": "Post title + URL"\n'
            "}"
        ),
        agent=agent,
    )


def create_tech_stack_inference_task(
    agent: Agent, company_name: str, job_description: str
) -> Task:
    return Task(
        description=(
            f"Infer the complete tech stack used by '{company_name}' "
            f"based on this job description:\n\n{job_description}\n\n"
            "Also search their GitHub org, engineering blog, and StackShare profile "
            "if they exist.\n\n"
            "Categorise technologies into:\n"
            "- Languages\n"
            "- Frameworks\n"
            "- Databases\n"
            "- Infrastructure / DevOps\n"
            "- AI/ML tools (if any)\n"
            "- Monitoring / Observability"
        ),
        expected_output=(
            "JSON with categories: languages, frameworks, databases, "
            "infrastructure, ai_ml, monitoring. Each is a list of strings."
        ),
        agent=agent,
    )