"""src/ai/local_llm.py"""
from __future__ import annotations
import logging, httpx
from src.utils.config import Settings

logger = logging.getLogger(__name__)
settings = Settings()

# LLM generation can take several minutes for large prompts
_LLM_TIMEOUT = httpx.Timeout(timeout=300.0, connect=10.0)


class OllamaClient:
    def __init__(self, http: httpx.AsyncClient | None = None, http_client: httpx.AsyncClient | None = None) -> None:
        self._base = settings.ollama_base_url
        self._model = settings.ollama_model
        self._http = http or http_client or httpx.AsyncClient(timeout=_LLM_TIMEOUT)

    async def generate(self, prompt: str, system: str | None = None) -> str:
        payload = {
            "model": self._model, "prompt": prompt, "stream": False,
            "options": {"temperature": 0.1, "num_predict": 2048},
        }
        if system:
            payload["system"] = system

        last_exc: Exception | None = None
        for attempt in range(2):  # 1 retry on timeout
            try:
                r = await self._http.post(
                    f"{self._base}/api/generate",
                    json=payload,
                    timeout=_LLM_TIMEOUT,   # per-request override
                )
                r.raise_for_status()
                return r.json()["response"]
            except httpx.ConnectError:
                raise RuntimeError(
                    f"Ollama not reachable at {self._base}. Run: ollama serve"
                )
            except httpx.ReadTimeout as exc:
                last_exc = exc
                logger.warning(
                    "Ollama read timeout (attempt %d/2, model=%s, prompt_len=%d)",
                    attempt + 1, self._model, len(prompt),
                )
                if attempt == 0:
                    continue  # retry once

        raise RuntimeError(
            f"Ollama timed out after 2 attempts ({self._model}). "
            f"The prompt may be too large ({len(prompt)} chars) or Ollama is overloaded. "
            f"Original error: {last_exc}"
        )

    async def health_check(self) -> bool:
        try:
            r = await self._http.get(f"{self._base}/api/tags", timeout=3)
            return r.status_code == 200
        except:
            return False