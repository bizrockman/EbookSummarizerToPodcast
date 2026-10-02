# Two-Tier SaaS Draft (FastAPI + Next.js)

## 1) Current State (Codebase Check)

You already have strong backend foundations:
- FastAPI app with routers, auth, queue jobs, and DB models (`api/main.py`, `api/routers/*`).
- Async processing with Huey workers (`api/tasks/audiobook_tasks.py`).
- DAO pattern for AI providers (`api/daos/llm_dao.py`, `api/daos/tts_dao.py`).
- Cost tracking and job persistence (`jobs`, `cost_logs`, `job_assets` tables).

Main gaps for your target:
- Summary + translated audiobook pipelines are still `501` in API.
- No web frontend tier yet (Streamlit is still primary UX).
- Observability existed, but run timeline history was missing as first-class API data.
- DB abstraction existed only partly; business logic still had direct SQLAlchemy usage.

## 2) Target Two-Tier Architecture

### Tier A: API + Worker Platform (FastAPI)
- `api-gateway`: authentication, request validation, job creation.
- `pipeline-worker`: chapter analysis, summarize, translate, TTS, audio combine.
- `storage`: book files, chapter artifacts, final audio (local now; S3-compatible later).
- `tracking`: jobs, costs, events, assets, provider metadata, durations.

### Tier B: Product UI (Next.js + Tailwind + React)
- Dashboard: books, jobs, costs, durations, failures.
- Job detail: timeline, stage-level metrics, asset downloads, logs.
- Pipeline builder UI:
  - language selection
  - summarization level (none/light/medium/aggressive)
  - naturalness controls (style prompt, pacing, voice profile)
  - provider overrides (LLM/TTS)

Suggested runtime:
- Frontend: Next.js App Router, Tailwind, React Query, optional Bun for local dev speed.
- Backend: keep FastAPI + Huey now; can later move queue backend to Redis/Celery/Temporal.

## 3) DAO Strategy (Provider + Database)

Keep DAOs in two dimensions:
- AI provider DAOs: LLM/TTS (already present).
- Persistence DAOs: Job tracking and data access for storage/backend swap.

Required DAO interfaces:
- `DatabaseDao`: users, books, billing aggregates.
- `JobTrackingDao`: jobs/events/cost logs/assets.
- `BlobStorageDao`: upload/download URLs, retention, deletion.
- `UsageAnalyticsDao`: reporting queries for dashboard and billing.

Implementations:
- `SQLite*Dao` for local dev.
- `SQLAlchemy*Dao` for MySQL/Postgres.
- `Supabase*Dao` or `Appwrite*Dao` adapters later.

## 4) Observability and Cost Tracking Requirements

Track per job and per stage:
- timestamps: queued, started, stage-start, stage-end, completed/failed.
- status + progress.
- provider/model/voice configuration.
- token/character usage and exact USD cost.
- file artifact metadata (size, duration, storage location).

Expose in API:
- `GET /jobs/{job_id}`
- `GET /jobs/{job_id}/result`
- `GET /jobs/{job_id}/events` (timeline for frontend and debugging)

## 5) Summarization/Naturalness Product Direction

Pipeline stages:
1. EPUB normalize + chapter extraction
2. optional chapter classification (content vs supplement)
3. optional summarization
4. optional translation
5. TTS render
6. post-processing (pause injection, loudness normalization, combine)

To reduce robotic output:
- speech-aware rewriting prompt before TTS (short sentences, oral style).
- SSML-like pause markers or punctuation tuning.
- optional style profiles: `neutral`, `warm narrator`, `teacher`.

To avoid deleting important plain-language concepts:
- replace single "word surprise" heuristic with hybrid scoring:
  - semantic salience
  - entity retention
  - chapter objective coverage
  - configurable minimum detail floor

## 6) Phased Migration Plan

### Phase 1 (now)
- Keep FastAPI/Huey.
- Finalize DAO boundaries.
- Add full event timeline and stage observability.
- Keep Streamlit for internal usage.

### Phase 2
- Build Next.js frontend against current API.
- Add polling + live status pages for jobs.
- Add detailed cost and timeline visualization.

### Phase 3
- Implement missing pipelines:
  - `/audiobook/translated`
  - `/audiobook/summary`
  - `/audiobook/summary-translated`
- Add quality controls (summarization strictness + naturalness profiles).

### Phase 4 (SaaS)
- Multi-tenant auth (JWT/OAuth).
- Stripe billing and quotas.
- Object storage + signed URLs.
- Production DB (MySQL/Postgres/Supabase) via DAO adapters.

## 7) What Was Implemented In This Iteration

- Added persistent job event timeline model: `job_events`.
- Added DAO abstraction for job tracking:
  - `api/daos/job_tracking_dao.py`
- Refactored worker-side job tracking writes to DAO usage.
- Added initial queue event creation via DAO.
- Added new API endpoint for timeline:
  - `GET /jobs/{job_id}/events`

This keeps your architecture aligned with "switchable backends" instead of coupling logic to SQLite directly.
