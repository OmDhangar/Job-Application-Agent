# Codebase Feature Coupling, Execution Flow, and Testing Guide

## 1) High-Level Architecture Map

- **Entry points**:
  - FastAPI (`src/api/main.py`) exposes CRUD + semantic endpoints and composes routers.
  - Streamlit UI (`src/ui/...`) likely triggers service/workflow methods for interactive flows.
- **Core layers**:
  - API routes → Service layer (`src/services/*`) → Workflows (`src/workflows/*`) → Domain engines (`src/tailoring`, `src/matching`, `src/enrichment`, `src/outreach`) → Data/infra (`src/database`, `src/queues`, `src/ai`).
- **Cross-cutting couplings**:
  - AI routing (`src/ai/router.py`) is shared by tailoring/enrichment.
  - Repositories and SQLAlchemy session model bind API + services to DB schema.
  - Queue publisher/worker contracts tie ingestion lifecycle to enrichment/embedding.

---

## 2) Feature-by-Feature Coupled Components

## Feature A: Job Discovery + Semantic Matching

### Primary components
- API: `src/api/routes/jobs.py` (`/search`, listing, detail).
- Service: `src/services/job_service.py` (`find_matching_jobs`).
- Matching engine: `src/matching/embedder.py`, `src/matching/semantic_search.py`, `src/matching/ranker.py`.
- DB model/repo dependencies: `src/database/models/jobs.py`, repository + pgvector-backed query path.

### Coupling profile
- **Tight coupling**: `JobService` assumes specific return shape from `SemanticJobSearch.find_similar` (expects fields like `id`, `title`, vectors/scores).
- **Medium coupling**: ranking logic depends on tokenized candidate skills strategy; API `/search` currently derives skills from query token split, which couples API behavior to ranker assumptions.
- **Infra coupling**: semantic search relies on vector availability and extension setup from startup lifecycle.

### Risk points
- `print`-style diagnostics in API route suggest production observability inconsistency (logger vs print).
- Contract drift risk between DB query output keys and ranker/job merging logic.

---

## Feature B: Resume Tailoring Pipeline

### Primary components
- Service facade: `src/services/tailoring_service.py`.
- Orchestrator: `src/workflows/tailoring.py`.
- Domain modules: parser, strategy generator, identity guard, scorer, LaTeX compiler.
- AI clients via router: local + Gemini path.

### Coupling profile
- **Intentional orchestration coupling** inside `TailoringWorkflow.run`:
  - JD analyzer output structure feeds strategy + identity audit skill checks.
  - Strategy plan fields directly embedded into prompt templates.
  - Output format drives both prompt construction and compile stage.
- **Data coupling**:
  - `TailoringService` dynamically imports parser and depends on `extract()` returning `(plain_text, raw_latex)` tuple.
- **External coupling**:
  - Gemini/LLM availability and pdflatex availability influence deterministic behavior.

### Risk points
- Many sequential stages increase blast radius for failures (AI parse/compile/scoring path).
- Prompt contracts are implicit Python string templates (harder to version-test).

---

## Feature C: End-to-End Job Acquisition Workflow

### Primary components
- Orchestrator: `src/workflows/job_acquisition.py`.
- Services: `JobService`, `TailoringService`, `OutreachService`.
- Repositories: candidate/application repos.
- Tracker: `src/tracking/tracker.py`.

### Coupling profile
- **High coupling by design**: workflow is coordinator for all bounded contexts.
- **Runtime coupling**:
  - Depends on candidate shape fields (`resume_raw`, `skills`, `years_experience`).
  - Tailoring output schema drives application repo update payload.
  - Outreach generation depends on application records created earlier.

### Risk points
- Try/except in per-job loop swallows failures into logs, potentially obscuring partial-data consistency.
- No explicit transactional boundary across create/update + downstream outreach.

---

## Feature D: Job Ingestion + Enrichment Queue Hand-off

### Primary components
- Orchestrator: `src/ingestion/pipeline.py`.
- Adapters: `src/adapters/*` via `AbstractJobAdapter`.
- Dedup: Redis-backed deduplicator.
- Persistence + publish: job repo + queue publisher.

### Coupling profile
- **Protocol coupling**:
  - Adapter `scrape()` async generator must emit canonical jobs with `fingerprint`, `source`.
- **Temporal coupling**:
  - Order matters: dedup check → upsert → publish enrichment task → mark seen.
- **Operational coupling**:
  - Redis/queue availability directly affects pipeline throughput and exactly-once behavior.

### Risk points
- `asyncio.gather(return_exceptions=True)` can keep pipeline alive while adapters fail; good for resilience, but needs monitoring/alerts.
- At-least-once semantics likely; duplicate enrichment jobs possible on edge failures between upsert/publish/mark_seen.

---

