"""
src/agents/fit_analysis.py

Fit Analysis Agent — honest, structured assessment of candidate ↔ job match.
Runs before strategy generation. Feeds directly into resume and email strategy.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_fit_analysis_agent


def create_fit_analysis_task(
    agent: Agent,
    identity_json: str,
    jd_analysis_json: str,
) -> Task:
    return Task(
        description=(
            "Produce a rigorous fit analysis between this candidate and job.\n\n"
            f"CANDIDATE IDENTITY:\n{identity_json}\n\n"
            f"JOB ANALYSIS:\n{jd_analysis_json}\n\n"
            "Analyse:\n"
            "1. SKILL MATCH — which required skills does the candidate genuinely have?\n"
            "2. SKILL GAPS — which required skills are missing? Be specific.\n"
            "3. SENIORITY FIT — is the level realistic? Over/under-qualified?\n"
            "4. DOMAIN ALIGNMENT — does the candidate's strongest domain match the role?\n"
            "5. TRAJECTORY ALIGNMENT — is this role a natural next step in their career?\n"
            "6. GENUINE STRENGTHS — what makes this candidate compelling for this specific role?\n"
            "7. HONEST WEAKNESSES — what will a recruiter see as red flags?\n"
            "8. OVERALL FIT SCORE — 0-100, be calibrated (50 = average fit, 80 = strong fit)\n"
            "9. APPLICATION RECOMMENDATION — apply | apply with caveats | skip\n"
            "10. POSITIONING STRATEGY — in 2 sentences, how should the candidate frame themselves?\n\n"
            "Be honest. Fabricated confidence destroys credibility in interviews."
        ),
        expected_output=(
            "JSON with: matched_skills (list), skill_gaps (list), seniority_fit "
            "(over/under/right), domain_alignment (high/medium/low), "
            "trajectory_alignment (natural/stretch/mismatch), "
            "genuine_strengths (list), honest_weaknesses (list), "
            "overall_fit_score (int 0-100), recommendation (apply/apply_with_caveats/skip), "
            "positioning_strategy (string)."
        ),
        agent=agent,
    )


def create_gap_bridging_task(
    agent: Agent, skill_gaps: list[str], resume_text: str
) -> Task:
    """Find honest ways to address skill gaps without fabrication."""
    return Task(
        description=(
            f"The candidate is missing these required skills: {', '.join(skill_gaps)}\n\n"
            f"Their resume:\n{resume_text[:2000]}\n\n"
            "For each gap, determine:\n"
            "1. Can it be bridged by adjacent skills they DO have? (e.g., similar DB experience)\n"
            "2. Is there a transferable project that partially addresses it?\n"
            "3. Should it be mentioned proactively (shows self-awareness) or left unaddressed?\n"
            "4. Is the gap a dealbreaker or a nice-to-have?\n\n"
            "Do NOT suggest claiming skills they don't have."
        ),
        expected_output=(
            "JSON array of gap objects: "
            "skill_gap, bridge_strategy (string or null), "
            "adjacent_evidence (string or null), is_dealbreaker (bool), "
            "mention_proactively (bool)."
        ),
        agent=agent,
    )