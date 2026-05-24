"""
src/api/routes/tailoring.py

Tailoring endpoint. Accepts resume file + job description.
Returns scored, critiqued, strategy-driven tailored resume.
"""
from __future__ import annotations

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile

from src.api.dependencies import get_tailoring_workflow
from src.tailoring.parser import ResumeParser
from src.workflows.tailoring import TailoringWorkflow

logger = logging.getLogger(__name__)
router = APIRouter(tags=["tailoring"])


@router.post("/run")
async def run_tailoring(
    resume: Annotated[UploadFile, File()],
    job_description: Annotated[str, Form()],
    candidate_email: Annotated[str, Form()] = "",
    workflow: TailoringWorkflow = Depends(get_tailoring_workflow),
):
    """
    Full tailoring pipeline:
    1. Parse resume (local)
    2. Extract candidate identity (local LLM)
    3. Analyze JD intent (local LLM, cached)
    4. Generate strategy (local)
    5. Tailor resume (Gemini)
    6. Audit identity constraints (local)
    7. Recruiter critique (Gemini)
    8. Score output (local)
    """
    if resume.content_type not in ("application/pdf", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"):
        raise HTTPException(400, "Resume must be PDF or DOCX")

    raw_bytes = await resume.read()

    parser = ResumeParser()
    try:
        resume_text = parser.extract(raw_bytes, resume.filename or "resume.pdf")
    except Exception as e:
        raise HTTPException(422, f"Could not parse resume: {e}")

    if not resume_text.strip():
        raise HTTPException(422, "Resume appears empty after extraction")

    try:
        result = await workflow.run(
            resume_text=resume_text,
            job_description=job_description,
            job_id="manual",
        )
    except Exception as e:
        logger.exception("Tailoring pipeline error")
        raise HTTPException(500, f"Tailoring failed: {e}")

    return result


@router.get("/health")
async def tailoring_health():
    return {"status": "ok"}
