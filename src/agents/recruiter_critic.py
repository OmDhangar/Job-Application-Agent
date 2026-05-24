"""
src/agents/recruiter_critic.py

Recruiter Critic Agent — adversarial review pass after tailoring.
Simulates a skeptical senior technical recruiter doing a 10-second scan.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_recruiter_critic_agent


def create_critique_task(
    agent: Agent, tailored_resume: str, job_description: str
) -> Task:
    return Task(
        description=(
            "You are a senior technical recruiter who reviews 50 resumes per day. "
            "You have exactly 10 seconds for first pass.\n\n"
            "Review this tailored resume for the role below.\n\n"
            f"JOB DESCRIPTION:\n{job_description[:800]}\n\n"
            f"TAILORED RESUME:\n{tailored_resume[:3000]}\n\n"
            "Provide:\n"
            "1. FIRST IMPRESSION SCORE: X/10 (line 1, nothing else on this line)\n"
            "2. ATS ISSUES: List any formatting, keyword, or structure problems that "
            "will cause ATS rejection\n"
            "3. CREDIBILITY SIGNALS: What builds trust? (metrics, company names, titles)\n"
            "4. RED FLAGS: What raises doubt? (vague claims, gaps, inconsistencies)\n"
            "5. SCANNABILITY: Is it easy to skim? What's the reading flow?\n"
            "6. TOP 1 IMPROVEMENT: The single highest-impact change\n\n"
            "Be direct. Do not soften feedback. A bad resume wastes everyone's time."
        ),
        expected_output=(
            "Structured critique starting with 'SCORE: X/10' then:\n"
            "ATS ISSUES: ...\nCREDIBILITY SIGNALS: ...\n"
            "RED FLAGS: ...\nSCANNABILITY: ...\nTOP IMPROVEMENT: ..."
        ),
        agent=agent,
    )


def create_ats_audit_task(agent: Agent, resume_text: str, required_keywords: list[str]) -> Task:
    """Focused ATS compliance check."""
    return Task(
        description=(
            f"ATS AUDIT — check this resume for keyword compliance and format issues.\n\n"
            f"REQUIRED KEYWORDS: {', '.join(required_keywords)}\n\n"
            f"RESUME TEXT:\n{resume_text[:3000]}\n\n"
            "Check:\n"
            "1. Which required keywords are present? (exact match)\n"
            "2. Which are missing entirely?\n"
            "3. Which appear but in a form ATS might not parse "
            "(e.g., inside tables, text boxes, headers)?\n"
            "4. Any formatting elements that block ATS parsing? "
            "(tables, columns, images, headers/footers)\n"
            "5. Overall ATS pass probability (0-100%)"
        ),
        expected_output=(
            "JSON: present_keywords (list), missing_keywords (list), "
            "problematic_keywords (list), format_issues (list), "
            "ats_pass_probability (int)."
        ),
        agent=agent,
    )