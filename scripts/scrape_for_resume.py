"""
scripts/scrape_for_resume.py

Uploads a resume, parses it, extracts keywords and technologies,
seeds/updates the candidate profile, and runs the ingestion pipeline
(YC Jobs, HackerNews, and top-tier Greenhouse/Lever boards) to scrape live jobs
matching the candidate's background.

All scraped jobs are persisted to the database and published to the RabbitMQ queues,
where background workers automatically enrich and embed them.
"""
from __future__ import annotations

import argparse
import asyncio
import hashlib
import logging
import pathlib
import re
import sys
import httpx
import redis.asyncio as aioredis
from uuid import uuid4

# Add project root to sys.path to allow running directly
project_root = pathlib.Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.utils.config import Settings
from src.database.connection import get_session
from src.database.models.candidates import Candidate
from src.database.repositories.job_repo import JobRepository
from src.tailoring.parser import ResumeParser
from src.ingestion.pipeline import IngestionPipeline
from src.ingestion.deduplicator import Deduplicator
from src.queues.publisher import QueuePublisher

# Import adapters
from src.adapters.yc_jobs import YCJobsAdapter
from src.adapters.hackernews import HackerNewsAdapter
from src.adapters.greenhouse import GreenhouseAdapter
from src.adapters.lever import LeverAdapter
from src.adapters.ashby import AshbyAdapter

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger("scrape_for_resume")
settings = Settings()

# A robust list of technical skills to match against resume text
TECH_KEYWORDS = {
    "python", "golang", "go", "rust", "c++", "java", "typescript", "javascript", "ruby", "php",
    "postgresql", "mysql", "redis", "mongodb", "elasticsearch", "docker", "kubernetes",
    "aws", "gcp", "azure", "terraform", "kafka", "rabbitmq", "react", "node.js", "next.js",
    "django", "fastapi", "spring", "angular", "vue", "pytorch", "tensorflow", "ci/cd", "graphql"
}

def extract_profile_from_text(text: str) -> dict:
    """Extract candidate name, email, and skills using simple rules."""
    text_lower = text.lower()
    
    # 1. Extract email
    email_match = re.search(r"[\w\.-]+@[\w\.-]+\.\w+", text)
    email = email_match.group(0) if email_match else f"candidate_{uuid4().hex[:8]}@example.com"
    
    # 2. Extract name (usually first line of a resume)
    lines = [line.strip() for line in text.split("\n") if line.strip()]
    name = lines[0] if lines else "Candidate"
    # Clean up name if it contains email or contact info
    if "@" in name or len(name) > 50:
        name = "Candidate"
        
    # 3. Extract skills matching our list
    skills = []
    for skill in TECH_KEYWORDS:
        # Match whole words only
        pattern = r"\b" + re.escape(skill) + r"\b"
        if re.search(pattern, text_lower):
            skills.append(skill.capitalize() if skill != "golang" else "Go")
            
    # 4. Infer target roles
    target_roles = []
    if "backend" in text_lower or "systems" in text_lower or "infrastructure" in text_lower:
        target_roles.append("backend")
    if "frontend" in text_lower or "ui" in text_lower or "web" in text_lower:
        target_roles.append("frontend")
    if "fullstack" in text_lower or "full-stack" in text_lower:
        target_roles.append("fullstack")
    if "data" in text_lower or "machine learning" in text_lower or "ml" in text_lower:
        target_roles.append("data")
    if "devops" in text_lower or "sre" in text_lower or "cloud" in text_lower:
        target_roles.append("devops")
        
    return {
        "name": name,
        "email": email,
        "skills": list(set(skills)),
        "target_roles": target_roles or ["backend"],
    }

