"""
src/matching/embedder.py   —  Local BGE embedding pipeline.
src/matching/ranker.py     —  Multi-signal job ranker.
src/matching/semantic_search.py — pgvector nearest-neighbor search.
"""
from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass

import numpy as np

logger = logging.getLogger(__name__)


# ─── Embedder ─────────────────────────────────────────────────────────────────

class LocalEmbedder:
    """
    BAAI/bge-base-en-v1.5 — 768-dim, runs on 8GB VRAM easily.
    All embeddings are cached in Redis to avoid re-computation.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        cache=None,
        device: str = "cuda",
    ) -> None:
        logger.info("Loading embedding model %s on %s", model_name, device)
        from sentence_transformers import SentenceTransformer
        self.model = SentenceTransformer(model_name, device=device)
        self.cache = cache
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> np.ndarray:
        key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"
        if self.cache:
            raw = self.cache.get_sync(key)
            if raw:
                return np.frombuffer(raw, dtype=np.float32)

        vec = self.model.encode(text, normalize_embeddings=True, show_progress_bar=False)
        if self.cache:
            self.cache.set_sync(key, vec.tobytes())
        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return self.model.encode(
            texts, normalize_embeddings=True,
            batch_size=32, show_progress_bar=False,
        )


