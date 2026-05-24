"""
src/agents/candidate_identity.py

Candidate Identity Agent — extracts the authentic professional identity
from a resume. This runs before any tailoring to establish what CANNOT change.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_candidate_identity_agent


def create_identity_extraction_task(agent: Agent, resume_text: str) -> Task:
    return Task(
        description=(
            "Extract the candidate's authentic professional identity from this resume.\n\n"
            "Your output becomes the IDENTITY CONTRACT — nothing in the tailored "
            "resume may contradict it.\n\n"
            f"RESUME:\n{resume_text[:3000]}\n\n"
            "Extract:\n"
            "1. NAME — full name\n"
            "2. CORE IDENTITY — who they genuinely are in 2 sentences (do not inflate)\n"
            "3. YEARS OF EXPERIENCE — total professional exp (be conservative, not generous)\n"
            "4. STRONGEST DOMAIN — one of: backend | frontend | fullstack | ml | data | "
            "devops | research | mobile\n"
            "5. VERIFIED SKILLS — only skills explicitly evidenced in resume\n"
            "6. COMPANIES WORKED — exact names, do not paraphrase\n"
            "7. EDUCATION — degree(s), institution(s), year(s)\n"
            "8. PROJECTS — titles only, do not paraphrase\n"
            "9. VOICE MARKERS — 3 characteristic phrases that reflect their writing style\n"
            "10. GENUINE DIFFERENTIATORS — what truly sets them apart (be honest, not promotional)\n\n"
            "IMPORTANT: If something is not clearly stated in the resume, mark it as 'not found'. "
            "Do not infer skills from project names."
        ),
        expected_output=(
            "JSON with: name, core_identity (string), years_experience (float), "
            "strongest_domain (string), verified_skills (list), companies_worked (list), "
            "education (list of objects), project_titles (list), voice_markers (list), "
            "genuine_differentiators (list)."
        ),
        agent=agent,
    )


def create_trajectory_analysis_task(agent: Agent, resume_text: str) -> Task:
    """Analyse career trajectory for strategic positioning."""
    return Task(
        description=(
            "Analyse this candidate's career trajectory:\n\n"
            f"{resume_text[:3000]}\n\n"
            "Identify:\n"
            "1. CAREER DIRECTION — where are they heading? (e.g., moving from backend to ML)\n"
            "2. GROWTH RATE — are they progressing quickly, steadily, or slowly?\n"
            "3. CONSISTENCY — is the career story coherent or fragmented?\n"
            "4. CREDIBILITY SIGNALS — publications, open source, competitions, metrics\n"
            "5. POSITIONING OPPORTUNITY — what angle makes them most compelling to employers?\n"
            "6. HONEST GAPS — skills or experience they don't have but roles often require\n\n"
            "Be honest. A well-positioned average candidate beats a poorly-positioned strong one."
        ),
        expected_output=(
            "JSON with: career_direction, growth_rate (fast/steady/slow), "
            "consistency_score (0-10), credibility_signals (list), "
            "positioning_opportunity (string), honest_gaps (list)."
        ),
        agent=agent,
    )