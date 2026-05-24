import asyncio
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from src.database.connection import get_session
from src.database.models import Job, Embedding
from src.queues.publisher import QueuePublisher
from src.utils.config import Settings

async def trigger():
    settings = Settings()
    publisher = await QueuePublisher.connect(settings.rabbitmq_url)
    
    async with get_session() as session:
        # Get jobs without embeddings
        res = await session.execute(
            select(Job).outerjoin(Embedding, Job.id == Embedding.entity_id).where(Embedding.id == None)
        )
        jobs = res.scalars().all()
        
        print(f"Found {len(jobs)} jobs without embeddings. Queueing...")
        for job in jobs:
            text = f"{job.title} {job.description} {' '.join(job.tech_stack or [])}"
            await publisher.publish("jobs.embed", {"job_id": str(job.id), "text": text[:2000]})
            print(f"Queued job {job.id}")
            
    await publisher._conn.close()

if __name__ == "__main__":
    asyncio.run(trigger())
