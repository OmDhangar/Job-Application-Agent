"""
src/workflows/intelligence.py  —  Company intelligence gathering crew (CrewAI).
"""
from __future__ import annotations
from crewai import Crew, Task
from src.agents.base import build_company_research_agent, build_job_discovery_agent


def build_intelligence_crew(company_name: str, company_url: str) -> Crew:
    """
    Two-agent crew for deep company profiling.
    Used before tailoring to give the resume strategy full context.
    """
    discovery_agent = build_job_discovery_agent()
    research_agent = build_company_research_agent()

    discover_task = Task(
        description=(
            f"Find all open roles at {company_name} ({company_url}). "
            "List titles, seniority levels, and any patterns in what they're hiring for. "
            "Identify which engineering teams appear to be growing fastest."
        ),
        expected_output="List of open roles with seniority and team context.",
        agent=discovery_agent,
    )

    research_task = Task(
        description=(
            f"Build a complete intelligence profile for {company_name}. Include: "
            "funding stage, headcount estimate, tech stack (inferred from job posts + blog), "
            "engineering culture (remote policy, tech debt attitude, shipping cadence), "
            "recent product launches or funding events, and hiring urgency indicators."
        ),
        expected_output=(
            "Structured JSON: stage, tech_stack, culture, recent_signals, hiring_urgency (0-10), "
            "eng_blog_url, key_contacts."
        ),
        agent=research_agent,
        context=[discover_task],
    )

    return Crew(
        agents=[discovery_agent, research_agent],
        tasks=[discover_task, research_task],
        verbose=False,
    )