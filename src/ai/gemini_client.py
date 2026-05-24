"""
src/ai/gemini_client.py

Thin async wrapper around Google Gemini.
Handles retries, rate-limit detection, and clean error propagation.
"""
from __future__ import annotations

import asyncio
import logging

import google.genai as genai
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class GeminiRateLimitError(Exception):
    pass


class GeminiClient:
    def __init__(self) -> None:
        self._client = genai.Client(api_key=settings.gemini_api_key)
        self._model = settings.gemini_model

    @retry(
        stop=stop_after_attempt(3),
        wait=wait_exponential(multiplier=2, min=2, max=30),
        retry=retry_if_exception_type(GeminiRateLimitError),
        reraise=True,
    )
    async def generate(self, prompt: str, system: str | None = None) -> str:
        full_prompt = f"{system}\n\n{prompt}" if system else prompt
        try:
            # google-genai is sync; run in executor to avoid blocking event loop
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None,
                lambda: self._client.models.generate_content(
                    model=self._model,
                    contents=full_prompt,
                ),
            )
            return response.text
        except Exception as exc:
            msg = str(exc).lower()
            if "quota" in msg or "rate" in msg or "429" in msg:
                logger.warning("Gemini rate limit hit: %s", exc)
                raise GeminiRateLimitError(str(exc)) from exc
            raise
