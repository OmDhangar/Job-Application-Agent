"""
src/api/dependencies.py

Dependency injection container for FastAPI.
All service instances are built here and injected into routes.
This is the single wiring point — changing a provider here changes the whole app.
"""
from __future__ import annotations

from functools import lru_cache
from typing import AsyncGenerator

import httpx
import redis.asyncio as aioredis

from src.ai.cache import InferenceCache
from src.ai.gemini_client import GeminiClient
from src.ai.local_llm import OllamaClient
from src.ai.router import AIRouter
from src.database.connection import AsyncSessionLocal, get_session
from src.enrichment.jd_analyzer import JDAnalyzer
from src.matching.embedder import LocalEmbedder
from src.matching.ranker import JobRanker
from src.tailoring.scorer import ResumeScorer
from src.tailoring.strategy_generator import StrategyGenerator
from src.utils.config import Settings
from src.workflows.tailoring import TailoringWorkflow

settings = Settings()

# ─── Singletons (created once per process) ────────────────────────────────────

@lru_cache(maxsize=1)
def get_cache() -> InferenceCache:
    return InferenceCache()


@lru_cache(maxsize=1)
def get_ollama() -> OllamaClient:
    return OllamaClient()


@lru_cache(maxsize=1)
def get_gemini() -> GeminiClient:
    return GeminiClient()


@lru_cache(maxsize=1)
def get_router() -> AIRouter:
    return AIRouter(
        cache=get_cache(),
        local=get_ollama(),
        cloud=get_gemini(),
    )


@lru_cache(maxsize=1)
def get_embedder() -> LocalEmbedder:
    return LocalEmbedder(
        model_name=settings.embedding_model,
        cache=get_cache(),
        device=settings.embedding_device,
    )


@lru_cache(maxsize=1)
def get_ranker() -> JobRanker:
    return JobRanker(embedder=get_embedder())


# ─── Per-request factories ─────────────────────────────────────────────────────

def get_jd_analyzer() -> JDAnalyzer:
    return JDAnalyzer(router=get_router())


def get_strategy_generator() -> StrategyGenerator:
    return StrategyGenerator()


def get_scorer() -> ResumeScorer:
    return ResumeScorer()


def get_tailoring_workflow() -> TailoringWorkflow:
    return TailoringWorkflow(
        ai_router=get_router(),
        jd_analyzer=get_jd_analyzer(),
        strategy_generator=get_strategy_generator(),
        scorer=get_scorer(),
    )
