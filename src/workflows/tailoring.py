"""
src/workflows/tailoring.py

Resume tailoring workflow with full LaTeX support.

Pipeline:
  1. Parse resume (PDF / DOCX / .tex)  ← local, zero API cost
  2. Extract candidate identity         ← local LLM
  3. Analyze JD intent                  ← local LLM, Redis cached
  4. Build strategy plan                ← local logic
  5. Tailor resume (LaTeX or Markdown)  ← Gemini  (1 API call)
  6. Identity audit                     ← local (fabrication guard)
  7. Recruiter critique                 ← Gemini  (1 API call)
  8. Compile PDF if LaTeX               ← local pdflatex
  9. Score output                       ← local
"""
from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict

from src.ai.router import AIRouter, TaskComplexity
from src.enrichment.jd_analyzer import JDAnalyzer
from src.schemas.candidate import IdentityProfile
from src.tailoring.identity_guard import IdentityGuard
from src.tailoring.latex_compiler import LatexCompiler
from src.tailoring.strategy_generator import StrategyGenerator, StrategyPlan
from src.tailoring.scorer import ResumeScorer

logger = logging.getLogger(__name__)

# ─── System prompts ──────────────────────────────────────────────────────────

_TAILORING_SYSTEM = """
You are a recruiter-psychology-aware resume strategist who writes resumes that
pass ATS systems AND impress human technical recruiters.

Core rules you NEVER break:
- Do NOT fabricate companies, skills, degrees, or projects not in the original.
- Do NOT keyword-stuff — max 3 occurrences of any single technical term.
- Do NOT inflate claimed years of experience by more than 0.5 years.
- Do NOT rewrite the candidate's entire identity; reframe and reorder authentically.
- When outputting LaTeX, produce ONLY valid, compilable LaTeX with no prose around it.
- Preserve all LaTeX document structure (\\documentclass, \\begin{document}, etc.).
""".strip()

_CRITIQUE_SYSTEM = """
You are a skeptical senior technical recruiter reviewing 50 resumes per day.
You are direct, fast, and have zero patience for fluff.
Give a numeric score from 1-10 for first impression on line 1, then bullet your critique.
""".strip()

_IDENTITY_SYSTEM = """
You are a career analyst. Extract structured information from a resume.
Return ONLY valid JSON. No markdown fences. No preamble.
""".strip()


