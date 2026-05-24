"""
src/utils/config.py

Pydantic Settings — single source of truth for all configuration.
"""
from __future__ import annotations

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # ── Database ──────────────────────────────────────────────
    database_url: str = Field(
        "postgresql+asyncpg://jobos:password@localhost:5432/jobos",
        validation_alias="DATABASE_URL",
    )

    # ── Cache / Queue ─────────────────────────────────────────
    redis_url: str = Field("redis://localhost:6379/0", validation_alias="REDIS_URL")
    rabbitmq_url: str = Field("amqp://guest:guest@localhost/", validation_alias="RABBITMQ_URL")

    # ── AI: Cloud ─────────────────────────────────────────────
    gemini_api_key: str = Field("", validation_alias="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.5-flash", validation_alias="GEMINI_MODEL")

    # ── AI: Local ─────────────────────────────────────────────
    ollama_base_url: str = Field("http://localhost:11434", validation_alias="OLLAMA_BASE_URL")
    ollama_model: str = Field("gemma3n:e4b-it-q4_K_M", validation_alias="OLLAMA_MODEL")

    # ── Embeddings ────────────────────────────────────────────
    embedding_model: str = Field("BAAI/bge-base-en-v1.5", validation_alias="EMBEDDING_MODEL")
    embedding_device: str = Field("cuda", validation_alias="EMBEDDING_DEVICE")

    # ── Scraping ──────────────────────────────────────────────
    playwright_headless: bool = Field(True, validation_alias="PLAYWRIGHT_HEADLESS")
    scraper_throttle_ms: int = Field(2000, validation_alias="SCRAPER_THROTTLE_MS")

    # ── App ───────────────────────────────────────────────────
    debug: bool = Field(False, validation_alias="DEBUG")
    secret_key: str = Field("change-me-in-production", validation_alias="SECRET_KEY")

    model_config = {"env_file": ".env", "case_sensitive": False, "extra": "ignore"}
