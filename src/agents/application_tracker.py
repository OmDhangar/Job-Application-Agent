"""
src/agents/application_tracker.py  —  Application tracking agent tasks.
src/agents/feedback.py             —  Feedback/learning agent tasks.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_application_tracker_agent, build_feedback_agent


# ─── Application Tracker ──────────────────────────────────────────────────────

def create_followup_schedule_task(
    agent: Agent, applications: list[dict]
) -> Task:
    """Analyse the application pipeline and recommend follow-up actions."""
    apps_text = "\n".join(
        f"- {a.get('company', '?')} | {a.get('role', '?')} | "
        f"Status: {a.get('status', '?')} | Applied: {a.get('applied_at', '?')} | "
        f"Last activity: {a.get('last_activity', '?')}"
        for a in applications
    )
    return Task(
        description=(
            f"Review these active applications and recommend follow-up actions:\n\n"
            f"{apps_text}\n\n"
            "For each application:\n"
            "1. Is a follow-up overdue? (>7 days applied, >14 days interviewing)\n"
            "2. What action should be taken? (follow-up email, check status, close)\n"
            "3. Priority level: high / medium / low\n"
            "4. Draft subject line for any follow-up needed\n\n"
            "Ghost applications (>21 days no reply) should be marked for closing."
        ),
        expected_output=(
            "JSON array of action items: company, role, current_status, "
            "action_needed, priority, follow_up_subject (or null), "
            "mark_ghosted (bool)."
        ),
        agent=agent,
    )


def create_status_summary_task(agent: Agent, applications: list[dict]) -> Task:
    """Summarise the current state of the job search."""
    return Task(
        description=(
            f"Summarise the current job search status based on:\n"
            f"{applications}\n\n"
            "Provide:\n"
            "1. Pipeline health score (0-10)\n"
            "2. Stage breakdown counts\n"
            "3. Biggest risks (e.g., 'all eggs in one company')\n"
            "4. Top 3 recommended actions this week\n"
            "5. Predicted timeline to first offer (conservative estimate)"
        ),
        expected_output=(
            "JSON: pipeline_health (int), stage_counts (dict), "
            "risks (list), actions_this_week (list), "
            "estimated_offer_weeks (int)."
        ),
        agent=agent,
    )


# ─── Feedback / Learning ──────────────────────────────────────────────────────

def create_outcome_analysis_task(
    agent: Agent, applications_with_outcomes: list[dict]
) -> Task:
    """Identify patterns in what's working and what isn't."""
    data_text = "\n".join(
        f"- {a.get('company')} | {a.get('role')} | "
        f"Status: {a.get('status')} | ATS: {a.get('ats_score')} | "
        f"IP: {a.get('interview_probability')} | "
        f"Source: {a.get('source')}"
        for a in applications_with_outcomes
    )
    return Task(
        description=(
            f"Analyse these application outcomes to identify patterns:\n\n"
            f"{data_text}\n\n"
            "Identify:\n"
            "1. Which job sources convert best?\n"
            "2. Do higher ATS scores correlate with more replies?\n"
            "3. Which company sizes / stages respond most?\n"
            "4. Is there a role type with better interview rates?\n"
            "5. What should change in the next batch of applications?\n\n"
            "Be data-driven. Only report patterns with 2+ data points."
        ),
        expected_output=(
            "JSON: best_sources (list), ats_correlation (high/medium/low/unclear), "
            "responsive_stages (list), best_role_types (list), "
            "recommended_changes (list of actionable strings)."
        ),
        agent=agent,
    )