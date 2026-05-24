"""
src/ai/local_llm.py

Async Ollama client for local LLM inference.
Zero API cost. Runs Qwen2.5 7B / Llama 3.1 8B / Phi-3 Mini on local GPU.
"""
from __future__ import annotations

import logging
import httpx

from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class OllamaClient:
    """
    Thin async wrapper around Ollama REST API.
    Ollama must be running: `ollama serve`
    Model must be pulled: `ollama pull qwen2.5:7b-instruct`
    """

    def __init__(self, http_client: httpx.AsyncClient | None = None) -> None:
        self._base = settings.ollama_base_url
        self._model = settings.ollama_model
        self._http = http_client or httpx.AsyncClient(timeout=120)

    async def generate(self, prompt: str, system: str | None = None) -> str:
        payload: dict = {
            "model": self._model,
            "prompt": prompt,
            "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        }
        if system:
            payload["system"] = system

        try:
            resp = await self._http.post(f"{self._base}/api/generate", json=payload)
            resp.raise_for_status()
            return resp.json()["response"]
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama not reachable at {self._base}. "
                "Run `ollama serve` and `ollama pull qwen2.5:7b-instruct`."
            )

    async def health_check(self) -> bool:
        try:
            r = await self._http.get(f"{self._base}/api/tags", timeout=3)
            return r.status_code == 200
        except Exception:
            return False
