"""
src/workflows/job_acquisition.py  —  Master end-to-end pipeline.

Orchestrates the full sequence:
  Job Discovery → Company Intel → Candidate Fit Analysis →
  Resume Strategy → Tailoring → Cold Email → Tracking
"""
from __future__ import annotations

import logging
from dataclasses import dataclass
from uuid import UUID

from src.services.job_service import JobService
from src.services.tailoring_service import TailoringService
from src.services.outreach_service import OutreachService
from src.tracking.tracker import ApplicationTracker

logger = logging.getLogger(__name__)


@dataclass
class AcquisitionRequest:
    candidate_id: UUID
    resume_bytes: bytes
    resume_filename: str
    target_seniority: str = "mid"
    remote_only: bool = False
    max_applications: int = 5
    output_format: str = "latex"    # latex | markdown


@dataclass
class AcquisitionResult:
    matched_jobs: list[dict]
    tailored_applications: list[dict]
    drafted_emails: list[dict]
    summary: dict


class JobAcquisitionWorkflow:
    """
    Single entry-point for the full pipeline.
    Called from the Streamlit UI "Run Full Pipeline" button or API endpoint.
    """

    def __init__(
        self,
        job_service: JobService,
        tailoring_service: TailoringService,
        outreach_service: OutreachService,
        tracker: ApplicationTracker,
        candidate_repo,
        application_repo,
    ) -> None:
        self.jobs = job_service
        self.tailoring = tailoring_service
        self.outreach = outreach_service
        self.tracker = tracker
        self.candidate_repo = candidate_repo
        self.application_repo = application_repo

    async def run(self, req: AcquisitionRequest) -> AcquisitionResult:
        logger.info("Full pipeline start — candidate=%s", req.candidate_id)

        # ── 1. Load candidate ─────────────────────────────────────────────────
        candidate = await self.candidate_repo.get(req.candidate_id)
        if not candidate:
            raise ValueError(f"Candidate {req.candidate_id} not found")
        resume_text = candidate.resume_raw or ""
        skills = candidate.skills or []

        # ── 2. Find matching jobs (local embedding + pgvector) ────────────────
        logger.info("Step 2: Semantic job matching")
        matched = await self.jobs.find_matching_jobs(
            candidate_text=resume_text,
            candidate_skills=skills,
            candidate_seniority=req.target_seniority,
            top_k=req.max_applications * 3,   # rank more, apply fewer
            filters={"remote_only": req.remote_only},
        )
        top_jobs = matched[: req.max_applications]
        logger.info("Matched %d jobs (showing top %d)", len(matched), len(top_jobs))

        # ── 3. Tailor resume + create applications ────────────────────────────
        tailored_apps: list[dict] = []
        for job in top_jobs:
            logger.info("Step 3: Tailoring for '%s'", job["title"])
            try:
                tailor_result = await self.tailoring.tailor(
                    resume_bytes=req.resume_bytes,
                    filename=req.resume_filename,
                    job_description=job.get("description", job["title"]),
                    job_id=job["id"],
                    output_format=req.output_format,
                )
                # Create application record
                app = await self.application_repo.create(
                    candidate_id=req.candidate_id,
                    job_id=UUID(job["id"]),
                )
                # Save tailored resume + scores to application
                await self.application_repo.update(
                    app.id,
                    tailored_resume=tailor_result["tailored_resume"],
                    ats_score=tailor_result["scores"]["ats_score"],
                    authenticity_score=tailor_result["scores"]["authenticity_score"],
                    recruiter_score=tailor_result["scores"]["recruiter_readability"],
                    interview_probability=tailor_result["scores"]["interview_probability"],
                    metadata={"scores": tailor_result["scores"]},
                )
                tailored_apps.append({
                    "application_id": str(app.id),
                    "job": job,
                    **tailor_result,
                })
            except Exception as e:
                logger.error("Tailoring failed for %s: %s", job["id"], e)

        # ── 4. Generate cold emails ───────────────────────────────────────────
        drafted_emails: list[dict] = []
        candidate_summary = f"{candidate.name}, {candidate.years_experience}yr exp, {', '.join(skills[:5])}"

        for app_data in tailored_apps:
            job = app_data["job"]
            try:
                email = await self.outreach.generate_for_application(
                    application_id=UUID(app_data["application_id"]),
                    candidate_summary=candidate_summary,
                    company_name=job.get("company_name", "Company"),
                    company_domain=job.get("company_domain", "company.com"),
                    job_title=job["title"],
                    tech_stack=job.get("tech_stack") or [],
                )
                drafted_emails.append(email)
            except Exception as e:
                logger.error("Email generation failed: %s", e)

        logger.info(
            "Pipeline complete — %d applications, %d emails drafted",
            len(tailored_apps), len(drafted_emails),
        )
        return AcquisitionResult(
            matched_jobs=matched,
            tailored_applications=tailored_apps,
            drafted_emails=drafted_emails,
            summary={
                "jobs_found": len(matched),
                "applications_created": len(tailored_apps),
                "emails_drafted": len(drafted_emails),
                "avg_interview_probability": (
                    sum(a["scores"]["interview_probability"] for a in tailored_apps)
                    / len(tailored_apps)
                    if tailored_apps else 0
                ),
            },
        )