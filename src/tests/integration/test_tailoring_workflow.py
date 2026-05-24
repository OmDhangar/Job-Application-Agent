"""
tests/integration/test_tailoring_workflow.py

End-to-end integration tests for the full tailoring pipeline.
These tests call real AI models — requires:
  - Ollama running with qwen2.5:7b-instruct
  - GEMINI_API_KEY set (used for generation + critique steps)
  - pdflatex installed

Mark slow tests with: pytest -m integration
"""
from __future__ import annotations

import os
import pytest
import asyncio

from src.tests.fixtures.samples import SAMPLE_LATEX_RESUME, SAMPLE_JD_BACKEND

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="module")
def ai_router():
    from src.ai.router import AIRouter
    from src.ai.local_llm import OllamaClient
    from src.ai.gemini_client import GeminiClient
    from src.ai.cache import InferenceCache
    return AIRouter(
        cache=InferenceCache(),
        local=OllamaClient(),
        cloud=GeminiClient(),
    )


@pytest.fixture(scope="module")
def tailoring_workflow(ai_router):
    from src.workflows.tailoring import TailoringWorkflow
    from src.enrichment.jd_analyzer import JDAnalyzer
    from src.tailoring.strategy_generator import StrategyGenerator
    from src.tailoring.scorer import ResumeScorer
    from src.tailoring.latex_compiler import LatexCompiler
    return TailoringWorkflow(
        ai_router=ai_router,
        jd_analyzer=JDAnalyzer(router=ai_router),
        strategy_generator=StrategyGenerator(),
        scorer=ResumeScorer(),
        latex_compiler=LatexCompiler(),
    )


@pytest.mark.asyncio
async def test_full_latex_tailoring_pipeline(tailoring_workflow):
    """Tests the complete pipeline: parse → strategy → Gemini tailor → audit → compile → score."""
    from src.tailoring.parser import ResumeParser
    parser = ResumeParser()
    plain, raw_latex = parser.extract(SAMPLE_LATEX_RESUME.encode(), "resume.tex")

    result = await tailoring_workflow.run(
        resume_text=plain,
        job_description=SAMPLE_JD_BACKEND,
        job_id="test-integration",
        output_format="latex",
        original_latex=raw_latex,
    )

    # Core assertions
    assert "tailored_resume" in result
    assert len(result["tailored_resume"]) > 500
    assert r"\documentclass" in result["tailored_resume"]
    assert r"\end{document}" in result["tailored_resume"]

    # Scores should be populated
    scores = result["scores"]
    for key in ["ats_score", "authenticity_score", "interview_probability", "composite"]:
        assert 0 <= scores[key] <= 100, f"{key} out of range: {scores[key]}"

    # Audit should run without crash
    assert "passed" in result["audit"]
    assert isinstance(result["audit"]["issues"], list)

    # Critique from Gemini
    assert len(result["critique"]) > 50

    # Strategy plan
    assert result["strategy"]["target_role_type"] in (
        "backend", "fullstack", "devops", "ml", "data", "frontend", "other"
    )


@pytest.mark.asyncio
async def test_pdf_compilation(tailoring_workflow):
    """Verify PDF is generated when output_format=latex and pdflatex is available."""
    from src.tailoring.parser import ResumeParser
    from src.tailoring.latex_compiler import LatexCompiler

    compiler = LatexCompiler()
    if not compiler.available:
        pytest.skip("pdflatex not available")

    parser = ResumeParser()
    plain, raw_latex = parser.extract(SAMPLE_LATEX_RESUME.encode(), "resume.tex")

    result = await tailoring_workflow.run(
        resume_text=plain,
        job_description=SAMPLE_JD_BACKEND,
        output_format="latex",
        original_latex=raw_latex,
    )

    assert result["has_pdf"] is True, "PDF should have compiled successfully"


@pytest.mark.asyncio
async def test_markdown_fallback(tailoring_workflow):
    """When output_format=markdown, no LaTeX should be in output."""
    from src.tailoring.parser import ResumeParser
    parser = ResumeParser()
    plain, _ = parser.extract(SAMPLE_LATEX_RESUME.encode(), "resume.tex")

    result = await tailoring_workflow.run(
        resume_text=plain,
        job_description=SAMPLE_JD_BACKEND,
        output_format="markdown",
    )

    tailored = result["tailored_resume"]
    assert r"\documentclass" not in tailored
    assert result["has_pdf"] is False


@pytest.mark.asyncio
async def test_identity_guard_prevents_fabrication(tailoring_workflow):
    """
    The identity audit should NOT flag fabrication when tailoring a resume for a
    matching role — i.e., the system shouldn't be adding fake skills.
    """
    from src.tailoring.parser import ResumeParser
    parser = ResumeParser()
    plain, raw_latex = parser.extract(SAMPLE_LATEX_RESUME.encode(), "resume.tex")

    result = await tailoring_workflow.run(
        resume_text=plain,
        job_description=SAMPLE_JD_BACKEND,
        output_format="latex",
        original_latex=raw_latex,
    )

    fabrication_count = result["audit"]["fabrication_risk"]
    assert fabrication_count == 0, (
        f"Fabrication detected: {result['audit']['issues']}"
    )