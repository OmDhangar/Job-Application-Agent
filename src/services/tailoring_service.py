
# ─── Tailoring Service ────────────────────────────────────────────────────────
from __future__ import annotations

import logging
from uuid import UUID

from src.workflows.tailoring import TailoringWorkflow

logger = logging.getLogger(__name__)

class TailoringService:
    def __init__(self, workflow: TailoringWorkflow) -> None:
        self.workflow = workflow

    async def tailor(
        self,
        resume_bytes: bytes,
        filename: str,
        job_description: str,
        job_id: str = "manual",
        output_format: str = "latex",
    ) -> dict:
        from src.tailoring.parser import ResumeParser
        parser = ResumeParser()
        plain_text, raw_latex = parser.extract(resume_bytes, filename)

        if not plain_text.strip():
            raise ValueError("Could not extract text from resume")

        return await self.workflow.run(
            resume_text=plain_text,
            job_description=job_description,
            job_id=job_id,
            output_format=output_format,
            original_latex=raw_latex,
        )


