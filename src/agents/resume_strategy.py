"""
src/agents/resume_strategy.py

Resume Strategy Agent — generates the tailoring blueprint.
This runs BEFORE the tailoring agent so Gemini gets focused instructions.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_resume_strategy_agent


def create_resume_strategy_task(
    agent: Agent,
    identity_json: str,
    fit_analysis_json: str,
    jd_analysis_json: str,
) -> Task:
    return Task(
        description=(
            "Generate a precise resume tailoring strategy based on the analysis below.\n\n"
            f"CANDIDATE IDENTITY:\n{identity_json}\n\n"
            f"FIT ANALYSIS:\n{fit_analysis_json}\n\n"
            f"JD ANALYSIS:\n{jd_analysis_json}\n\n"
            "Produce a strategy covering:\n"
            "1. NARRATIVE ANGLE — the 1-sentence story this resume should tell\n"
            "2. SECTION ORDER — what order should sections appear? "
            "(e.g., for ML roles: Skills → Projects → Experience → Education)\n"
            "3. PRIMARY EMPHASIS — which 2 projects/jobs to lead with and WHY\n"
            "4. COMPRESS — which projects/roles to shorten or remove\n"
            "5. BULLET STRATEGY — what type of achievement to lead each bullet with "
            "(metric | architecture | impact | scale | collaboration)\n"
            "6. ATS KEYWORDS — exact phrases from JD the candidate genuinely has "
            "(NO keywords they don't have)\n"
            "7. SECTION WEIGHTS — expand / compress / reorder for each section\n"
            "8. AUTHENTICITY NOTES — what MUST be preserved verbatim\n"
            "9. DANGER ZONES — what the tailoring agent must NOT change\n\n"
            "Think like a principal engineer helping a friend, not a template machine."
        ),
        expected_output=(
            "JSON strategy object: narrative_angle, section_order (list), "
            "primary_emphasis (list of 2), compress (list), "
            "bullet_strategy (string), ats_keywords (list, authentic only), "
            "section_weights (dict), authenticity_notes (string), "
            "danger_zones (list of strings)."
        ),
        agent=agent,
    )


def create_section_reorder_task(
    agent: Agent, current_sections: list[str], role_type: str
) -> Task:
    """Determine optimal section ordering for a specific role type."""
    return Task(
        description=(
            f"The resume currently has these sections in this order: "
            f"{', '.join(current_sections)}\n\n"
            f"The target role type is: {role_type}\n\n"
            "Recommend the optimal section order for maximum recruiter impact. "
            "Recruiters spend 6-10 seconds on first pass — the most relevant "
            "section must be visible immediately.\n\n"
            "Rules:\n"
            "- For ML/research roles: lead with Skills or Projects\n"
            "- For backend roles: lead with Experience\n"
            "- For junior candidates: lead with Projects (compensates for lack of exp)\n"
            "- Education goes last unless applying to academia\n"
            "- Summary/Objective: only include if it adds real value"
        ),
        expected_output=(
            "JSON: recommended_order (list), rationale (string, 2 sentences)."
        ),
        agent=agent,
    )