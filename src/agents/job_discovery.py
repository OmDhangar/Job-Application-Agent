"""
src/agents/job_discovery.py

Job Discovery Agent — CrewAI task definitions for job sourcing.
This agent is responsible for finding, filtering, and scoring job opportunities.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_job_discovery_agent


def create_job_discovery_task(
    agent: Agent,
    role: str,
    skills: list[str],
    location: str = "Remote",
    seniority: str = "mid",
) -> Task:
    """
    Task: discover relevant job postings for a candidate profile.

    The agent scrapes + searches multiple job boards and returns
    a structured list of opportunities ranked by relevance.
    """
    return Task(
        description=(
            f"Find the top 20 most relevant job postings for a {seniority}-level "
            f"{role} engineer with these skills: {', '.join(skills[:8])}.\n\n"
            f"Search across LinkedIn, YC Jobs, Wellfound, Greenhouse, Lever, "
            f"and HackerNews 'Who is Hiring' threads.\n\n"
            f"Location preference: {location}\n\n"
            "For each job, capture:\n"
            "- Company name and URL\n"
            "- Job title and seniority level\n"
            "- Required tech stack\n"
            "- Remote/hybrid/onsite status\n"
            "- Posting date (favour recent < 2 weeks)\n"
            "- Direct application URL\n\n"
            "Discard postings that are clearly mismatched (wrong domain, "
            "extremely over-qualified, or expired)."
        ),
        expected_output=(
            "JSON array of up to 20 job objects, each with: "
            "title, company, url, tech_stack (list), seniority, remote_type, "
            "posted_date, relevance_note (1 sentence why it fits)."
        ),
        agent=agent,
    )


def create_job_scoring_task(agent: Agent, jobs_raw: str, candidate_summary: str) -> Task:
    """
    Task: score and rank already-discovered jobs against a candidate profile.
    """
    return Task(
        description=(
            f"Given this list of job postings:\n{jobs_raw}\n\n"
            f"And this candidate profile:\n{candidate_summary}\n\n"
            "Score each job on a 0-10 scale based on:\n"
            "- Skill alignment (how well the candidate's skills match requirements)\n"
            "- Role fit (does the seniority and role type match?)\n"
            "- Company quality (stage, engineering reputation)\n"
            "- Application probability (realistic chance of getting an interview)\n\n"
            "Return only the top 5 with scores and brief justifications."
        ),
        expected_output=(
            "JSON array of top 5 jobs, each with: "
            "title, company, url, overall_score (0-10), skill_score, fit_score, "
            "application_probability (0-100%), justification (2 sentences)."
        ),
        agent=agent,
    )