# Job Acquisition Operating System — Complete Architecture

## Architectural Autopsy of the Current System

Before redesigning, here is exactly what is wrong with the current code:

| File | Problem |
|------|---------|
| `agents.py` | Monolithic. AI call, text extraction, and agent wiring in one module. No interface contracts. |
| `crew.py` | Hardcoded inputs. File-path-dependent tools. No DI. Workflow not reusable as a service. |
| `crew_run.py` | One-shot script. No retry, no queue, no observability hooks. |
| `connection.py` | SQLite. No pooling. No migrations. No async support. |
| `queries.py` | Stub functions returning dicts. No ORM models. No schema enforcement. |
| `streamlit_app.py` | UI, AI logic, and DB writes all in one function. Untestable. |
| `chroma.sqlite3` | Vector DB embedded in project root. No persistence strategy. |

**Root failure**: The entire system is a single-tier pipeline. There is no separation between ingestion, intelligence, storage, and presentation.

---

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                     PRESENTATION LAYER                          │
│            Streamlit MVP  /  FastAPI + React (v2)               │
└──────────────────────────────┬──────────────────────────────────┘
                               │ HTTP / WebSocket
┌──────────────────────────────▼──────────────────────────────────┐
│                      API GATEWAY (FastAPI)                       │
│   Auth │ Rate Limiting │ Request Validation │ Response Shaping   │
└──┬─────────────┬───────────────┬────────────────────┬───────────┘
   │             │               │                    │
   ▼             ▼               ▼                    ▼
[Jobs API]  [Candidates]  [Applications]       [Intelligence]
   │             │               │                    │
   └─────────────┴───────────────┴────────────────────┘
                               │
           ┌───────────────────▼──────────────────────┐
           │           SERVICE LAYER                    │
           │  JobService │ TailoringService │           │
           │  OutreachService │ TrackingService         │
           └───────────────────┬──────────────────────┘
                               │
           ┌───────────────────▼──────────────────────┐
           │        ORCHESTRATION LAYER (CrewAI)       │
           │   Crews │ Agents │ Tasks │ Workflows      │
           └────────┬──────────────────────────────────┘
                    │
      ┌─────────────┼─────────────────┐
      ▼             ▼                 ▼
  [AI Router]  [Queue Layer]    [Ingestion Engine]
  Local/Cloud  RabbitMQ/Redis   Playwright Adapters
      │             │                 │
      └─────────────┴─────────────────┘
                    │
      ┌─────────────▼──────────────────────────┐
      │         DATA LAYER                      │
      │  PostgreSQL + pgvector │ Redis Cache    │
      │  Raw payload store │ Embedding store    │
      └────────────────────────────────────────┘
