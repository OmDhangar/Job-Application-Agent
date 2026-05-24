"""
src/agents/resume_tailoring.py

Resume Tailoring Agent — executes the strategy to produce the final resume.
Handles both LaTeX and Markdown output formats.
"""
from __future__ import annotations

from crewai import Agent, Task
from src.agents.base import build_resume_tailoring_agent


_LATEX_RULES = """
LATEX OUTPUT RULES (non-negotiable):
1. Output ONLY the complete compilable LaTeX source — no prose, no explanation.
2. Preserve \\documentclass, ALL \\usepackage lines, and ALL \\newcommand definitions exactly.
3. Do NOT change \\textbf, \\textit, \\href, or layout commands.
4. You MAY reorder \\resumeItem bullets within an entry.
5. You MAY reorder \\resumeProjectHeading entries relative to each other.
6. You MAY rewrite \\resumeItem text to improve relevance — using only real facts.
7. Do NOT change dates, GPA, degree names, or company names.
8. Do NOT add \\resumeItem bullets that didn't exist (you may modify existing ones).
9. Keep balanced braces — every { must have a matching }.
10. The output must compile with: pdflatex -interaction=nonstopmode resume.tex
"""

_MARKDOWN_RULES = """
MARKDOWN OUTPUT RULES:
1. Output clean Markdown only — no LaTeX, no HTML.
2. Use ## for section headers, **bold** for company/degree names.
3. Use bullet points (- ) for achievements.
4. Keep all dates, company names, and factual claims from the original.
"""


def create_latex_tailoring_task(
    agent: Agent,
    latex_source: str,
    strategy_json: str,
    jd_text: str,
) -> Task:
    return Task(
        description=(
            f"Tailor this LaTeX resume according to the strategy below.\n\n"
            f"STRATEGY:\n{strategy_json}\n\n"
            f"JOB DESCRIPTION (for context):\n{jd_text[:1500]}\n\n"
            f"{_LATEX_RULES}\n\n"
            f"ORIGINAL LATEX SOURCE:\n{latex_source}"
        ),
        expected_output=(
            "Complete, compilable LaTeX resume source starting with "
            r"\documentclass and ending with \end{document}. "
            "Nothing else — no explanation, no markdown fences."
        ),
        agent=agent,
        output_file="tailored_resume.tex",
    )


def create_markdown_tailoring_task(
    agent: Agent,
    resume_text: str,
    strategy_json: str,
    jd_text: str,
) -> Task:
    return Task(
        description=(
            f"Tailor this resume according to the strategy below.\n\n"
            f"STRATEGY:\n{strategy_json}\n\n"
            f"JOB DESCRIPTION:\n{jd_text[:1500]}\n\n"
            f"{_MARKDOWN_RULES}\n\n"
            f"ORIGINAL RESUME:\n{resume_text[:3000]}"
        ),
        expected_output=(
            "Complete tailored resume in Markdown format. "
            "No LaTeX, no explanation, no preamble."
        ),
        agent=agent,
        output_file="tailored_resume.md",
    )