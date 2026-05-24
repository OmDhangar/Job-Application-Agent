"""
src/agents/cold_email.py

Cold Email Agent — generates deeply personalised outreach.
Not templates. Never sounds like a template.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_cold_email_agent


def create_cold_email_task(
    agent: Agent,
    company_intel_json: str,
    candidate_summary: str,
    job_title: str,
    recipient_name: str | None = None,
) -> Task:
    recipient = recipient_name or "the hiring team"
    return Task(
        description=(
            f"Write a cold outreach email from this candidate to {recipient} at the company below.\n\n"
            f"COMPANY INTELLIGENCE:\n{company_intel_json}\n\n"
            f"CANDIDATE SUMMARY:\n{candidate_summary}\n\n"
            f"TARGET ROLE: {job_title}\n\n"
            "RULES YOU CANNOT BREAK:\n"
            "- Do NOT open with 'I hope this email finds you well'\n"
            "- Do NOT say 'I came across your job posting'\n"
            "- Do NOT use 'I would love to' or 'I am passionate about'\n"
            "- MUST reference one specific and real detail about the company\n"
            "  (from the intel above — a product, a blog post, a funding round, a tech choice)\n"
            "- Body MAXIMUM 120 words. Subject line MAXIMUM 8 words.\n"
            "- End with ONE clear ask (e.g., '15-minute call?')\n"
            "- Sound like a curious, confident professional — not a desperate applicant\n\n"
            "FORMAT:\n"
            "SUBJECT: <subject line>\n"
            "---\n"
            "<email body>\n\n"
            "Write 2 variants: one more direct, one more narrative."
        ),
        expected_output=(
            "Two email variants.\n"
            "VARIANT 1 — DIRECT:\n"
            "SUBJECT: ...\n---\n...\n\n"
            "VARIANT 2 — NARRATIVE:\n"
            "SUBJECT: ...\n---\n..."
        ),
        agent=agent,
    )


def create_followup_email_task(
    agent: Agent,
    original_email: str,
    days_since_send: int,
    company_name: str,
) -> Task:
    return Task(
        description=(
            f"Write a follow-up email. The candidate sent the email below "
            f"{days_since_send} days ago and has not received a reply.\n\n"
            f"ORIGINAL EMAIL:\n{original_email}\n\n"
            f"COMPANY: {company_name}\n\n"
            "Rules:\n"
            "- DO NOT be passive-aggressive\n"
            "- DO NOT guilt-trip ('I haven't heard back...')\n"
            "- Add a new piece of value or a brief new angle\n"
            "- Even shorter than the original — 60 words max\n"
            "- One clear, easy ask"
        ),
        expected_output="SUBJECT: ...\n---\n<follow-up email body, 60 words max>",
        agent=agent,
    )