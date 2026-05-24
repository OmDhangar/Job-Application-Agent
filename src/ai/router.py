"""
src/ai/router.py  —  AI routing (local vs cloud).
"""
from __future__ import annotations
import hashlib, logging
from enum import Enum

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    EXTRACTION     = "extraction"
    CLASSIFICATION = "classification"
    ANALYSIS       = "analysis"
    GENERATION     = "generation"
    CRITIQUE       = "critique"


_TIER = {
    TaskComplexity.EXTRACTION:     "local",
    TaskComplexity.CLASSIFICATION: "local",
    TaskComplexity.ANALYSIS:       "local",
    TaskComplexity.GENERATION:     "cloud",
    TaskComplexity.CRITIQUE:       "cloud",
}


class AIRouter:
    def __init__(self, cache, local, cloud) -> None:
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
        key = cache_key or hashlib.sha256(prompt.encode()).hexdigest()
        if cache_key and (cached := await self.cache.get(key)):
            logger.debug("Cache hit [%s...]", key[:8])
            return cached

        tier = _TIER[complexity]
        try:
            result = await (self.local if tier == "local" else self.cloud).generate(
                prompt, system=system
            )
        except Exception as exc:
            logger.warning("%s tier failed: %s — degrading to local", tier, exc)
            result = await self.local.generate(prompt, system=system)

        if cache_key:
            await self.cache.set(key, result)
        return result