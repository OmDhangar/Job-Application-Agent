"""
scripts/seed_jobs.py

Database seeding script to populate initial, high-quality, realistic jobs 
and company records for instant system testing.
"""
from __future__ import annotations

import asyncio
import hashlib
import logging
from datetime import datetime, timezone, timedelta

from src.database.connection import get_session
from src.database.models import Company, Job

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def make_fingerprint(source: str, source_id: str, title: str) -> str:
    payload = f"{source}:{source_id}:{title}"
    return hashlib.sha256(payload.encode()).hexdigest()


async def seed() -> None:
    logger.info("Starting database seed...")
    
    companies_data = [
        {
            "name": "Stripe",
            "domain": "stripe.com",
            "linkedin_url": "https://linkedin.com/company/stripe",
            "hq_location": "San Francisco, CA",
            "stage": "public",
            "headcount": 8000,
            "tech_stack": ["Ruby", "Go", "Java", "PostgreSQL", "Redis", "Kafka"],
            "hiring_urgency": 8,
        },
        {
            "name": "Figma",
            "domain": "figma.com",
            "linkedin_url": "https://linkedin.com/company/figma",
            "hq_location": "San Francisco, CA",
            "stage": "growth",
            "headcount": 1500,
            "tech_stack": ["TypeScript", "React", "Rust", "C++", "PostgreSQL"],
            "hiring_urgency": 9,
        },
        {
            "name": "Notion",
            "domain": "notion.so",
            "linkedin_url": "https://linkedin.com/company/notion",
            "hq_location": "San Francisco, CA",
            "stage": "growth",
            "headcount": 600,
            "tech_stack": ["TypeScript", "React", "Node.js", "PostgreSQL", "Redis"],
            "hiring_urgency": 7,
        }
    ]

    jobs_data = [
        {
            "company_name": "Stripe",
            "title": "Senior Backend Engineer - Core Platform",
            "source": "greenhouse",
            "source_id": "stripe-backend-101",
            "source_url": "https://boards.greenhouse.io/stripe/jobs/4829374002",
            "location": "Remote - US",
            "remote_type": "remote",
            "employment_type": "full_time",
            "seniority": "senior",
            "description": (
                "We are looking for a Senior Backend Engineer to join our Core Platform team. "
                "You will scale APIs that handle millions of payments daily, improve microservices throughput, "
                "and maintain fault-tolerant database schemas. "
                "Requirements: 5+ years backend systems experience. Deep knowledge of Python, Go, or Java. "
                "Strong PostgreSQL skills, Redis caching, Kafka event streaming, and Docker containerization."
            ),
            "requirements": ["Python/Go/Java", "PostgreSQL", "Kafka/RabbitMQ", "Docker", "Distributed Systems"],
            "tech_stack": ["Python", "Go", "PostgreSQL", "Redis", "Kafka", "Docker"],
            "salary_min": 160000,
            "salary_max": 210000,
            "posted_at": datetime.now(timezone.utc) - timedelta(days=2),
        },
        {
            "company_name": "Figma",
            "title": "Backend Software Engineer - Collaboration Systems",
            "source": "lever",
            "source_id": "figma-collab-202",
            "source_url": "https://jobs.lever.co/figma/collab-202",
            "location": "San Francisco, CA",
            "remote_type": "onsite",
            "employment_type": "full_time",
            "seniority": "mid",
            "description": (
                "Join Figma's real-time collaboration backend team. "
                "Work on low-latency document sync services, optimize memory footprint of server processes, "
                "and scale websocket connections. "
                "Requirements: Experience building scalable web backends. Proficient in Node.js, C++, or Rust. "
                "Experience with PostgreSQL, Redis caching, Docker, and designing RESTful/GraphQL APIs."
            ),
            "requirements": ["Node.js/Rust", "PostgreSQL", "Redis", "WebSockets", "Docker"],
            "tech_stack": ["Node.js", "Rust", "PostgreSQL", "Redis", "Docker", "WebSockets"],
            "salary_min": 140000,
            "salary_max": 180000,
            "posted_at": datetime.now(timezone.utc) - timedelta(days=5),
        },
        {
            "company_name": "Notion",
            "title": "Full-Stack Engineer - AI Features",
            "source": "ashby",
            "source_id": "notion-ai-303",
            "source_url": "https://jobs.ashbyhq.com/notion/ai-303",
            "location": "Hybrid - San Francisco",
            "remote_type": "hybrid",
            "employment_type": "full_time",
            "seniority": "mid",
            "description": (
                "Build the future of writing in Notion. Help us ship AI assistant features, "
                "vector databases integration for semantic search, and real-time content generation tools. "
                "Requirements: Proficiency with TypeScript, React, and Node.js. Experience integrating LLMs "
                "and vector embeddings. PostgreSQL, Redis, and Docker exposure."
            ),
            "requirements": ["TypeScript/React/Node.js", "PostgreSQL", "LLM APIs", "Docker"],
            "tech_stack": ["TypeScript", "React", "Node.js", "PostgreSQL", "Docker", "Redis"],
            "salary_min": 130000,
            "salary_max": 175000,
            "posted_at": datetime.now(timezone.utc) - timedelta(days=1),
        }
    ]

    async with get_session() as session:
        # Create Companies
        company_map = {}
        for c_info in companies_data:
            # Check if domain exists
            from sqlalchemy import select
            res = await session.execute(select(Company).where(Company.domain == c_info["domain"]))
            co = res.scalar_one_or_none()
            if not co:
                co = Company(**c_info)
                session.add(co)
                logger.info("Creating company: %s", c_info["name"])
            else:
                logger.info("Company %s already exists, skipping", c_info["name"])
            company_map[c_info["name"]] = co

        # Flush to get IDs
        await session.flush()

        # Create Jobs
        for j_info in jobs_data:
            fp = make_fingerprint(j_info["source"], j_info["source_id"], j_info["title"])
            res = await session.execute(select(Job).where(Job.fingerprint == fp))
            job = res.scalar_one_or_none()
            if not job:
                co = company_map[j_info["company_name"]]
                # Remove company_name from parameters for Job ORM
                params = j_info.copy()
                params.pop("company_name")
                params["company_id"] = co.id
                params["fingerprint"] = fp
                
                job = Job(**params)
                session.add(job)
                logger.info("Creating job: %s", j_info["title"])
            else:
                logger.info("Job %s already exists, skipping", j_info["title"])

    logger.info("Database seeding complete!")


if __name__ == "__main__":
    asyncio.run(seed())
