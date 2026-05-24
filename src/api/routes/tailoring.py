"""
src/api/routes/tailoring.py

POST /api/v1/tailoring/run         → full tailoring pipeline
POST /api/v1/tailoring/compile     → compile existing LaTeX to PDF
GET  /api/v1/tailoring/health      → liveness check
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, Response, UploadFile
from fastapi.responses import StreamingResponse
import io

from src.api.dependencies import get_tailoring_workflow
from src.tailoring.latex_compiler import LatexCompiler
from src.tailoring.parser import ResumeParser
from src.workflows.tailoring import TailoringWorkflow

logger = logging.getLogger(__name__)
router = APIRouter()

ALLOWED_TYPES = {
    "application/pdf",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    "application/x-tex",
    "text/x-tex",
    "application/octet-stream",   # browsers often send .tex as this
}


@router.post("/run")
async def run_tailoring(
    resume: Annotated[UploadFile, File(description="Resume file (.pdf / .docx / .tex)")],
    job_description: Annotated[str, Form(description="Full job description text")],
    output_format: Annotated[str, Form(description="latex or markdown")] = "latex",
    candidate_email: Annotated[str, Form()] = "",
    workflow: TailoringWorkflow = Depends(get_tailoring_workflow),
):
    """
    Full tailoring pipeline:
      1. Parse resume (PDF / DOCX / .tex)
      2. Extract candidate identity  ← local LLM
      3. Analyse JD intent           ← local LLM (Redis cached)
      4. Generate strategy           ← local
      5. Tailor resume               ← Gemini (1 call)
      6. Identity audit              ← local
      7. Recruiter critique          ← Gemini (1 call)
      8. Compile PDF (LaTeX only)    ← pdflatex (local)
      9. Score output                ← local

    Returns JSON with tailored_resume, scores, audit, critique, strategy.
    PDF bytes are NOT returned here — use /download-pdf after this call.
    """
    if output_format not in ("latex", "markdown"):
        raise HTTPException(400, "output_format must be 'latex' or 'markdown'")

    raw_bytes = await resume.read()
    if not raw_bytes:
        raise HTTPException(400, "Uploaded file is empty")

    filename = resume.filename or "resume.pdf"
    parser = ResumeParser()

    try:
        plain_text, raw_latex = parser.extract(raw_bytes, filename)
    except Exception as e:
        raise HTTPException(422, f"Could not parse resume: {e}")

    if not plain_text.strip():
        raise HTTPException(422, "Resume appears empty after text extraction")

    try:
        result = await workflow.run(
            resume_text=plain_text,
            job_description=job_description,
            job_id="manual",
            output_format=output_format,
            original_latex=raw_latex,
        )
    except Exception as e:
        logger.exception("Tailoring pipeline error")
        raise HTTPException(500, f"Tailoring failed: {e}")

    # PDF bytes are large — return metadata only; client can call /download-pdf
    pdf_bytes = result.pop("pdf_bytes", None)
    result["pdf_available"] = pdf_bytes is not None

    # Store PDF in memory keyed by a short token if needed (MVP: skip, return inline)
    if pdf_bytes:
        result["pdf_size_bytes"] = len(pdf_bytes)

    return result


@router.post("/compile-pdf")
async def compile_latex_to_pdf(
    latex_source: Annotated[str, Form(description="LaTeX source to compile")],
):
    """
    Compile arbitrary LaTeX source to PDF using local pdflatex.
    Returns the raw PDF as application/pdf.
    """
    compiler = LatexCompiler(timeout=30)
    if not compiler.available:
        raise HTTPException(503, "pdflatex not available on this server")

    issues = compiler.validate_latex(latex_source)
    if issues:
        raise HTTPException(422, f"Invalid LaTeX: {'; '.join(issues)}")

    pdf_bytes, log = compiler.compile(latex_source)
    if pdf_bytes is None:
        logger.error("Compile failed. Log excerpt: %s", log[-500:])
        raise HTTPException(422, f"LaTeX compilation failed. Check your source.")

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={"Content-Disposition": "attachment; filename=tailored_resume.pdf"},
    )


@router.get("/health")
async def tailoring_health():
    compiler = LatexCompiler()
    return {"status": "ok", "pdflatex_available": compiler.available}