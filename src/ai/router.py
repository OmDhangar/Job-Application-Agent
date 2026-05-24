"""
src/ai/router.py

AI Router — directs tasks to local or cloud inference based on complexity.
Local-first. Gemini only for generation and critique tasks.
"""
from __future__ import annotations

import hashlib
import logging
from enum import Enum
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from src.ai.local_llm import OllamaClient
    from src.ai.gemini_client import GeminiClient
    from src.ai.cache import InferenceCache

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    EXTRACTION     = "extraction"      # → local  (skill extraction, parsing)
    CLASSIFICATION = "classification"  # → local  (role type, seniority)
    ANALYSIS       = "analysis"        # → local  (similarity, scoring)
    GENERATION     = "generation"      # → cloud  (resume tailoring, email)
    CRITIQUE       = "critique"        # → cloud  (recruiter critique)


_ROUTING: dict[TaskComplexity, str] = {
    TaskComplexity.EXTRACTION:     "local",
    TaskComplexity.CLASSIFICATION: "local",
    TaskComplexity.ANALYSIS:       "local",
    TaskComplexity.GENERATION:     "cloud",
    TaskComplexity.CRITIQUE:       "cloud",
}


class AIRouter:
    """
    Single entry-point for all LLM inference in the system.
    Handles routing, caching, and graceful degradation.
    """

    def __init__(
        self,
        cache: "InferenceCache",
        local: "OllamaClient",
        cloud: "GeminiClient",
    ) -> None:
        self.cache = cache
        self.local = local
        self.cloud = cloud

    async def route(
        self,
        prompt: str,
        complexity: TaskComplexity,
        cache_key: str | None = None,
        system: str | None = None,
    ) -> str:
        key = cache_key or self._hash(prompt)

        if cached := await self.cache.get(key):
            logger.debug("Cache hit [%s...]", key[:8])
            return cached

        tier = _ROUTING[complexity]
        logger.info("Routing [%s] → %s", complexity.value, tier)

        result = await self._invoke(prompt, system, tier)
        await self.cache.set(key, result)
        return result

    async def _invoke(self, prompt: str, system: str | None, tier: str) -> str:
        try:
            if tier == "local":
                return await self.local.generate(prompt, system=system)
            return await self.cloud.generate(prompt, system=system)
        except Exception as exc:
            logger.warning("Primary tier '%s' failed: %s — degrading", tier, exc)
            if tier == "cloud":
                logger.info("Falling back to local model")
                return await self.local.generate(prompt, system=system)
            raise

    @staticmethod
    def _hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()
