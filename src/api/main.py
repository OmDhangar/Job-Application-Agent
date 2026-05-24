"""
src/api/main.py  —  FastAPI application entry-point.
"""
from __future__ import annotations

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.middleware import RequestIDMiddleware
from src.api.routes import jobs, candidates, applications, tailoring, outreach
from src.database.connection import engine, Base
from src.utils.config import Settings

settings = Settings()
logger = logging.getLogger(__name__)

logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="[%(asctime)s] %(levelname)s %(name)s: %(message)s",
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create all tables on startup (use Alembic for production migrations)
    async with engine.begin() as conn:
        # Register pgvector extension first
        await conn.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        await conn.run_sync(Base.metadata.create_all)
    logger.info("Database tables ensured")
    yield
    await engine.dispose()
    logger.info("Database connections closed")


app = FastAPI(
    title="Job Acquisition OS",
    version="1.0.0",
    description="AI-powered job acquisition platform",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8501", "http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestIDMiddleware)

app.include_router(jobs.router,         prefix="/api/v1/jobs",         tags=["jobs"])
app.include_router(candidates.router,   prefix="/api/v1/candidates",   tags=["candidates"])
app.include_router(applications.router, prefix="/api/v1/applications", tags=["applications"])
app.include_router(tailoring.router,    prefix="/api/v1/tailoring",    tags=["tailoring"])
app.include_router(outreach.router,     prefix="/api/v1/outreach",     tags=["outreach"])


@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok", "version": "1.0.0"}


@app.get("/", tags=["health"])
async def root():
    return {"message": "Job Acquisition OS API", "docs": "/docs"}