## 3) Execution Flow Tracing (How to Debug Each Feature)

### A. Trace Job Search Request
1. `POST /api/v1/jobs/search` accepts `JobSearchRequest`.
2. Embedding generated from query.
3. Vector search fetches candidate jobs.
4. Ranker computes composite score.
5. Route maps scored IDs back to job payload, returns top-k.

**Debug checkpoints**
- Validate embedding shape + numeric range.
- Snapshot raw vector-search rows count before ranking.
- Assert id bijection between scored results and raw jobs.

### B. Trace Tailoring Request
1. Upload resume bytes + filename enters `TailoringService.tailor`.
2. Parser extracts plain text and optional LaTeX source.
3. `TailoringWorkflow.run` performs:
   - JD analyze → identity extract → strategy generate.
   - LLM tailoring.
   - Identity audit.
   - Recruiter critique.
   - Optional LaTeX compile.
   - Scoring.
4. Returns consolidated dict with resume, audit, critique, scores, pdf flag.

**Debug checkpoints**
- Persist intermediate artifacts (plan, prompts, audit output) with request IDs.
- Capture compile logs on LaTeX failures.
- Distinguish model failures vs business-rule failures in error types.

### C. Trace Full Acquisition Run
1. Candidate loaded by ID.
2. Matching called (top_k multiplied for rerank headroom).
3. Iterative tailoring per job + application create/update.
4. Outreach email generation per tailored application.
5. Aggregated summary returned.

**Debug checkpoints**
- Correlate each job ID across stages in structured logs.
- Track partial success ratio (matched vs tailored vs emailed).
- Verify application metadata schema in repo updates.

### D. Trace Ingestion Cycle
1. Pipeline spawns `_drain` per adapter concurrently.
2. For each scraped job: dedup check.
3. Upsert DB record.
4. Publish enrichment event.
5. Mark fingerprint seen.
6. Increment per-source stats.

**Debug checkpoints**
- Inspect dedup hit-rate by source.
- Measure per-adapter exception rates.
- Validate queue publish acknowledgements.

---

## 4) Testing Strategy by Feature

## Unit tests (fast, deterministic)
- **Matching**:
  - Ranker scoring invariants (monotonicity, bounds).
  - Merge logic preserves sort order and does not drop valid IDs.
- **Tailoring domain modules**:
  - Parser extraction matrix by filetype.
  - IdentityGuard catches fabricated entities.
  - StrategyGenerator deterministic output given fixture identity/JD.
  - Scorer bounds and weighting checks.
- **Ingestion**:
  - `_drain` with fake adapter/repo/publisher to assert call order.

## Integration tests (real component boundaries)
- Existing integration for tailoring should be extended with:
  - Failure-mode test where Gemini/local model unavailable.
  - Compile-failure path test asserting safe fallback metadata.
- API integration:
  - Spin test DB + seed vectors, then exercise `/jobs/search` and assert rank contract.
- Ingestion integration:
  - Use ephemeral Redis + fake queue to verify dedup + publish semantics.

## Contract tests
- Define typed schema contracts for:
  - `SemanticJobSearch.find_similar` return payload.
  - Tailoring workflow response shape used by `JobAcquisitionWorkflow`.
  - Queue message envelope (`jobs.enrich`) and worker expectations.

## End-to-end smoke tests
- Run minimal “golden path”:
  - ingest sample jobs → search → tailor one resume → draft one outreach email.
- Assert both DB side effects and API/UI-visible outputs.

---

## 5) Design & Coupling Improvement Recommendations

- **Stabilize contracts**:
  - Introduce pydantic/dataclass DTOs between service/workflow boundaries instead of dict-heavy payloads.
- **Reduce orchestration fragility**:
  - Split `TailoringWorkflow.run` into explicit stage methods returning typed stage results.
- **Observability**:
  - Replace `print` diagnostics in routes with structured logs and request/job correlation IDs.
- **Error taxonomy**:
  - Distinguish `ExternalDependencyError` (LLM/Redis/queue) from `DomainValidationError` for cleaner retries.
- **Transactional consistency**:
  - Wrap application create/update sequence in transaction; define compensating actions when tailoring succeeds but DB update fails.
- **Test architecture**:
  - Move LLM-dependent tests behind explicit markers and provide “simulated model” fixtures for CI determinism.

---

## 6) Practical Debugging Best Practices for This Repo

- Start with **one feature slice** and follow it end-to-end (route → service → workflow → domain modules → repo).
- Add **structured logging context** early (`request_id`, `candidate_id`, `job_id`, `stage`).
- Keep “golden fixtures” for resumes/JDs so scoring regressions are diffable.
- Add **idempotency keys** for queue publish flows where possible.
- Track latency per stage (embedding, search, LLM generate, compile, score) to detect bottlenecks and flaky dependencies.