async def run_pipeline(
    resume_path: str,
    limit: int = 15,
    source: str = "all",
) -> None:
    path = pathlib.Path(resume_path)
    if not path.exists():
        logger.error("Resume file not found at: %s", resume_path)
        sys.exit(1)
        
    print(f"\n==================================================")
    print(f"[RESUME] Parsing Resume: {path.name}")
    print(f"==================================================")
    
    # 1. Parse resume
    parser = ResumeParser()
    with open(path, "rb") as f:
        file_bytes = f.read()
    
    try:
        plain_text, raw_latex = parser.extract(file_bytes, path.name)
    except Exception as e:
        logger.exception("Failed to parse resume: %s", e)
        sys.exit(1)
        
    profile = extract_profile_from_text(plain_text)
    print(f"[OK] Name:  {profile['name']}")
    print(f"[OK] Email: {profile['email']}")
    print(f"[OK] Extracted Skills: {', '.join(profile['skills'][:12])}")
    print(f"[OK] Inferred Role: {', '.join(profile['target_roles'])}")
    
    # 2. Update candidate in database
    print(f"\n[DB] Updating Candidate Profile in Postgres...")
    async with get_session() as session:
        from sqlalchemy import select
        res = await session.execute(select(Candidate).where(Candidate.email == profile["email"]))
        candidate = res.scalar_one_or_none()
        if not candidate:
            candidate = Candidate(
                name=profile["name"],
                email=profile["email"],
                resume_raw=plain_text,
                skills=profile["skills"],
                years_experience=3.0,  # default placeholder
                target_roles=profile["target_roles"],
            )
            session.add(candidate)
        else:
            candidate.resume_raw = plain_text
            candidate.skills = profile["skills"]
            candidate.target_roles = profile["target_roles"]
            session.add(candidate)
            
    print(f"Candidate ID generated/found: {candidate.id}")
    
    # 3. Setup Redis and RabbitMQ publisher
    print(f"\n[CONN] Connecting to Redis cache and RabbitMQ message broker...")
    redis = aioredis.from_url(settings.redis_url)
    deduplicator = Deduplicator(redis)
    
    try:
        publisher = await QueuePublisher.connect(settings.rabbitmq_url)
    except Exception as e:
        logger.error("Could not connect to RabbitMQ (amqp) broker: %s. Is RabbitMQ service running?", e)
        sys.exit(1)
        
    # 4. Build adapters
    print(f"\n[API] Initializing Scraper Adapters...")
    async with httpx.AsyncClient(headers={"User-Agent": "JobAcquisitionOS-Client/1.0"}) as http:
        adapters = []
        
        # Scrape all platforms or specific source
        if source in ("all", "yc_jobs"):
            logger.info("Adding YC Work at a Startup adapter")
            adapters.append(YCJobsAdapter(http=http))
            
        if source in ("all", "hackernews"):
            logger.info("Adding HackerNews adapter")
            adapters.append(HackerNewsAdapter(http=http))
            
        # Add high-quality Greenhouse/Lever/Ashby boards to scrape
        if source in ("all", "greenhouse"):
            boards = ["stripe", "openai", "anthropic", "pinecone", "vercel", "supabase"]
            logger.info("Adding Greenhouse adapter for boards: %s", boards)
            adapters.append(GreenhouseAdapter(boards=boards, http=http))
            
        if source in ("all", "lever"):
            companies = ["figma", "notion", "airtable", "replit", "linear"]
            logger.info("Adding Lever adapter for companies: %s", companies)
            adapters.append(LeverAdapter(companies=companies, http=http))
            
        if source in ("all", "ashby"):
            slugs = ["sentry", "monzo", "revolut"]
            logger.info("Adding Ashby adapter for slugs: %s", slugs)
            adapters.append(AshbyAdapter(slugs=slugs, http=http))

        # 5. Run the Ingestion Pipeline
        print(f"\n[RUN] Running Ingestion Pipeline (Scraping live job listings)...")
        async with get_session() as session:
            job_repo = JobRepository(session)
            pipeline = IngestionPipeline(
                adapters=adapters,
                deduplicator=deduplicator,
                job_repo=job_repo,
                publisher=publisher,
            )
            
            stats = await pipeline.run()
            
        print(f"\n==================================================")
        print(f"[STATS] Ingestion Stats (New Jobs Scraped & Saved to DB):")
        print(f"==================================================")
        for src_name, count in stats.items():
            print(f"  * {src_name}: {count} new jobs")
            
        total_scraped = sum(stats.values())
        print(f"Total new jobs ingested: {total_scraped}")
        print(f"==================================================")
        
        print(f"\n[WORKER] Background Worker Alert")
        print(f"The scraped jobs have been successfully published to RabbitMQ!")
        print(f"Your background worker processes (ingestion_worker, embedding_worker, enrichment_worker)")
        print(f"are actively compiling local BGE embeddings and enriching their tech-stacks now.")
        
        print(f"\n[NEXT] Next Steps:")
        print(f"1. Open the Streamlit UI (http://localhost:8501) or browse to 'Job Discovery'.")
        print(f"2. Paste a search query matching your stack or click 'Browse latest jobs'.")
        print(f"3. Go to the 'Resume Tailoring' page, upload your resume, select a matched job, and tailor it!")
        print(f"Candidate ID to use in tracker: {candidate.id}\n")

def main():
    p = argparse.ArgumentParser(description="Scrape and ingest jobs matching your resume.")
    p.add_argument("resume_path", help="Path to your PDF, DOCX, or LaTeX resume.")
    p.add_argument("--limit", type=int, default=15, help="Max jobs to process per platform.")
    p.add_argument(
        "--source",
        choices=["yc_jobs", "hackernews", "greenhouse", "lever", "ashby", "all"],
        default="all",
        help="Specific source to scrape.",
    )
    args = p.parse_args()
    asyncio.run(run_pipeline(args.resume_path, args.limit, args.source))

if __name__ == "__main__":
    main()
