"""
src/api/dependencies.py  —  FastAPI dependency injection wiring.
All singleton infrastructure is built once and shared across requests.
"""
from __future__ import annotations

import httpx
from functools import lru_cache
from typing import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from src.ai.cache import InferenceCache
from src.ai.gemini_client import GeminiClient
from src.ai.local_llm import OllamaClient
from src.ai.router import AIRouter
from src.database.connection import AsyncSessionLocal, get_db
from src.enrichment.jd_analyzer import JDAnalyzer
from src.matching.embedder import LocalEmbedder
from src.matching.ranker import JobRanker
from src.matching.semantic_search import SemanticJobSearch
from src.outreach.personalizer import EmailPersonalizer
from src.outreach.contact_finder import ContactFinder
from src.tailoring.latex_compiler import LatexCompiler
from src.tailoring.scorer import ResumeScorer
from src.tailoring.strategy_generator import StrategyGenerator
from src.utils.config import Settings
from src.workflows.tailoring import TailoringWorkflow

settings = Settings()


# ── Singletons (instantiated once per process) ───────────────────────────────

@lru_cache(maxsize=1)
def get_cache() -> InferenceCache:
    return InferenceCache()


@lru_cache(maxsize=1)
def get_http_client() -> httpx.AsyncClient:
    return httpx.AsyncClient(
        timeout=httpx.Timeout(timeout=300.0, connect=10.0),
        follow_redirects=True,
    )


@lru_cache(maxsize=1)
def get_ollama() -> OllamaClient:
    return OllamaClient(http=get_http_client())


@lru_cache(maxsize=1)
def get_gemini() -> GeminiClient:
    return GeminiClient()


@lru_cache(maxsize=1)
def get_router() -> AIRouter:
    return AIRouter(cache=get_cache(), local=get_ollama(), cloud=get_gemini())


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


@lru_cache(maxsize=1)
def get_semantic_search() -> SemanticJobSearch:
    return SemanticJobSearch(session_factory=AsyncSessionLocal)


@lru_cache(maxsize=1)
def get_latex_compiler() -> LatexCompiler:
    return LatexCompiler(timeout=30)


# ── Per-request factories ─────────────────────────────────────────────────────

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
        latex_compiler=get_latex_compiler(),
    )


def get_email_personalizer() -> EmailPersonalizer:
    return EmailPersonalizer(router=get_router())


def get_contact_finder() -> ContactFinder:
    return ContactFinder(http=get_http_client())