```

---

## Folder Structure

```
job_acquisition_os/
│
├── src/
│   ├── agents/                    # CrewAI agent definitions
│   │   ├── __init__.py
│   │   ├── base.py                # AgentFactory, base configs
│   │   ├── job_discovery.py
│   │   ├── company_research.py
│   │   ├── candidate_identity.py
│   │   ├── fit_analysis.py
│   │   ├── resume_strategy.py
│   │   ├── resume_tailoring.py
│   │   ├── recruiter_critic.py
│   │   ├── cold_email.py
│   │   ├── application_tracker.py
│   │   └── feedback.py
│   │
│   ├── workflows/                 # Crew orchestration
│   │   ├── __init__.py
│   │   ├── job_acquisition.py     # Master workflow
│   │   ├── tailoring.py           # Resume tailoring crew
│   │   ├── outreach.py            # Cold email crew
│   │   └── intelligence.py        # Company intel crew
│   │
│   ├── ingestion/                 # Job scraping & ingestion
│   │   ├── __init__.py
│   │   ├── pipeline.py            # Async ingestion orchestrator
│   │   ├── deduplicator.py        # Fingerprint-based dedup
│   │   └── scheduler.py           # APScheduler config
│   │
│   ├── adapters/                  # Source-specific adapters
│   │   ├── __init__.py
│   │   ├── base.py                # AbstractJobAdapter
│   │   ├── linkedin.py
│   │   ├── greenhouse.py
│   │   ├── lever.py
│   │   ├── ashby.py
│   │   ├── wellfound.py
│   │   ├── yc_jobs.py
│   │   ├── internshala.py
│   │   └── hackernews.py
│   │
│   ├── enrichment/                # AI enrichment pipelines
│   │   ├── __init__.py
│   │   ├── company_enricher.py    # Tech stack, stage, culture
│   │   ├── jd_analyzer.py         # Intent, requirements extraction
│   │   ├── candidate_profiler.py  # Identity preservation layer
│   │   └── skill_extractor.py     # Local model skill extraction
│   │
│   ├── matching/                  # Semantic matching engine
│   │   ├── __init__.py
│   │   ├── embedder.py            # Local embedding pipeline
│   │   ├── ranker.py              # Multi-signal scoring
│   │   ├── semantic_search.py     # pgvector queries
│   │   └── scorer.py              # Composite scoring (ATS+recruiter)
│   │
│   ├── tailoring/                 # Resume tailoring engine
│   │   ├── __init__.py
│   │   ├── parser.py              # PDF/DOCX → structured resume
│   │   ├── identity_guard.py      # Authenticity constraints
│   │   ├── strategy_generator.py  # Section weighting logic
│   │   ├── bullet_rewriter.py     # Bullet optimization
│   │   ├── ats_validator.py       # ATS compliance checker
│   │   └── scorer.py              # Multi-dimensional scoring
│   │
│   ├── outreach/                  # Cold email engine
│   │   ├── __init__.py
│   │   ├── contact_finder.py      # Email discovery
│   │   ├── personalizer.py        # Deep personalization
│   │   └── templates.py           # Non-template templates
│   │
│   ├── tracking/                  # Application tracking
│   │   ├── __init__.py
│   │   ├── tracker.py
│   │   └── analytics.py
│   │
│   ├── database/
│   │   ├── __init__.py
│   │   ├── connection.py          # Async SQLAlchemy + pgvector
│   │   ├── migrations/            # Alembic migrations
│   │   ├── models/                # ORM models
│   │   │   ├── jobs.py
│   │   │   ├── companies.py
│   │   │   ├── candidates.py
│   │   │   ├── applications.py
│   │   │   ├── outreach.py
│   │   │   ├── embeddings.py
│   │   │   └── raw_payloads.py
│   │   └── repositories/          # Data access layer
│   │       ├── job_repo.py
│   │       ├── candidate_repo.py
│   │       └── application_repo.py
│   │
│   ├── schemas/                   # Pydantic schemas
│   │   ├── __init__.py
│   │   ├── job.py
│   │   ├── candidate.py
│   │   ├── application.py
│   │   └── outreach.py
│   │
│   ├── services/                  # Business logic services
│   │   ├── __init__.py
│   │   ├── job_service.py
│   │   ├── tailoring_service.py
│   │   ├── outreach_service.py
│   │   └── tracking_service.py
│   │
│   ├── api/                       # FastAPI application
│   │   ├── __init__.py
│   │   ├── main.py
│   │   ├── dependencies.py        # DI providers
│   │   ├── middleware.py
│   │   └── routes/
│   │       ├── jobs.py
│   │       ├── candidates.py
│   │       ├── applications.py
│   │       ├── tailoring.py
│   │       └── outreach.py
│   │
│   ├── ui/                        # Streamlit MVP
│   │   ├── __init__.py
│   │   ├── app.py
│   │   ├── pages/
│   │   │   ├── 1_Job_Discovery.py
│   │   │   ├── 2_Resume_Tailor.py
│   │   │   ├── 3_Cold_Email.py
│   │   │   └── 4_Applications.py
│   │   └── components/
│   │       ├── job_card.py
│   │       └── resume_viewer.py
│   │
│   ├── queues/                    # RabbitMQ / Redis workers
│   │   ├── __init__.py
│   │   ├── publisher.py
│   │   ├── consumer.py
│   │   └── workers/
│   │       ├── ingestion_worker.py
│   │       ├── enrichment_worker.py
│   │       ├── embedding_worker.py
│   │       └── tailoring_worker.py
│   │
│   ├── ai/                        # AI routing & inference
│   │   ├── __init__.py
│   │   ├── router.py              # Local vs cloud routing
│   │   ├── local_llm.py           # Ollama client
│   │   ├── gemini_client.py       # Gemini client w/ fallback
│   │   ├── embedder.py            # Local embedding model
│   │   └── cache.py               # Inference result caching
│   │
│   └── utils/
│       ├── __init__.py
│       ├── text.py
│       ├── retry.py
│       ├── fingerprint.py
│       └── config.py              # Pydantic settings
│
├── tests/
│   ├── unit/
│   ├── integration/
│   └── fixtures/
│
├── scripts/
│   ├── migrate.sh
│   ├── seed_jobs.py
│   └── run_worker.sh
│
├── docker/
│   ├── Dockerfile.api
│   ├── Dockerfile.worker
│   └── docker-compose.yml
│
├── alembic.ini
├── pyproject.toml
└── .env.example
```

---

## Database Schema

```sql
-- Enable pgvector
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- ─── Companies ────────────────────────────────────────────────────────────────
CREATE TABLE companies (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    domain          TEXT UNIQUE,
    linkedin_url    TEXT,
    hq_location     TEXT,
    stage           TEXT,           -- seed, series_a, series_b, public, unknown
    headcount       INT,
    tech_stack      TEXT[],
    engineering_culture JSONB,      -- {"remote_friendly": true, "eng_blog": "...", ...}
    hiring_urgency  SMALLINT,       -- 0-10 score
    enriched_at     TIMESTAMPTZ,
    raw_metadata    JSONB,          -- catch-all for source-specific data
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ─── Jobs ─────────────────────────────────────────────────────────────────────
CREATE TABLE jobs (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    company_id      UUID REFERENCES companies(id),
    title           TEXT NOT NULL,
    source          TEXT NOT NULL,  -- linkedin, greenhouse, lever, ashby, ...
    source_id       TEXT,           -- original ID in source system
    source_url      TEXT,
    location        TEXT,
    remote_type     TEXT,           -- remote, hybrid, onsite
    employment_type TEXT,           -- full_time, contract, internship
    seniority       TEXT,           -- intern, junior, mid, senior, staff, principal
    description     TEXT,
    requirements    TEXT[],
    responsibilities TEXT[],
    tech_stack      TEXT[],
    salary_min      INT,
    salary_max      INT,
    salary_currency TEXT DEFAULT 'USD',
    posted_at       TIMESTAMPTZ,
    expires_at      TIMESTAMPTZ,
    enriched        BOOLEAN DEFAULT FALSE,
    opportunity_score FLOAT,        -- composite AI-generated score
    raw_metadata    JSONB,
    fingerprint     TEXT UNIQUE,    -- SHA-256 for deduplication
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_jobs_source ON jobs(source);
CREATE INDEX idx_jobs_opportunity_score ON jobs(opportunity_score DESC);
CREATE INDEX idx_jobs_posted_at ON jobs(posted_at DESC);

-- ─── Candidates ───────────────────────────────────────────────────────────────
CREATE TABLE candidates (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name            TEXT NOT NULL,
    email           TEXT UNIQUE NOT NULL,
    phone           TEXT,
    location        TEXT,
    linkedin_url    TEXT,
    github_url      TEXT,
    portfolio_url   TEXT,
    resume_raw      TEXT,           -- extracted plain text
    resume_structured JSONB,        -- parsed sections: experience, skills, education, projects
    identity_profile JSONB,         -- AI-extracted identity: strengths, trajectory, voice
    skills          TEXT[],
    years_experience FLOAT,
    target_roles    TEXT[],
    target_companies TEXT[],
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

-- ─── Applications ─────────────────────────────────────────────────────────────
CREATE TABLE applications (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    candidate_id    UUID REFERENCES candidates(id),
    job_id          UUID REFERENCES jobs(id),
    status          TEXT NOT NULL DEFAULT 'discovered',
    -- discovered → applied → replied → interviewing → offered → rejected → ghosted
    tailored_resume TEXT,
    resume_version  INT DEFAULT 1,
    ats_score       FLOAT,
    authenticity_score FLOAT,
    recruiter_score FLOAT,
    interview_probability FLOAT,
    applied_at      TIMESTAMPTZ,
    last_activity   TIMESTAMPTZ,
    notes           TEXT,
    metadata        JSONB,
    created_at      TIMESTAMPTZ DEFAULT now(),
    updated_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_applications_status ON applications(status);
CREATE INDEX idx_applications_candidate ON applications(candidate_id);

-- ─── Outreach ─────────────────────────────────────────────────────────────────
CREATE TABLE outreach (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    application_id  UUID REFERENCES applications(id),
    candidate_id    UUID REFERENCES candidates(id),
    recipient_name  TEXT,
    recipient_email TEXT,
    recipient_role  TEXT,
    channel         TEXT,           -- email, linkedin
    subject         TEXT,
    body            TEXT,
    personalization_signals JSONB,  -- what signals were used
    sent_at         TIMESTAMPTZ,
    opened_at       TIMESTAMPTZ,
    replied_at      TIMESTAMPTZ,
    status          TEXT DEFAULT 'drafted',
    created_at      TIMESTAMPTZ DEFAULT now()
);

-- ─── Embeddings ───────────────────────────────────────────────────────────────
CREATE TABLE embeddings (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    entity_type     TEXT NOT NULL,  -- job, candidate, company, resume_version
    entity_id       UUID NOT NULL,
    embedding_model TEXT NOT NULL,  -- bge-base-en-v1.5, nomic-embed-text, ...
    vector          vector(768),    -- adjust dim per model
    chunk_text      TEXT,           -- source text that was embedded
    chunk_index     INT DEFAULT 0,
    created_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_embeddings_entity ON embeddings(entity_type, entity_id);
CREATE INDEX idx_embeddings_vector ON embeddings
    USING ivfflat (vector vector_cosine_ops) WITH (lists = 100);

-- ─── Raw Payloads ─────────────────────────────────────────────────────────────
CREATE TABLE raw_payloads (
    id              UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    source          TEXT NOT NULL,
    source_id       TEXT,
    payload         JSONB NOT NULL, -- exact scraped/API response
    processed       BOOLEAN DEFAULT FALSE,
    error           TEXT,
    scraped_at      TIMESTAMPTZ DEFAULT now()
);

CREATE INDEX idx_raw_payloads_processed ON raw_payloads(processed);
```

---

## Queue Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                    RabbitMQ Exchanges & Queues                   │
│                                                                  │
│  Exchange: jobs.direct                                           │
│    → Queue: jobs.raw          (scraped raw payloads)             │
│    → Queue: jobs.enrich       (needs company/jd enrichment)      │
│    → Queue: jobs.embed        (needs vector embedding)           │
│    → Queue: jobs.rank         (needs opportunity scoring)        │
│                                                                  │
│  Exchange: tailoring.direct                                      │
│    → Queue: tailoring.request (user triggered tailoring jobs)    │
│    → Queue: tailoring.score   (score existing tailored resumes)  │
│                                                                  │
│  Exchange: outreach.direct                                       │
│    → Queue: outreach.generate (generate cold emails)             │
│    → Queue: outreach.send     (send approved emails)             │
│                                                                  │
│  Dead Letter Exchange: dlx.default                               │
│    → Queue: dlq.failed        (all failed messages)              │
└──────────────────────────────────────────────────────────────────┘

Redis Usage:
  - Embedding cache:      embed:{sha256(text)} → vector bytes
  - Company intel cache:  company:{domain}     → enriched JSON (TTL 7d)
  - JD analysis cache:    jd:{fingerprint}     → analysis JSON (TTL 24h)
  - Rate limit counters:  ratelimit:{source}   → counter (TTL 60s)
  - Session state:        session:{user_id}    → Streamlit state
```

---

## AI Routing Architecture

The single most important architectural decision is **never sending raw volume to cloud APIs**.

```
                    ┌─────────────────────────────┐
                    │       AI Router              │
                    │  src/ai/router.py            │
                    └──────────────┬──────────────┘
                                   │
            ┌──────────────────────┼──────────────────────┐
            ▼                      ▼                       ▼
     TIER 1: LOCAL           TIER 2: FREE            TIER 3: CLOUD
     Ollama + GGUF           Gemini Free              Gemini Pro
     bge embeddings          (lightweight)            (complex tasks)
            │                      │                       │
     - Embedding               - Quick JD               - Final resume
     - Skill extraction          analysis                  tailoring
     - Similarity scoring      - Company                - Recruiter
     - Dedup / filter            classification           critique
     - Ranking top-N           - Feasibility            - Cold email
     - Parsing                   check                    personalization
     - Clustering                                       - Hiring intent
```

**Flow for 100 scraped jobs → 1 tailored resume:**

```
100 jobs ingested
    ↓ [local] fingerprint dedup         → discard duplicates
    ↓ [local] embedding generation      → store in pgvector
    ↓ [local] cosine similarity vs candidate profile
    ↓ [local] composite opportunity scoring
    → Top 10 selected
    ↓ [local/free-tier] JD intent analysis
    → Top 3 selected
    ↓ [Gemini] deep fit analysis + strategy generation
    → 1 job selected by candidate
    ↓ [Gemini] full resume tailoring + recruiter critique
    → Final output
```

Cost: ~3 Gemini calls for the entire pipeline, not 100.

---

## Agent Definitions

### Agent Responsibility Matrix

| Agent | Model Tier | Primary Task | Output |
|-------|-----------|-------------|--------|
| JobDiscovery | Local | Scrape, normalize, fingerprint | Canonical job records |
| CompanyResearch | Local + Gemini | Enrich company profiles | CompanyProfile |
| CandidateIdentity | Local | Extract identity, voice, trajectory | IdentityProfile |
| FitAnalysis | Local | Score candidate↔job semantic fit | FitReport |
| ResumeStrategy | Gemini | Generate tailoring strategy | StrategyPlan |
| ResumeTailoring | Gemini | Rewrite resume sections | TailoredResume |
| RecruiterCritic | Gemini | Adversarial critique pass | CritiqueReport |
| ColdEmail | Gemini | Personalized outreach | EmailDraft |
| ApplicationTracker | Local | Update application state | ApplicationRecord |
| FeedbackLearning | Local | Update scoring models | Updated weights |

---

## Core Module Code

### src/ai/router.py

```python
"""
AI Router — directs tasks to local or cloud inference based on complexity,
cost budget, and task classification.
"""
from enum import Enum
from typing import Any
from functools import lru_cache
import hashlib, json, logging

from src.ai.local_llm import OllamaClient
from src.ai.gemini_client import GeminiClient
from src.ai.cache import InferenceCache

logger = logging.getLogger(__name__)

class TaskComplexity(Enum):
    EXTRACTION   = "extraction"    # → local
    CLASSIFICATION = "classification"  # → local
    ANALYSIS     = "analysis"      # → local or free-tier
    GENERATION   = "generation"    # → cloud
    CRITIQUE     = "critique"      # → cloud

COMPLEXITY_ROUTING = {
    TaskComplexity.EXTRACTION:     "local",
    TaskComplexity.CLASSIFICATION: "local",
    TaskComplexity.ANALYSIS:       "local",
    TaskComplexity.GENERATION:     "cloud",
    TaskComplexity.CRITIQUE:       "cloud",
}

class AIRouter:
    def __init__(self, cache: InferenceCache, local: OllamaClient, cloud: GeminiClient):
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
        # Check cache first
        key = cache_key or hashlib.sha256(prompt.encode()).hexdigest()
        if cached := await self.cache.get(key):
            logger.debug(f"Cache hit for {key[:8]}")
            return cached

        tier = COMPLEXITY_ROUTING[complexity]

        try:
            if tier == "local":
                result = await self.local.generate(prompt, system=system)
            else:
                result = await self.cloud.generate(prompt, system=system)
        except Exception as e:
            logger.warning(f"Primary inference failed ({tier}): {e}, falling back")
            # Graceful degradation
            if tier == "cloud":
                result = await self.local.generate(prompt, system=system)
            else:
                raise

        await self.cache.set(key, result)
        return result
```

### src/adapters/base.py

```python
"""
Abstract adapter contract. Every job source must implement this.
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import AsyncIterator
import hashlib, json

@dataclass
class CanonicalJob:
    """Normalized job record. Source-specific data goes in raw_metadata."""
    title: str
    company_name: str
    source: str
    source_url: str
    description: str
    location: str | None = None
    remote_type: str | None = None           # remote | hybrid | onsite
    employment_type: str | None = None       # full_time | contract | internship
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
        """Deterministic dedup key — stable across re-scrapes."""
        payload = f"{self.source}:{self.source_id or self.source_url}:{self.title}"
        return hashlib.sha256(payload.encode()).hexdigest()


class AbstractJobAdapter(ABC):
    """
    Every source adapter transforms raw source data into CanonicalJob records.
    Implement scrape() as an async generator for memory efficiency.
    """
    source_name: str

    @abstractmethod
    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        """Yield canonical jobs from this source."""
        ...

    @abstractmethod
    async def health_check(self) -> bool:
        """Return True if source is reachable."""
        ...
```

### src/adapters/greenhouse.py

```python
"""
Greenhouse adapter — uses their public JSON API, no scraping needed.
Most companies expose: https://boards-api.greenhouse.io/v1/boards/{company}/jobs
"""
import httpx
import logging
from datetime import datetime
from typing import AsyncIterator
from src.adapters.base import AbstractJobAdapter, CanonicalJob

logger = logging.getLogger(__name__)

class GreenhouseAdapter(AbstractJobAdapter):
    source_name = "greenhouse"
    BASE = "https://boards-api.greenhouse.io/v1/boards/{board}/jobs"

    def __init__(self, boards: list[str], http_client: httpx.AsyncClient):
        self.boards = boards     # e.g. ["stripe", "figma", "notion"]
        self.http = http_client

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for board in self.boards:
            url = self.BASE.format(board=board)
            try:
                r = await self.http.get(url, timeout=10)
                r.raise_for_status()
                data = r.json()
                for job in data.get("jobs", []):
                    yield self._transform(job, board)
            except Exception as e:
                logger.error(f"Greenhouse {board}: {e}")

    def _transform(self, raw: dict, board: str) -> CanonicalJob:
        location = raw.get("location", {}).get("name", "")
        return CanonicalJob(
            title=raw["title"],
            company_name=board.capitalize(),
            source=self.source_name,
            source_url=raw.get("absolute_url", ""),
            source_id=str(raw.get("id")),
            description=raw.get("content", ""),
            location=location,
            remote_type="remote" if "remote" in location.lower() else None,
            posted_at=datetime.fromisoformat(raw["updated_at"].replace("Z", "+00:00"))
                      if raw.get("updated_at") else None,
            company_domain=f"{board}.com",
            raw_metadata=raw,
        )

    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self.BASE.format(board="stripe"), timeout=5)
            return r.status_code == 200
        except:
            return False
```

### src/adapters/lever.py

```python
"""
Lever adapter — public postings JSON API.
Endpoint: https://api.lever.co/v0/postings/{company}?mode=json
"""
import httpx, logging
from datetime import datetime, timezone
from typing import AsyncIterator
from src.adapters.base import AbstractJobAdapter, CanonicalJob

logger = logging.getLogger(__name__)

class LeverAdapter(AbstractJobAdapter):
    source_name = "lever"
    BASE = "https://api.lever.co/v0/postings/{company}?mode=json"

    def __init__(self, companies: list[str], http_client: httpx.AsyncClient):
        self.companies = companies
        self.http = http_client

    async def scrape(self, **kwargs) -> AsyncIterator[CanonicalJob]:
        for company in self.companies:
            url = self.BASE.format(company=company)
            try:
                r = await self.http.get(url, timeout=10)
                r.raise_for_status()
                for posting in r.json():
                    yield self._transform(posting, company)
            except Exception as e:
                logger.error(f"Lever {company}: {e}")

    def _transform(self, raw: dict, company: str) -> CanonicalJob:
        cats = raw.get("categories", {})
        return CanonicalJob(
            title=raw.get("text", ""),
            company_name=company.capitalize(),
            source=self.source_name,
            source_url=raw.get("hostedUrl", ""),
            source_id=raw.get("id"),
            description=raw.get("descriptionPlain", ""),
            location=cats.get("location"),
            remote_type=cats.get("commitment", "").lower() or None,
            seniority=cats.get("level"),
            posted_at=datetime.fromtimestamp(raw["createdAt"] / 1000, tz=timezone.utc)
                      if raw.get("createdAt") else None,
            company_domain=f"{company}.com",
            raw_metadata=raw,
        )

    async def health_check(self) -> bool:
        try:
            r = await self.http.get(self.BASE.format(company="figma"), timeout=5)
            return r.status_code in (200, 404)
        except:
            return False
```

### src/ingestion/pipeline.py

```python
"""
Async ingestion pipeline. Runs all adapters concurrently, deduplicates,
publishes to queue for downstream enrichment.
"""
import asyncio, logging
from src.adapters.base import AbstractJobAdapter, CanonicalJob
from src.ingestion.deduplicator import Deduplicator
from src.queues.publisher import QueuePublisher
from src.database.repositories.job_repo import JobRepository

logger = logging.getLogger(__name__)

class IngestionPipeline:
    def __init__(
        self,
        adapters: list[AbstractJobAdapter],
        deduplicator: Deduplicator,
        publisher: QueuePublisher,
        job_repo: JobRepository,
    ):
        self.adapters = adapters
        self.deduplicator = deduplicator
        self.publisher = publisher
        self.job_repo = job_repo

    async def run(self) -> dict[str, int]:
        stats = {a.source_name: 0 for a in self.adapters}
        tasks = [self._drain_adapter(a, stats) for a in self.adapters]
        await asyncio.gather(*tasks, return_exceptions=True)
        logger.info(f"Ingestion complete: {stats}")
        return stats

    async def _drain_adapter(self, adapter: AbstractJobAdapter, stats: dict):
        try:
            async for job in adapter.scrape():
                if await self.deduplicator.is_duplicate(job.fingerprint):
                    continue
                record = await self.job_repo.upsert(job)
                await self.publisher.publish("jobs.enrich", {
                    "job_id": str(record.id),
                    "source": job.source,
                })
                await self.deduplicator.mark_seen(job.fingerprint)
                stats[adapter.source_name] += 1
        except Exception as e:
            logger.error(f"Adapter {adapter.source_name} failed: {e}")
```

### src/matching/embedder.py

```python
"""
Local embedding pipeline using sentence-transformers.
Runs entirely on GPU/CPU — zero API cost.
"""
import numpy as np
import hashlib, logging
from sentence_transformers import SentenceTransformer
from src.ai.cache import InferenceCache

logger = logging.getLogger(__name__)

class LocalEmbedder:
    """
    Uses bge-base-en-v1.5 (768-dim) by default.
    Compatible with nomic-embed-text for 768-dim pgvector columns.
    """

    def __init__(
        self,
        model_name: str = "BAAI/bge-base-en-v1.5",
        cache: InferenceCache | None = None,
        device: str = "cuda",
    ):
        logger.info(f"Loading embedding model {model_name} on {device}")
        self.model = SentenceTransformer(model_name, device=device)
        self.cache = cache
        self.dim = self.model.get_sentence_embedding_dimension()

    def embed(self, text: str) -> np.ndarray:
        key = f"embed:{hashlib.sha256(text.encode()).hexdigest()}"
        if self.cache:
            if cached := self.cache.get_sync(key):
                return np.frombuffer(cached, dtype=np.float32)

        vec = self.model.encode(
            text,
            normalize_embeddings=True,  # cosine = dot product after normalization
            show_progress_bar=False,
        )

        if self.cache:
            self.cache.set_sync(key, vec.tobytes())

        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Batch embedding is 5-10x faster than individual calls."""
        return self.model.encode(
            texts,
            normalize_embeddings=True,
            batch_size=32,
            show_progress_bar=False,
        )
```

### src/matching/ranker.py

```python
"""
Multi-signal job ranker. Combines semantic similarity with structural signals.
This is where most intelligence lives — keeps Gemini calls minimal.
"""
import numpy as np
from dataclasses import dataclass
from src.matching.embedder import LocalEmbedder

@dataclass
class JobScore:
    job_id: str
    semantic_score: float       # cosine similarity
    skill_overlap: float        # Jaccard on extracted skills
    seniority_match: float      # 0 or 1
    recency_bonus: float        # days since posted, decayed
    composite: float            # weighted final score

class JobRanker:
    WEIGHTS = {
        "semantic":    0.45,
        "skill":       0.30,
        "seniority":   0.15,
        "recency":     0.10,
    }

    def __init__(self, embedder: LocalEmbedder):
        self.embedder = embedder

    def rank(
        self,
        candidate_vec: np.ndarray,
        candidate_skills: set[str],
        candidate_seniority: str,
        jobs: list[dict],
    ) -> list[JobScore]:
        scores = []
        for job in jobs:
            job_vec = np.array(job["embedding"])
            semantic = float(np.dot(candidate_vec, job_vec))  # already normalized

            job_skills = set(job.get("tech_stack", []))
            skill_overlap = (
                len(candidate_skills & job_skills) / len(candidate_skills | job_skills)
                if candidate_skills | job_skills else 0.0
            )

            seniority_match = 1.0 if job.get("seniority") == candidate_seniority else 0.3

            days_old = job.get("days_since_posted", 30)
            recency = max(0.0, 1.0 - (days_old / 60))

            composite = (
                self.WEIGHTS["semantic"]  * semantic
                + self.WEIGHTS["skill"]   * skill_overlap
                + self.WEIGHTS["seniority"] * seniority_match
                + self.WEIGHTS["recency"] * recency
            )

            scores.append(JobScore(
                job_id=job["id"],
                semantic_score=semantic,
                skill_overlap=skill_overlap,
                seniority_match=seniority_match,
                recency_bonus=recency,
                composite=composite,
            ))

        return sorted(scores, key=lambda s: s.composite, reverse=True)
```

### src/tailoring/identity_guard.py

```python
"""
Identity Guard — the most important component in the tailoring pipeline.
Prevents fabrication, keyword stuffing, and identity erasure.
This runs BEFORE and AFTER Gemini tailoring to enforce constraints.
"""
import re
from dataclasses import dataclass
from typing import Callable

@dataclass
class IdentityProfile:
    """Extracted from candidate's original resume — the source of truth."""
    name: str
    years_experience: float
    core_skills: list[str]
    companies_worked: list[str]
    degrees: list[str]
    project_titles: list[str]
    voice_markers: list[str]  # characteristic phrases that reflect their writing style

@dataclass
class TailoringConstraints:
    """Hard rules the tailoring engine must not violate."""
    forbidden_skills: list[str]       # skills not in original resume
    forbidden_companies: list[str]    # companies not in work history
    max_experience_inflation: float   # years
    required_authenticity_markers: list[str]  # phrases that must survive


class IdentityGuard:
    def __init__(self, identity: IdentityProfile):
        self.identity = identity
        self.constraints = self._derive_constraints()

    def _derive_constraints(self) -> TailoringConstraints:
        return TailoringConstraints(
            forbidden_skills=[],  # populated dynamically vs JD
            forbidden_companies=[],
            max_experience_inflation=0.5,  # can round up to nearest 0.5yr
            required_authenticity_markers=self.identity.voice_markers[:3],
        )

    def audit(self, original: str, tailored: str, job_skills: list[str]) -> dict:
        """
        Compare original vs tailored resume.
        Returns audit report with violation flags.
        """
        issues = []

        # 1. Fabricated skills check
        original_lower = original.lower()
        for skill in job_skills:
            if skill.lower() not in original_lower:
                if skill.lower() in tailored.lower():
                    issues.append(f"FABRICATED_SKILL: {skill}")

        # 2. Company fabrication check
        tailored_companies = self._extract_companies(tailored)
        for co in tailored_companies:
            if co not in self.identity.companies_worked:
                issues.append(f"FABRICATED_COMPANY: {co}")

        # 3. Keyword density check (ATS stuffing)
        for skill in job_skills:
            count = tailored.lower().count(skill.lower())
            if count > 5:
                issues.append(f"KEYWORD_STUFFING: {skill} appears {count}x")

        # 4. Identity preservation check
        for marker in self.constraints.required_authenticity_markers:
            if marker.lower() not in tailored.lower():
                issues.append(f"IDENTITY_ERASED: '{marker}' missing")

        return {
            "passed": len(issues) == 0,
            "issues": issues,
            "fabrication_risk": sum(1 for i in issues if "FABRICATED" in i),
            "stuffing_risk": sum(1 for i in issues if "STUFFING" in i),
        }

    def _extract_companies(self, text: str) -> list[str]:
        # Simple heuristic — production version uses NER
        lines = text.split("\n")
        companies = []
        for line in lines:
            if "Inc" in line or "Corp" in line or "Ltd" in line:
                companies.append(line.strip())
        return companies
```

### src/tailoring/strategy_generator.py

```python
"""
Resume Strategy Generator.
Produces a strategy plan BEFORE handing off to Gemini for actual rewriting.
This keeps Gemini's job small, focused, and cheaper.
"""
from dataclasses import dataclass
from src.tailoring.identity_guard import IdentityProfile
from src.enrichment.jd_analyzer import JDAnalysis

@dataclass
class SectionWeight:
    section: str
    weight: float   # 0.0–1.0, influences space allocation
    action: str     # "expand" | "compress" | "reorder" | "keep"

@dataclass
class StrategyPlan:
    target_role_type: str           # backend | frontend | ml | fullstack | research
    primary_emphasis: list[str]     # top 3 skills/experiences to lead with
    secondary_emphasis: list[str]   # supporting evidence
    compress: list[str]             # sections/projects to minimize
    section_weights: list[SectionWeight]
    bullet_focus: list[str]         # verbs and outcome types to emphasize
    ats_keywords: list[str]         # exact phrases from JD that candidate actually has
    authenticity_notes: str         # what to preserve

class StrategyGenerator:
    ROLE_TYPE_SIGNALS = {
        "backend": ["api", "database", "microservice", "kafka", "redis", "postgres", "grpc"],
        "ml":      ["model", "training", "inference", "pytorch", "tensorflow", "llm", "rag"],
        "frontend":["react", "vue", "typescript", "css", "ux", "component"],
        "devops":  ["kubernetes", "docker", "ci/cd", "terraform", "helm", "aws"],
        "research":["paper", "publication", "experiment", "ablation", "arxiv"],
    }

    def generate(
        self,
        candidate: IdentityProfile,
        jd: JDAnalysis,
        fit_scores: dict[str, float],
    ) -> StrategyPlan:
        role_type = self._classify_role(jd.tech_stack + jd.required_skills)

        # Rank candidate's projects by relevance to JD
        project_scores = {
            p: fit_scores.get(p, 0.0) for p in candidate.project_titles
        }
        ranked_projects = sorted(project_scores, key=project_scores.get, reverse=True)

        primary = ranked_projects[:2]
        compress = ranked_projects[-3:] if len(ranked_projects) > 4 else []

        # Only include JD keywords that genuinely exist in candidate profile
        authentic_keywords = [
            kw for kw in jd.ats_keywords
            if any(kw.lower() in skill.lower() for skill in candidate.core_skills)
        ]

        section_weights = self._compute_section_weights(role_type)

        return StrategyPlan(
            target_role_type=role_type,
            primary_emphasis=primary,
            secondary_emphasis=ranked_projects[2:4] if len(ranked_projects) > 2 else [],
            compress=compress,
            section_weights=section_weights,
            bullet_focus=self._bullet_focus(role_type),
            ats_keywords=authentic_keywords,
            authenticity_notes=f"Preserve: {', '.join(candidate.voice_markers[:2])}",
        )

    def _classify_role(self, signals: list[str]) -> str:
        counts = {rt: 0 for rt in self.ROLE_TYPE_SIGNALS}
        for signal in [s.lower() for s in signals]:
            for role_type, keywords in self.ROLE_TYPE_SIGNALS.items():
                if any(kw in signal for kw in keywords):
                    counts[role_type] += 1
        return max(counts, key=counts.get) if any(counts.values()) else "fullstack"

    def _compute_section_weights(self, role_type: str) -> list[SectionWeight]:
        base = [
            SectionWeight("experience", 0.9, "expand"),
            SectionWeight("projects",   0.8, "reorder"),
            SectionWeight("skills",     0.7, "reorder"),
            SectionWeight("education",  0.4, "compress"),
        ]
        if role_type == "research":
            base.append(SectionWeight("publications", 1.0, "expand"))
        return base

    def _bullet_focus(self, role_type: str) -> list[str]:
        focus = {
            "backend": ["built", "scaled", "optimized", "reduced latency", "throughput"],
            "ml":      ["trained", "improved accuracy", "deployed", "reduced error"],
            "frontend":["implemented", "improved UX", "reduced load time", "accessibility"],
            "devops":  ["automated", "reduced downtime", "migrated", "provisioned"],
            "research":["published", "proposed", "demonstrated", "evaluated"],
        }
        return focus.get(role_type, ["built", "improved", "led", "designed"])
```

### src/workflows/tailoring.py

```python
"""
Resume tailoring workflow — the full pipeline from raw resume to scored output.
Orchestrates: parsing → identity extraction → strategy → tailoring → critique → scoring
"""
import logging
from crewai import Crew, Task
from src.agents.candidate_identity import build_identity_agent
from src.agents.resume_strategy import build_strategy_agent
from src.agents.resume_tailoring import build_tailoring_agent
from src.agents.recruiter_critic import build_critic_agent
from src.tailoring.identity_guard import IdentityGuard, IdentityProfile
from src.tailoring.strategy_generator import StrategyGenerator
from src.tailoring.scorer import ResumeScorer
from src.ai.router import AIRouter, TaskComplexity
from src.enrichment.jd_analyzer import JDAnalyzer

logger = logging.getLogger(__name__)

class TailoringWorkflow:
    def __init__(
        self,
        ai_router: AIRouter,
        jd_analyzer: JDAnalyzer,
        strategy_generator: StrategyGenerator,
        scorer: ResumeScorer,
    ):
        self.router = ai_router
        self.jd_analyzer = jd_analyzer
        self.strategy = strategy_generator
        self.scorer = scorer

    async def run(
        self,
        resume_text: str,
        job_description: str,
        job_id: str,
    ) -> dict:
        # Phase 1: Local analysis (no Gemini yet)
        logger.info("Phase 1: Local analysis")
        jd = await self.jd_analyzer.analyze(job_description)
        identity = await self._extract_identity(resume_text)
        guard = IdentityGuard(identity)
        plan = self.strategy.generate(identity, jd, fit_scores={})

        # Phase 2: Gemini tailoring (one call)
        logger.info("Phase 2: Gemini tailoring")
        tailored = await self.router.route(
            prompt=self._build_tailoring_prompt(resume_text, job_description, plan),
            complexity=TaskComplexity.GENERATION,
            cache_key=f"tailor:{plan.target_role_type}:{hash(resume_text[:200])}",
            system=TAILORING_SYSTEM_PROMPT,
        )

        # Phase 3: Identity audit (local, fast)
        logger.info("Phase 3: Identity audit")
        audit = guard.audit(resume_text, tailored, jd.tech_stack)
        if not audit["passed"]:
            logger.warning(f"Identity violations: {audit['issues']}")
            # Auto-fix minor violations before escalating
            tailored = await self._auto_fix(tailored, audit["issues"])

        # Phase 4: Gemini critique (one call)
        logger.info("Phase 4: Recruiter critique")
        critique = await self.router.route(
            prompt=self._build_critique_prompt(tailored, job_description),
            complexity=TaskComplexity.CRITIQUE,
        )

        # Phase 5: Local scoring
        scores = self.scorer.score(tailored, jd, identity, critique)

        return {
            "tailored_resume": tailored,
            "strategy": plan,
            "audit": audit,
            "critique": critique,
            "scores": scores,
            "job_id": job_id,
        }

    def _build_tailoring_prompt(self, resume, jd, plan) -> str:
        return f"""
You are a senior resume strategist. Tailor this resume for the job below.

STRATEGY:
- Role type: {plan.target_role_type}
- Lead with: {', '.join(plan.primary_emphasis)}
- Compress: {', '.join(plan.compress)}
- ATS keywords to include (ONLY if they match existing experience): {', '.join(plan.ats_keywords)}
- Bullet style: {', '.join(plan.bullet_focus)}
- Preserve this voice: {plan.authenticity_notes}

CONSTRAINTS (ABSOLUTE):
- Do NOT fabricate any company, skill, or project not in the original
- Do NOT keyword-stuff — max 3 mentions of any single term
- Do NOT rewrite the candidate's entire identity
- Do NOT increase claimed years of experience

RESUME:
{resume}

JOB DESCRIPTION:
{jd}

Return the tailored resume in clean markdown. No preamble.
""".strip()

    def _build_critique_prompt(self, tailored, jd) -> str:
        return f"""
You are an experienced technical recruiter reviewing this resume for the role below.
Give a brutally honest 5-point critique covering:
1. First-impression strength (0-10)
2. ATS compliance issues (list any)
3. Credibility signals (what builds trust)
4. Red flags (what raises doubt)
5. Single most impactful improvement

RESUME:
{tailored}

JOB:
{jd}
""".strip()

    async def _extract_identity(self, resume_text: str) -> IdentityProfile:
        # Use local model for extraction — no Gemini needed
        extracted = await self.router.route(
            prompt=f"Extract the following from this resume as JSON: name, years_experience, core_skills (list), companies_worked (list), degrees (list), project_titles (list)\n\nRESUME:\n{resume_text}",
            complexity=TaskComplexity.EXTRACTION,
        )
        import json, re
        try:
            data = json.loads(re.search(r'\{.*\}', extracted, re.DOTALL).group())
            return IdentityProfile(
                name=data.get("name", ""),
                years_experience=float(data.get("years_experience", 0)),
                core_skills=data.get("core_skills", []),
                companies_worked=data.get("companies_worked", []),
                degrees=data.get("degrees", []),
                project_titles=data.get("project_titles", []),
                voice_markers=[],
            )
        except:
            return IdentityProfile("", 0, [], [], [], [], [])

    async def _auto_fix(self, tailored: str, issues: list[str]) -> str:
        # Minor fix pass for keyword stuffing violations only
        # Fabrication violations must be flagged to user, not silently fixed
        return tailored

TAILORING_SYSTEM_PROMPT = """
You are a recruiter-psychology-aware resume strategist.
You write resumes that pass ATS AND impress human technical recruiters.
You never fabricate experience. You reframe real experience compellingly.
You understand that recruiters spend 6-10 seconds on first pass.
You optimize for: clarity, credibility, relevance, scannability.
"""
```

### src/tailoring/scorer.py

```python
"""
Multi-dimensional resume scoring.
All scoring is local — no API calls needed.
"""
import re
from dataclasses import dataclass
from src.enrichment.jd_analyzer import JDAnalysis
from src.tailoring.identity_guard import IdentityProfile

@dataclass
class ResumeScores:
    ats_score: float               # 0-100: keyword match, format compliance
    authenticity_score: float      # 0-100: fabrication risk inverse
    recruiter_readability: float   # 0-100: structure, scannability
    technical_credibility: float   # 0-100: depth of technical claims
    interview_probability: float   # 0-100: composite estimate
    composite: float               # weighted final

class ResumeScorer:
    def score(
        self,
        tailored: str,
        jd: JDAnalysis,
        identity: IdentityProfile,
        critique: str,
    ) -> ResumeScores:
        ats = self._ats_score(tailored, jd)
        auth = self._authenticity_score(tailored, identity)
        readability = self._readability_score(tailored)
        credibility = self._credibility_score(tailored)

        # Extract numeric signal from Gemini critique
        first_impression = self._extract_critic_score(critique)

        composite = (
            ats * 0.30
            + auth * 0.25
            + readability * 0.20
            + credibility * 0.15
            + first_impression * 0.10
        )

        return ResumeScores(
            ats_score=ats,
            authenticity_score=auth,
            recruiter_readability=readability,
            technical_credibility=credibility,
            interview_probability=composite * 0.85,  # conservative estimate
            composite=composite,
        )

    def _ats_score(self, resume: str, jd: JDAnalysis) -> float:
        resume_lower = resume.lower()
        matched = sum(1 for kw in jd.ats_keywords if kw.lower() in resume_lower)
        base = (matched / len(jd.ats_keywords) * 100) if jd.ats_keywords else 50.0

        # Penalty for ATS-hostile patterns
        penalties = 0
        if re.search(r'<table', resume): penalties += 10
        if re.search(r'\|.*\|.*\|', resume): penalties += 5  # markdown tables
        return max(0.0, base - penalties)

    def _authenticity_score(self, resume: str, identity: IdentityProfile) -> float:
        score = 100.0
        # Check if core companies still present
        for co in identity.companies_worked:
            if co.lower() not in resume.lower():
                score -= 15
        # Check reasonable experience claims
        # (simplified — production version uses NLP)
        return max(0.0, score)

    def _readability_score(self, resume: str) -> float:
        score = 70.0
        lines = resume.split("\n")
        bullet_lines = [l for l in lines if l.strip().startswith(("•", "-", "*"))]
        if len(bullet_lines) > 5: score += 10
        if any("•" in l and len(l) < 20 for l in lines): score -= 5  # too short bullets
        long_bullets = [l for l in bullet_lines if len(l) > 200]
        score -= len(long_bullets) * 3
        return min(100.0, max(0.0, score))

    def _credibility_score(self, resume: str) -> float:
        score = 50.0
        # Quantified achievements
        numbers = re.findall(r'\d+[%x]|\d+\s*(ms|TB|GB|K|M)', resume)
        score += min(30.0, len(numbers) * 5)
        # Action verbs
        strong_verbs = ["built", "scaled", "optimized", "led", "designed", "reduced", "improved"]
        for v in strong_verbs:
            if v in resume.lower(): score += 3
        return min(100.0, score)

    def _extract_critic_score(self, critique: str) -> float:
        match = re.search(r'(\d+)\s*/\s*10', critique)
        return float(match.group(1)) * 10 if match else 60.0
```

### src/database/connection.py (async, production-grade)

```python
"""
Async PostgreSQL connection with pgvector support.
Uses SQLAlchemy 2.0 async engine.
"""
from contextlib import asynccontextmanager
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from src.utils.config import Settings

settings = Settings()

engine = create_async_engine(
    settings.database_url,              # postgresql+asyncpg://...
    pool_size=10,
    max_overflow=20,
    pool_pre_ping=True,
    echo=settings.debug,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)

class Base(DeclarativeBase):
    pass

@asynccontextmanager
async def get_session() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
```

### src/api/main.py

```python
"""
FastAPI application entry point.
"""
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from src.api.routes import jobs, candidates, tailoring, applications, outreach
from src.api.middleware import RequestIDMiddleware
from src.database.connection import engine, Base

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield

app = FastAPI(
    title="Job Acquisition OS",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(CORSMiddleware, allow_origins=["*"])
app.add_middleware(RequestIDMiddleware)

app.include_router(jobs.router,         prefix="/api/v1/jobs")
app.include_router(candidates.router,   prefix="/api/v1/candidates")
app.include_router(tailoring.router,    prefix="/api/v1/tailoring")
app.include_router(applications.router, prefix="/api/v1/applications")
app.include_router(outreach.router,     prefix="/api/v1/outreach")

@app.get("/health")
async def health(): return {"status": "ok"}
```

### src/outreach/personalizer.py

```python
"""
Cold email personalizer. The goal is to NOT sound like a cold email.
Uses company intelligence to construct genuine, specific outreach.
"""
from dataclasses import dataclass
from src.ai.router import AIRouter, TaskComplexity

@dataclass
class PersonalizationSignals:
    company_name: str
    recent_news: str | None       # from web scraping
    tech_stack: list[str]
    engineering_blog_reference: str | None
    recruiter_name: str | None
    recruiter_role: str | None
    candidate_specific_connection: str  # why THIS candidate for THIS company
    job_title: str

class EmailPersonalizer:
    def __init__(self, router: AIRouter):
        self.router = router

    async def generate(
        self,
        signals: PersonalizationSignals,
        candidate_summary: str,
    ) -> dict:
        prompt = self._build_prompt(signals, candidate_summary)
        email = await self.router.route(
            prompt=prompt,
            complexity=TaskComplexity.GENERATION,
            cache_key=None,  # emails must never be cached — always fresh
        )
        return {
            "subject": self._extract_subject(email),
            "body": self._extract_body(email),
            "personalization_signals": signals.__dict__,
        }

    def _build_prompt(self, s: PersonalizationSignals, candidate: str) -> str:
        news_ref = f"I noticed {s.recent_news}. " if s.recent_news else ""
        blog_ref = f"Your post on {s.engineering_blog_reference} resonated with me. " if s.engineering_blog_reference else ""

        return f"""
Write a cold email from this candidate to the hiring team at {s.company_name}.

RULES:
- Do NOT open with "I hope this email finds you well"
- Do NOT use "I came across your posting"
- Reference something SPECIFIC about the company (provided below)
- Maximum 150 words for the body
- Sound like a human, not a template
- One specific connection between candidate's work and company's work

COMPANY SIGNALS:
- Recent: {news_ref}
- Engineering: {blog_ref}
- Tech stack they use: {', '.join(s.tech_stack[:4])}
- Role: {s.job_title}

CANDIDATE SUMMARY:
{candidate}

SPECIFIC CONNECTION:
{s.candidate_specific_connection}

Output format:
SUBJECT: [subject line]
---
[email body]
""".strip()

    def _extract_subject(self, text: str) -> str:
        for line in text.split("\n"):
            if line.startswith("SUBJECT:"):
                return line.replace("SUBJECT:", "").strip()
        return "Regarding the opening at your team"

    def _extract_body(self, text: str) -> str:
        parts = text.split("---", 1)
        return parts[1].strip() if len(parts) > 1 else text
```

### src/utils/config.py

```python
"""
Centralized configuration using Pydantic Settings.
Single source of truth for all environment variables.
"""
from pydantic_settings import BaseSettings
from pydantic import Field

class Settings(BaseSettings):
    # Database
    database_url: str = Field(..., env="DATABASE_URL")
    # postgresql+asyncpg://user:pass@localhost:5432/jobos

    # Redis
    redis_url: str = Field("redis://localhost:6379/0", env="REDIS_URL")

    # RabbitMQ
    rabbitmq_url: str = Field("amqp://guest:guest@localhost/", env="RABBITMQ_URL")

    # AI — Cloud
    gemini_api_key: str = Field(..., env="GEMINI_API_KEY")
    gemini_model: str = Field("gemini-2.0-flash", env="GEMINI_MODEL")

    # AI — Local
    ollama_base_url: str = Field("http://localhost:11434", env="OLLAMA_BASE_URL")
    ollama_model: str = Field("qwen2.5:7b-instruct", env="OLLAMA_MODEL")

    # Embeddings
    embedding_model: str = Field("BAAI/bge-base-en-v1.5", env="EMBEDDING_MODEL")
    embedding_device: str = Field("cuda", env="EMBEDDING_DEVICE")

    # Scraping
    playwright_headless: bool = Field(True)
    scraper_throttle_ms: int = Field(2000)  # ms between requests per domain

    # App
    debug: bool = Field(False)
    secret_key: str = Field(..., env="SECRET_KEY")

    class Config:
        env_file = ".env"
        case_sensitive = False
```

---

## docker-compose.yml

```yaml
version: "3.9"

services:
  db:
    image: pgvector/pgvector:pg16
    environment:
      POSTGRES_DB: jobos
      POSTGRES_USER: jobos
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - pgdata:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    command: redis-server --maxmemory 512mb --maxmemory-policy allkeys-lru
    ports:
      - "6379:6379"

  rabbitmq:
    image: rabbitmq:3.13-management
    environment:
      RABBITMQ_DEFAULT_USER: jobos
      RABBITMQ_DEFAULT_PASS: ${RABBITMQ_PASSWORD}
    ports:
      - "5672:5672"
      - "15672:15672"  # management UI

  api:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    environment:
      DATABASE_URL: postgresql+asyncpg://jobos:${DB_PASSWORD}@db:5432/jobos
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://jobos:${RABBITMQ_PASSWORD}@rabbitmq/
      GEMINI_API_KEY: ${GEMINI_API_KEY}
      OLLAMA_BASE_URL: http://host.docker.internal:11434  # Ollama runs on host GPU
    ports:
      - "8000:8000"
    depends_on: [db, redis, rabbitmq]

  ingestion_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: python -m src.queues.workers.ingestion_worker
    environment:
      DATABASE_URL: postgresql+asyncpg://jobos:${DB_PASSWORD}@db:5432/jobos
      REDIS_URL: redis://redis:6379/0
      RABBITMQ_URL: amqp://jobos:${RABBITMQ_PASSWORD}@rabbitmq/
    depends_on: [db, redis, rabbitmq]
    deploy:
      replicas: 2

  embedding_worker:
    build:
      context: .
      dockerfile: docker/Dockerfile.worker
    command: python -m src.queues.workers.embedding_worker
    environment:
      DATABASE_URL: postgresql+asyncpg://jobos:${DB_PASSWORD}@db:5432/jobos
      OLLAMA_BASE_URL: http://host.docker.internal:11434
    deploy:
      replicas: 1  # GPU-bound, 1 is fine

  ui:
    build:
      context: .
      dockerfile: docker/Dockerfile.api
    command: streamlit run src/ui/app.py --server.port 8501
    ports:
      - "8501:8501"
    depends_on: [api]

volumes:
  pgdata:
```

---

## Migration Plan (from current codebase)

### Week 1 — Foundation

| Day | Task |
|-----|------|
| 1-2 | Set up PostgreSQL + pgvector + Redis + RabbitMQ via docker-compose |
| 3 | Implement database models, run initial migrations via Alembic |
| 4 | Build `LocalEmbedder` + cache layer, verify on GPU |
| 5 | Port existing `queries.py` stubs into real ORM repositories |

### Week 2 — Core Pipeline

| Day | Task |
|-----|------|
| 6-7 | Implement Greenhouse + Lever adapters (API-based, zero Playwright) |
| 8 | Build `IngestionPipeline`, test deduplication |
| 9 | Build `AIRouter` with Ollama local model + Gemini fallback |
| 10 | Test end-to-end: scrape → embed → rank for a candidate |

### Week 3 — Tailoring Engine

| Day | Task |
|-----|------|
| 11 | Port `agents.py` extraction logic into `tailoring/parser.py` |
| 12-13 | Build `IdentityGuard` + `StrategyGenerator` |
| 14 | Build `TailoringWorkflow` — test against existing personal resume |
| 15 | Implement `ResumeScorer`, validate scores are sensible |

### Week 4 — API + UI

| Day | Task |
|-----|------|
| 16-17 | FastAPI routes for tailoring + job discovery |
| 18 | Refactor `streamlit_app.py` into multi-page Streamlit under `src/ui/` |
| 19 | Cold email pipeline |
| 20 | Application tracker |

---

## Security Considerations

1. **API Keys**: Never in code. Pydantic Settings + `.env` + Docker secrets in production.
2. **Resume PII**: Encrypt `resume_raw` at rest (PostgreSQL column-level encryption or application-layer AES-256).
3. **Scraping rate limits**: Per-domain throttle in Redis (`INCR` + `EXPIRE`). Respect `robots.txt`.
4. **Playwright isolation**: Run in sandboxed container, not alongside the API process.
5. **Auth on FastAPI**: Add JWT (python-jose) before exposing to internet. Currently assumes single-user local tool.
6. **Gemini prompt injection**: All user-supplied content (JD, resume) must be wrapped in explicit delimiters in prompts — never interpolated raw.

---

## Scalability Considerations

| Bottleneck | Solution |
|-----------|---------|
| Embedding 10K jobs | Batch in embedding_worker, 32 at a time, GPU parallel |
| Playwright scraping LinkedIn | Rotating residential proxies + session pool |
| Gemini rate limits | Redis token bucket counter, graceful degradation to Ollama |
| pgvector slow on 1M+ rows | IVFFlat index with `lists=200`, HNSW for higher recall |
| Streamlit concurrent users | Move to FastAPI + React when multi-user needed |
| Resume parsing at scale | Cache parsed structured output by SHA-256 of raw bytes |

---

## Recommended Frontend Migration Path

Streamlit is adequate for MVP (single user). When you need multi-user:

1. Keep FastAPI backend as-is — it's already production-ready
2. Replace Streamlit with **Next.js 14 + Tailwind**
3. Use FastAPI's WebSocket support for streaming tailoring progress
4. Streamlit remains viable for internal tools / personal use indefinitely

---

## Summary of Architectural Wins vs Current State

| Dimension | Current | New |
|-----------|---------|-----|
| Coupling | UI + AI + DB in one file | Strict layer separation |
| AI cost | Every action → Gemini | Local-first, Gemini for final 3% |
| Deduplication | None | SHA-256 fingerprint |
| Schema | SQLite stub | PostgreSQL + pgvector + JSONB |
| Matching | None | BGE embeddings + multi-signal ranker |
| Identity preservation | None | IdentityGuard + audit |
| Resume scoring | None | 5-dimensional local scorer |
| Scalability | Single script | Async workers + queues |
| Observability | print statements | Structured logging + request IDs |
| Adaptability | Hardcoded Gemini | Local fallback, model routing |
