import asyncio
from sqlalchemy import text
from src.database.connection import get_session

async def main():
    async with get_session() as session:
        res = await session.execute(text('SELECT count(*) FROM jobs'))
        print('Jobs:', res.scalar())
        res = await session.execute(text("SELECT count(*) FROM embeddings WHERE entity_type = 'job'"))
        print('Embeddings:', res.scalar())
        res = await session.execute(text("SELECT remote_type, seniority FROM jobs LIMIT 5"))
        print('Sample jobs:', res.fetchall())

if __name__ == "__main__":
    asyncio.run(main())
