"""src/ai/local_llm.py"""
from __future__ import annotations
import logging, httpx
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()


class OllamaClient:
    def __init__(self, http: httpx.AsyncClient | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._base = settings.ollama_base_url
        self._model = settings.ollama_model
        self._http = http or http_client or httpx.AsyncClient(timeout=120)

    async def generate(self, prompt: str, system: str | None = None) -> str:
        payload = {
            "model": self._model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        }
        if system:
            payload["system"] = system
        try:
            r = await self._http.post(f"{self._base}/api/generate", json=payload)
            r.raise_for_status()
            return r.json()["response"]
        except httpx.ConnectError:
            raise RuntimeError(
                f"Ollama not reachable at {self._base}. Run: ollama serve"
            )

    async def health_check(self) -> bool:
        try:
            r = await self._http.get(f"{self._base}/api/tags", timeout=3)
            return r.status_code == 200
        except:
            return False