class TailoringWorkflow:

    def __init__(
        self,
        ai_router: AIRouter,
        jd_analyzer: JDAnalyzer,
        strategy_generator: StrategyGenerator,
        scorer: ResumeScorer,
        latex_compiler: LatexCompiler,
    ) -> None:
        self.router = ai_router
        self.jd_analyzer = jd_analyzer
        self.strategy = strategy_generator
        self.scorer = scorer
        self.compiler = latex_compiler

    async def run(
        self,
        resume_text: str,
        job_description: str,
        job_id: str = "manual",
        output_format: str = "latex",   # "latex" | "markdown"
        original_latex: str | None = None,  # raw .tex source if uploaded
    ) -> dict:
        """
        Run the full tailoring pipeline.

        Args:
            resume_text:    Plain-text extracted from the resume (all formats).
            job_description: Raw JD text.
            job_id:          DB job ID or "manual".
            output_format:   "latex" (default) or "markdown".
            original_latex:  Original .tex source — passed through to Gemini
                             for structure-preserving LaTeX tailoring.
        Returns:
            dict with tailored_resume, scores, audit, critique, strategy, pdf_bytes.
        """
        logger.info("Tailoring pipeline start — format=%s job=%s", output_format, job_id)

        # ── Phase 1: Local analysis (zero Gemini cost) ───────────────────────
        jd = await self.jd_analyzer.analyze(job_description)
        identity = await self._extract_identity(resume_text)
        guard = IdentityGuard(identity)
        plan = self.strategy.generate(identity, jd, fit_scores={})
        logger.info("Phase 1 complete — role_type=%s seniority=%s", jd.role_type, jd.seniority)

        # ── Phase 2: Gemini tailoring (1 API call) ───────────────────────────
        if output_format == "latex" and original_latex:
            prompt = self._build_latex_prompt(original_latex, job_description, plan)
        else:
            prompt = self._build_markdown_prompt(resume_text, job_description, plan)

        tailored = await self.router.route(
            prompt=prompt,
            complexity=TaskComplexity.GENERATION,
            cache_key=None,   # never cache tailored resumes — always fresh
            system=_TAILORING_SYSTEM,
        )

        # Clean any accidental prose wrapping
        if output_format == "latex":
            tailored = _extract_latex(tailored)
        logger.info("Phase 2 complete — tailored length=%d", len(tailored))

        # ── Phase 3: Identity audit (local) ──────────────────────────────────
        audit = guard.audit(
            original=resume_text,
            tailored=tailored,
            job_skills=jd.tech_stack + jd.required_skills,
        )
        if not audit["passed"]:
            logger.warning("Identity violations: %s", audit["issues"])

        # ── Phase 4: Gemini critique (1 API call) ────────────────────────────
        critique = await self.router.route(
            prompt=self._build_critique_prompt(tailored, job_description, output_format),
            complexity=TaskComplexity.CRITIQUE,
            system=_CRITIQUE_SYSTEM,
        )
        logger.info("Phase 4 complete — critique received")

        # ── Phase 5: Compile PDF (local pdflatex, no API cost) ───────────────
        pdf_bytes: bytes | None = None
        if output_format == "latex":
            pdf_bytes, compile_log = self.compiler.compile(tailored)
            if pdf_bytes is None:
                logger.warning("LaTeX compile failed: %s", compile_log[:300])
            else:
                logger.info("PDF compiled — %d bytes", len(pdf_bytes))

        # ── Phase 6: Score (local) ───────────────────────────────────────────
        scores = self.scorer.score(tailored, jd, identity, critique)

        return {
            "tailored_resume": tailored,
            "output_format": output_format,
            "pdf_bytes": pdf_bytes,
            "has_pdf": pdf_bytes is not None,
            "strategy": asdict(plan),
            "audit": audit,
            "critique": critique,
            "scores": {
                "ats_score": scores.ats_score,
                "authenticity_score": scores.authenticity_score,
                "recruiter_readability": scores.recruiter_readability,
                "technical_credibility": scores.technical_credibility,
                "interview_probability": scores.interview_probability,
                "composite": scores.composite,
            },
            "job_id": job_id,
        }

    # ─── Prompt builders ─────────────────────────────────────────────────────

    def _build_latex_prompt(
        self, latex_source: str, jd: str, plan: StrategyPlan
    ) -> str:
        return f"""
You are given a candidate's LaTeX resume source code and a job description.
Your task is to tailor the LaTeX resume for this specific job.

STRATEGY:
- Role type detected: {plan.target_role_type}
- Lead with these projects/experiences: {', '.join(plan.primary_emphasis)}
- De-emphasize (move down or compress): {', '.join(plan.compress)}
- ATS keywords to naturally include (ONLY if the candidate genuinely has them):
  {', '.join(plan.ats_keywords)}
- Preferred bullet action verbs: {', '.join(plan.bullet_focus)}
- Preserve this candidate voice: {plan.authenticity_notes}
- Section priorities: {', '.join(f"{s.section}={s.action}" for s in plan.section_weights)}

HARD CONSTRAINTS:
1. Output ONLY the complete, compilable LaTeX source. No prose, no explanation.
2. Preserve the EXACT \\documentclass, preamble packages, and \\newcommand macros.
3. Do NOT add skills, companies, or projects not present in the original.
4. Do NOT change dates, GPAs, degree names, or company names.
5. You MAY reorder \\resumeItem bullets within a job/project entry.
6. You MAY reorder projects relative to each other.
7. You MAY rewrite bullet text to better emphasize relevant impact — but only
   using facts already present in the original.
8. Keep the output under the same approximate page count as the original.

ORIGINAL LATEX RESUME:
{latex_source}

JOB DESCRIPTION:
{jd}

Output the complete tailored LaTeX source now:
""".strip()

    def _build_markdown_prompt(
        self, resume_text: str, jd: str, plan: StrategyPlan
    ) -> str:
        return f"""
Tailor this resume for the job below. Output clean Markdown only.

STRATEGY:
- Role type: {plan.target_role_type}
- Lead with: {', '.join(plan.primary_emphasis)}
- Compress: {', '.join(plan.compress)}
- ATS keywords (only if genuinely present): {', '.join(plan.ats_keywords)}
- Bullet verbs: {', '.join(plan.bullet_focus)}
- Preserve: {plan.authenticity_notes}

HARD CONSTRAINTS:
- Do NOT fabricate skills, companies, or achievements.
- Do NOT keyword-stuff — max 3 mentions of any single term.
- Do NOT inflate years of experience.

RESUME:
{resume_text}

JOB DESCRIPTION:
{jd}
""".strip()

    def _build_critique_prompt(
        self, tailored: str, jd: str, fmt: str
    ) -> str:
        content = tailored if fmt == "markdown" else _latex_to_plain(tailored)
        return f"""
Review this resume as a skeptical senior technical recruiter.

Line 1: Score X/10 (first impression)

Then cover:
1. ATS compliance issues (list any formatting or keyword problems)
2. Credibility signals (what builds trust)
3. Red flags (what raises doubt)
4. Single most impactful improvement

RESUME:
{content[:3000]}

ROLE:
{jd[:800]}
""".strip()

    # ─── Identity extraction ─────────────────────────────────────────────────

    async def _extract_identity(self, resume_text: str) -> IdentityProfile:
        prompt = (
            "Extract the following from this resume and return as JSON with exactly "
            "these keys: name (string), years_experience (float), core_skills (array), "
            "companies_worked (array), degrees (array), project_titles (array), "
            "voice_markers (array of 2-3 characteristic phrases), "
            "strongest_domain (string: backend|frontend|fullstack|ml|data|devops|research).\n\n"
            f"RESUME:\n{resume_text[:3000]}"
        )
        raw = await self.router.route(
            prompt=prompt,
            complexity=TaskComplexity.EXTRACTION,
            cache_key=f"identity:{hash(resume_text[:500])}",
            system=_IDENTITY_SYSTEM,
        )
        return _parse_identity(raw)


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _extract_latex(text: str) -> str:
    """Strip any accidental prose before \\documentclass or after \\end{document}."""
    # If model wrapped in markdown fences, strip them
    text = re.sub(r"```(?:latex|tex)?", "", text).strip().strip("`")
    # Find the real LaTeX document
    match = re.search(r"(\\documentclass.*)", text, re.DOTALL)
    if match:
        latex = match.group(1)
        # Trim anything after \end{document}
        end = latex.find(r"\end{document}")
        if end != -1:
            latex = latex[: end + len(r"\end{document}")]
        return latex.strip()
    return text.strip()


def _latex_to_plain(latex: str) -> str:
    """Very lightweight LaTeX → plain text for critique prompt."""
    text = re.sub(r"\\[a-zA-Z]+\{([^}]*)\}", r"\1", latex)
    text = re.sub(r"\\[a-zA-Z]+", " ", text)
    text = re.sub(r"[{}]", "", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def _parse_identity(raw: str) -> IdentityProfile:
    try:
        clean = re.sub(r"```(?:json)?", "", raw).strip().strip("`")
        data = json.loads(clean)
        return IdentityProfile(
            name=data.get("name", ""),
            years_experience=float(data.get("years_experience", 0)),
            core_skills=data.get("core_skills", []),
            companies_worked=data.get("companies_worked", []),
            degrees=data.get("degrees", []),
            project_titles=data.get("project_titles", []),
            voice_markers=data.get("voice_markers", []),
            strongest_domain=data.get("strongest_domain", "fullstack"),
        )
    except Exception as e:
        logger.warning("Identity parse failed: %s", e)
        return IdentityProfile(
            name="", years_experience=0, core_skills=[], companies_worked=[],
            degrees=[], project_titles=[], voice_markers=[], strongest_domain="fullstack",
        )