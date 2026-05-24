"""
src/adapters/base.py  —  Abstract adapter contract + CanonicalJob dataclass.
"""
from __future__ import annotations

import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator


@dataclass
class CanonicalJob:
    title: str
    company_name: str
    source: str
    source_url: str
    description: str
    location: str | None = None
    remote_type: str | None = None
    employment_type: str | None = None
    seniority: str | None = None
    tech_stack: list[str] = field(default_factory=list)
    requirements: list[str] = field(default_factory=list)
    salary_min: int | None = None
    salary_max: int | None = None
    salary_currency: str = "USD"
    posted_at: datetime | None = None
    source_id: str | None = None
    company_domain: str | None = None
    raw_metadata: dict = field(default_factory=dict)

    @property
    def fingerprint(self) -> str:
        payload = f"{self.source}:{self.source_id or self.source_url}:{self.title}"
        return hashlib.sha256(payload.encode()).hexdigest()


class AbstractJobAdapter(ABC):
    source_name: str

    @abstractmethod
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]: ...

    @abstractmethod
    async def health_check(self) -> bool: ...