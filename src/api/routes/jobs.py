"""
src/api/routes/jobs.py  —  Job discovery and search endpoints.
"""
from __future__ import annotations
from uuid import UUID
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, desc
from sqlalchemy.ext.asyncio import AsyncSession
from src.api.dependencies import get_embedder, get_ranker, get_semantic_search
from src.database.connection import get_db
from src.schemas.job import JobRead, JobSearchRequest

router = APIRouter()


@router.get("/", response_model=list[dict])
async def list_jobs(
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
    remote_only: bool = False,
    seniority: str | None = None,
    db: AsyncSession = Depends(get_db),
):
    from src.database.models.jobs import Job
    q = select(Job).order_by(desc(Job.posted_at)).offset(offset).limit(limit)
    if remote_only:
        q = q.where(Job.remote_type == "remote")
    if seniority:
        q = q.where(Job.seniority == seniority)
    result = await db.execute(q)
    jobs = result.scalars().all()
    return [
        {
            "id": str(j.id), "title": j.title, "source": j.source,
            "location": j.location, "remote_type": j.remote_type,
            "seniority": j.seniority, "tech_stack": j.tech_stack,
            "opportunity_score": j.opportunity_score, "posted_at": str(j.posted_at),
        }
        for j in jobs
    ]


@router.get("/{job_id}", response_model=dict)
async def get_job(job_id: UUID, db: AsyncSession = Depends(get_db)):
    from src.database.models.jobs import Job
    result = await db.execute(select(Job).where(Job.id == job_id))
    job = result.scalar_one_or_none()
    if not job:
        raise HTTPException(404, "Job not found")
    return {"id": str(job.id), "title": job.title, "description": job.description,
            "source": job.source, "source_url": job.source_url, "tech_stack": job.tech_stack,
            "seniority": job.seniority, "remote_type": job.remote_type}


@router.post("/search")
async def semantic_search(
    req: JobSearchRequest,
    embedder=Depends(get_embedder),
    search=Depends(get_semantic_search),
    ranker=Depends(get_ranker),
):
    print(f"\n--- SEMANTIC SEARCH API ---")
    print(f"Request: query='{req.query}', remote_only={req.remote_only}, seniority={req.seniority}, top_k={req.top_k}")
    
    vec = embedder.embed(req.query)
    print(f"Embedding generated. Shape: {vec.shape}")
    
    results = await search.find_similar(
        vec, top_k=req.top_k * 2,
        filters={"remote_only": req.remote_only, "seniority": req.seniority},
    )
    print(f"Database query (find_similar) returned {len(results)} jobs.")
    if len(results) > 0:
        print(f"Sample raw job titles: {[j['title'] for j in results[:5]]}")
        
    import numpy as np
    scored = ranker.rank(
        candidate_vec=vec,
        candidate_skills=set(req.query.lower().split()),
        candidate_seniority=req.seniority or "mid",
        jobs=results,
    )
    print(f"Ranker returned {len(scored)} scored jobs.")
    
    id_to_job = {j["id"]: j for j in results}
    final_output = [
        {**id_to_job[s.job_id], "composite_score": s.composite,
         "semantic_score": s.semantic_score, "skill_overlap": s.skill_overlap}
        for s in scored[: req.top_k] if s.job_id in id_to_job
    ]
    print(f"Returning {len(final_output)} jobs to client.\n")
    return final_output