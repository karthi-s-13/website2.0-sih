# Nigrani — AI-Powered Predictive Project Monitoring

AI-Powered Predictive Project Monitoring & Early-Warning Platform, built for **SIH 2.0 (MoSPI /
IPMD — Ministry of Statistics and Programme Implementation)**.

Nigrani identifies public infrastructure projects at risk of **cost overrun, schedule delay, or
implementation problems**, combining **point-in-time ML prediction** with a **multi-agent
reasoning layer** that explains *why* a project is at risk and *what* a monitoring authority
should review next — every claim grounded in real project data, official review reports, and
verified web sources, never fabricated.

See [`docs/`](docs/) for the full SRS, Solution Architecture, PRD, and Agentic Specification
this system was built against.

> **Development principle:** build the smallest working system first, validate it on a 5-project
> cohort, then progressively layer on intelligence, RAG, web evidence, multi-agent orchestration,
> MCP, evaluation, observability, and cost tracking. See
> [`docs/development_phases.md`](docs/development_phases.md) for the full phase plan
> (Phase 0 → Phase 18). **This repository is currently at Phase 12.**

---

## What it does

For any ingested project, ask a plain-English question — *"Will this project finish on
time?"*, *"Why is this project at risk?"*, *"What should we review next?"* — and get back an
answer built from five kinds of grounded evidence:

| Source | What it provides | LLM involved? |
|---|---|---|
| **Structured project data** | Monthly cost/progress observations, milestones, revision events | No — raw facts |
| **Deterministic health formulas** | Cost/schedule utilisation, progress-vs-expected gap, expenditure divergence, trend, anomalies | No — plain arithmetic |
| **ML cost-overrun model** | A point-in-time probability + risk tier from a pretrained LightGBM model | No — inference only |
| **Review-report RAG** | Citation-backed excerpts from official MoSPI review-report PDFs (hybrid vector + keyword search) | Only to phrase the answer around cited excerpts |
| **Web intelligence** | Trust-tiered external evidence (news, government notices, contractor/court disputes) via Tavily search | Only to extract/summarize grounded claims |

A **Coordinator agent** classifies the question's intent, resolves the project, plans which of
the above to call, runs them (in parallel where independent), and hands everything to a
**Reporting agent** that writes one short executive-summary paragraph — the *only* place an LLM
is allowed to generate prose, and only ever grounded in the facts computed above. Every
LLM-touched step has a **deterministic, still-cited fallback** if the LLM is unavailable, over
quota, or its output fails a guardrail check (e.g. an ungrounded "on track" claim contradicting
the computed schedule tier) — the system never blocks or fabricates, it degrades honestly.

---

## Architecture

```text
┌─────────────────────────┐        ┌──────────────────────────────────────────────┐
│   Next.js frontend       │  HTTP  │              FastAPI backend                  │
│  (dashboard, ARIA chat,  │◄──────►│  /api/v1/projects/*   /api/v1/analyze         │
│   AI Report Card)        │        │  /api/v1/portfolio    /api/v1/models          │
└─────────────────────────┘        └───────────────┬────────────────────────────────┘
                                                     │
                        ┌────────────────────────────┼─────────────────────────────┐
                        ▼                            ▼                             ▼
              ┌──────────────────┐         ┌──────────────────┐         ┌──────────────────┐
              │   Coordinator     │         │   Deterministic   │         │   LLM-touched     │
              │   (intent →       │────────►│   services         │────────►│   agents           │
              │   plan → execute) │         │  health / anomaly  │         │  history / RAG    │
              │                   │         │  prediction / RAG   │         │  answer / claim    │
              │  diagnosis ⇄      │         │  retrieval / web    │         │  extraction /      │
              │  intervention     │         │  search / evidence  │         │  intent / exec.    │
              └──────────────────┘         │  fusion             │         │  summary           │
                                            └─────────┬──────────┘         └─────────┬──────────┘
                                                       ▼                              ▼
                                            ┌────────────────────┐        ┌────────────────────┐
                                            │ Postgres (+pgvector)│        │  Groq (generation)  │
                                            │  LightGBM model     │        │  Gemini (embeddings)│
                                            │  Tavily (web search) │        │                     │
                                            └────────────────────┘        └────────────────────┘
```

Seven **MCP servers** additionally expose the same backend capabilities as standard
Model-Context-Protocol tools for external agent clients (Claude Desktop/Code, an MCP Inspector,
etc.) — additive, the Coordinator itself still calls every service directly in-process.

---

## Key features

- **Deterministic project health** — cost/schedule utilisation, physical-vs-expected progress
  gap, expenditure-progress divergence, recent trend, milestone health. Plain arithmetic, always
  reproducible, computed live.
- **Point-in-time ML cost-overrun prediction** — a pretrained LightGBM model scored as of any
  chosen snapshot month, never leaking future data into a past prediction.
- **Anomaly detection** — flags unusual patterns (stagnation, non-monotonic data) against a
  project's own history.
- **Project History agent** — a chronological, evidence-tagged timeline (`OBSERVED_FACT` /
  `INFERRED_TREND` / `MODEL_PREDICTION`) plus an LLM-written narrative.
- **Review-Report RAG** — PDF ingestion (PyMuPDF + OCR fallback), page-aware chunking, Gemini
  embeddings in Postgres/pgvector, hybrid (vector + keyword) retrieval with Reciprocal Rank
  Fusion, and a citation-grounding filter so a national sector-aggregate bulletin is never
  presented as if it were project-specific evidence unless it actually names the project.
- **Web Intelligence agent** — Tavily-backed search with trust-tier scoring and SSRF-safe
  source fetching.
- **Risk Diagnosis & Intervention agents** — fuse every evidence source above into one pool,
  identify ranked risk drivers, compute an overall risk score, and map each driver to a
  monitoring/review/verification recommendation — never an autonomous administrative decision.
- **Multi-agent Coordinator** — classifies question intent (14 intents), resolves the target
  project (including disambiguation when a query is ambiguous), plans and executes only the
  stages a question actually needs, and risk-triggers a deeper analysis automatically when a
  narrow query turns out to be CRITICAL/HIGH risk.
- **Portfolio ranking** — ranks every ingested project by risk score for a portfolio-wide view.
- **ARIA AI Copilot** — a chat assistant in both portfolio-wide (`/analyze`) and per-project
  (project detail page) modes, with an expandable multi-stage reasoning trace and a
  collapsible evidence-grounding panel.
- **AI Report Card** — a project-page widget that runs every available agent in parallel and
  persists the assembled report client-side.
- **MCP servers (Phase 12)** — 7 standalone servers (PAIMANA, ML, Analytics, Document, Web,
  Knowledge, Reporting) exposing the same capabilities as MCP tools.
- **Graceful degradation everywhere** — every LLM call has a deterministic, still-grounded
  fallback; every ML/RAG/web call reports genuine unavailability rather than fabricating a
  result.

---

## Repository layout

```text
backend/         FastAPI application (api, core, models, schemas, services, repositories)
frontend/        Next.js dashboard, ARIA chat, AI Report Card
agents/          Specialist agent notes (coordinator, history, health, prediction, ...)
mcp_servers/     MCP server process entrypoints (Phase 12) - server code itself lives under
                 backend/app/mcp/<name>/, mirroring backend/app/services/<domain>/
ml/              Model training, feature engineering, inference, evaluation
rag/             Review-report ingestion/retrieval pipeline notes
data/            Raw / processed / feature / validation-cohort data
evaluation/      Agent + ML evaluation suites
observability/   Tracing, metrics, logging config
cost_tracking/   LLM/tool cost attribution
security/        Auth, policies, guardrails
prompts/         Versioned agent prompts
scripts/         One-off / operational scripts (ingestion, feature build, diagnosis, coordinator)
docs/            SRS, Solution Architecture, PRD, Agentic Specification, phase plan
model/           Pretrained model artifacts (source-of-record, not modified by the app)
project/         Raw Flash Report CSVs for the validation cohort
review reprot/   Raw official review-report PDFs (source-of-record, not modified by the app)
```

---

## Tech stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI 0.115, Pydantic 2, SQLAlchemy 2, Alembic |
| Database | PostgreSQL 16 + `pgvector` (vector search, no separate vector DB service) |
| ML | LightGBM (pretrained cost-overrun model), scikit-learn, pandas |
| Text generation (LLM) | Groq (`openai/gpt-oss-20b` by default) — intent classification, RAG answers, history/claim/executive-summary narratives |
| Embeddings | Gemini (`gemini-embedding-001`) — Groq has no embeddings API |
| Web search | Tavily |
| PDF ingestion | PyMuPDF, `pytesseract` (OCR fallback) |
| Multi-agent tooling | Official `mcp` SDK (`FastMCP`) — 7 standalone MCP servers |
| Frontend | Next.js 16 (App Router, Turbopack), React 19, TypeScript, Tailwind CSS |
| Maps | Leaflet / react-leaflet |
| Cache | Redis (present in the stack, not yet load-bearing) |
| Testing | pytest, pytest-asyncio, pytest-cov |
| Lint/type-check | ruff, mypy (backend); eslint, tsc (frontend) |

---

## Prerequisites

- Python 3.12+
- Node.js 20+
- PostgreSQL 16 with the `pgvector` extension available
- Docker / Docker Compose (optional, for the full local stack)
- API keys (all optional — every feature they touch degrades gracefully without one):
  - [Groq](https://console.groq.com/) — narrative/answer/intent generation
  - [Gemini](https://ai.google.dev/) — review-report embeddings
  - [Tavily](https://tavily.com/) — web intelligence search

---

## Quick start (Docker Compose)

```bash
cp .env.example .env   # then fill in DATABASE_URL / API keys as needed
docker compose up --build
```

This starts PostgreSQL, Redis, the API, and the frontend. The vector search needed by RAG runs
inside the same PostgreSQL container via `pgvector` — no separate vector DB service.

---

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt
cp ../.env.example ../.env    # then edit as needed
alembic upgrade head
uvicorn app.main:app --reload
```

- API docs: http://localhost:8000/api/docs
- Health: http://localhost:8000/api/health
- Readiness (checks DB): http://localhost:8000/api/v1/ready

Run tests:

```bash
cd backend
pytest
```

Run a migration (once models change):

```bash
cd backend
alembic revision --autogenerate -m "message"
alembic upgrade head
```

### Frontend

```bash
cd frontend
cp .env.local.example .env.local
npm install
npm run dev
```

Visit http://localhost:3000 — the landing page pings the backend `/api/health` endpoint.

---

## Configuration

All configuration is externalized via environment variables (see `.env.example`) and loaded
through `backend/app/core/config.py` (`pydantic-settings`). **Never commit a real `.env` file**
(it's gitignored).

| Variable | Purpose | Required? |
|---|---|---|
| `DATABASE_URL` | PostgreSQL connection string (`postgresql+psycopg://...`) | Yes |
| `REDIS_URL` | Redis connection string | No (present, not yet load-bearing) |
| `SECRET_KEY` | App secret | Yes (any value for local dev) |
| `CORS_ORIGINS` | JSON list of allowed frontend origins | Yes |
| `LOG_LEVEL`, `LOG_JSON` | Logging config | No |
| `GEMINI_API_KEY`, `GEMINI_MODEL` | Review-report RAG embeddings only | No — falls back to keyword-only retrieval |
| `GROQ_API_KEY`, `GROQ_MODEL` | Text generation for every LLM-touched agent | No — falls back to deterministic templates |
| `TAVILY_API_KEY` | Web Intelligence agent search | No — falls back to reporting web evidence as unavailable |
| `NEXT_PUBLIC_API_BASE_URL` | Frontend → backend base URL | Yes (frontend) |

---

## Point-in-time discipline

This system predicts and explains project risk **as of a chosen snapshot month**, using only
data available at or before that month. Any feature, evidence, or event with a timestamp after
the snapshot must never reach a prediction — enforced starting in the feature-engineering phase
and treated as a `DATA_LEAKAGE_DETECTED` failure if violated. See
`docs/SRS_AI_Powered_Predictive_Project_Monitoring.md` sections 1, 33, and DR-005.

## Validation cohort

Five projects (under `project/`) are the initial forward-looking validation cohort — projects
whose revised cost has not yet diverged from the originally approved cost (i.e. no cost overrun
has been recorded against them yet). They are early-warning test cases, not confirmed
cost-overrun labels, and their source records are never modified by the application.

---

## Data pipeline, phase by phase

### 1 — Data ingestion

```bash
cd backend
alembic upgrade head
cd ..
python scripts/ingest_flash_reports.py
```

Profiles and ingests `data/raw/flash_reports/*.csv` (a working copy of `project/`, which stays
untouched) into `projects`, `project_monthly_observations`, `project_events`, and
`data_quality_issues`, and seeds `validation_cohort`. See `backend/app/services/ingestion/`.

### 2 — Feature store

```bash
python scripts/build_features.py
```

Computes one point-in-time feature vector per `(project_id, snapshot_month)` into
`project_monthly_features`, tagged with a versioned `feature_version`. Safe to re-run — rows are
upserted. See `backend/app/services/features/formulas.py`.

### 3 — ML prediction

```bash
python scripts/predict_validation_cohort.py
```

Runs `model/lightgbm_cost_overrun_model.pkl` (integrated as-is, not retrained) for each
validation-cohort project at its latest observed month, via
`POST /api/v1/projects/{project_id}/predict`:

```bash
curl -X POST http://localhost:8000/api/v1/projects/617069/predict \
  -H "Content-Type: application/json" -d '{"prediction_date": "2026-07-01"}'
```

The model's own custom preprocessing step isn't importable as shipped with the artifact; see
`docs/model_integration_notes.md` for exactly how `ml/pipeline/feature_engineering.py`
reconstructs it from evidence, and what remains genuine, flagged uncertainty (mainly the `kw_*`
keyword lists). `GET /api/v1/models` returns model metadata (version, training metrics).

### 4 — Project health

```bash
curl http://localhost:8000/api/v1/projects/617069/health
```

Deterministic project-health metrics — cost/schedule utilisation, physical vs. expected
progress, expenditure-progress divergence, a recent trend, and milestone health (honestly
`NOT_AVAILABLE` when the source data has no milestone fields). No ML, no LLM: plain arithmetic
in `backend/app/services/health/formulas.py`. Optional `?as_of=YYYY-MM-DD` (defaults to the
project's latest observed month).

### 6 — Project History agent

```bash
python scripts/ask_project_history.py
python scripts/ask_project_history.py --question "Why is this project risky?"
```

`GET /api/v1/projects/{project_id}/history` (optional `?question=`, defaults to *"What happened
to this project?"*, and `?as_of=`) answers with a chronological, evidence-backed `timeline`,
`major_changes`, and `historical_risk_signals` — all built deterministically in
`backend/app/services/history/timeline.py` (no LLM) — plus a `current_state` narrative written
by an LLM (`backend/app/services/history/llm.py`). Every evidence entry is tagged
`OBSERVED_FACT`, `INFERRED_TREND`, or `MODEL_PREDICTION`. If `GROQ_API_KEY` is unset, the call
fails, or the model's output violates the output guardrail (e.g. asserting a definite
overrun/no-overrun outcome), the agent transparently falls back to a deterministic template
summary (`summary_source: "DETERMINISTIC_FALLBACK"`) rather than blocking or fabricating.

### 7 — Review-Report RAG

```bash
python scripts/ingest_review_reports.py
python scripts/ask_review_evidence.py
python scripts/ask_review_evidence.py --question "Any mention of land acquisition delays?"
```

Ingests `data/raw/review_reports/*.pdf` (copied from `review reprot/`, which stays untouched):
PyMuPDF text extraction with an OCR fallback (`pytesseract`, activates automatically wherever
Tesseract is installed — degrades gracefully otherwise), page-aware chunking (a chunk never
spans two pages), Gemini embeddings (`gemini-embedding-001`, 768-dim, stored in Postgres via
`pgvector`), then hybrid retrieval (vector + keyword, combined by Reciprocal Rank Fusion) with a
deterministic keyword-boost rerank. `GET /api/v1/projects/{project_id}/review-evidence`
(optional `?question=`, defaults to *"What does the latest review report say about this
project?"*) answers via a grounded-LLM-with-guardrail pattern: every claim must cite a
`(document_name, page)` pair actually present in the retrieved chunks, or the agent falls back to
a deterministic, still citation-bearing answer. The real review reports turned out to be
**national sector-aggregate bulletins** (Power, Coal, Roads, Railways, etc.), not project-level
write-ups — a citation-relevance filter keeps a generic bulletin excerpt from being presented as
project-specific evidence unless it actually names the project or its agency.

### 8 — Web Intelligence agent

`GET /api/v1/projects/{project_id}/web-evidence` searches Tavily for external implementation
signals (news, government notices, tender/contractor/court disputes), scores each source into a
trust tier, and extracts grounded claims via an LLM (falls back to deterministic snippet +
keyword-overlap extraction with no key or a failed/invalid call).

### 9–10 — Risk Diagnosis & Intervention agents

```bash
python scripts/diagnose_projects.py
python scripts/recommend_interventions.py
```

`GET /api/v1/projects/{project_id}/diagnosis` fuses structured data, health, anomalies, ML
prediction, review-report and web evidence into one pool (`app/services/evidence/fusion.py`),
each item tagged with exactly one evidence category, then deterministically identifies ranked
risk drivers and an overall risk score. `GET /api/v1/projects/{project_id}/interventions` maps
every driver to a review/verification/monitoring/information-request action — never an
autonomous administrative decision.

### 11 — Coordinator & Reporting

```bash
python scripts/run_coordinator.py
curl -X POST http://localhost:8000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "Will this project finish on time?", "project_id": "617069"}'
```

`POST /api/v1/analyze` is the single entry point behind the ARIA chat: it classifies the
question's intent (14 possible intents, LLM-classified with a deterministic keyword fallback),
resolves the target project (returning `candidates` if the query is ambiguous), plans only the
stages that intent actually needs, executes them (in parallel where genuinely independent), and
risk-triggers a deeper analysis automatically if a narrow query turns out CRITICAL/HIGH risk.
The Reporting agent then writes one grounded executive-summary paragraph from whatever the plan
computed — the only LLM-generated prose in the whole report, with a guardrail that rejects any
claim contradicting the underlying deterministic facts (e.g. "on track" when the computed
schedule tier says otherwise).

`GET /api/v1/portfolio` ranks every ingested project by risk score for a portfolio-wide view.

---

## API reference

| Endpoint | Purpose |
|---|---|
| `GET /api/health` | Liveness check |
| `GET /api/v1/ready` | Readiness check (verifies DB connectivity) |
| `GET /api/v1/models` | ML model metadata (version, training metrics) |
| `GET /api/v1/projects` | List all ingested projects |
| `GET /api/v1/projects/{id}` | Project detail |
| `POST /api/v1/projects/{id}/predict` | Point-in-time ML cost-overrun prediction |
| `GET /api/v1/projects/{id}/health` | Deterministic health metrics |
| `GET /api/v1/projects/{id}/anomalies` | Anomaly detection results |
| `GET /api/v1/projects/{id}/history` | Timeline + LLM narrative |
| `GET /api/v1/projects/{id}/review-evidence` | RAG-grounded review-report answer |
| `GET /api/v1/projects/{id}/web-evidence` | Trust-tiered web intelligence |
| `GET /api/v1/projects/{id}/diagnosis` | Fused evidence + ranked risk drivers |
| `GET /api/v1/projects/{id}/interventions` | Recommended monitoring actions |
| `POST /api/v1/analyze` | Multi-agent Coordinator — free-text question → full report |
| `GET /api/v1/portfolio` | Portfolio-wide risk ranking |

Full interactive docs (request/response schemas): http://localhost:8000/api/docs

---

## MCP servers (Phase 12)

Seven MCP servers expose Phases 1–11's capabilities as controlled tools over the standard
Model Context Protocol, additively — the Coordinator (`POST /api/v1/analyze`) still calls every
service directly in-process, unchanged. Each server is a standalone process built on the
official `mcp` SDK's `FastMCP`:

| Server | Tools |
|---|---|
| PAIMANA | `get_project`, `get_monthly_observations`, `get_milestones`, `get_project_events` |
| ML | `predict_cost_risk`, `predict_time_risk`, `get_model_metadata`, `get_feature_schema`, `explain_prediction` |
| Analytics | `calculate_health`, `calculate_cost_utilisation`, `calculate_schedule_utilisation`, `calculate_progress_gap`, `calculate_divergence`, `calculate_expected_progress`, `calculate_trend`, `detect_anomaly` |
| Document | `search_documents`, `retrieve_chunks`, `get_document_page`, `get_document_metadata`, `find_project_mentions` |
| Web | `search_web`, `fetch_source`, `verify_source`, `extract_claim` |
| Knowledge | `vector_search`, `hybrid_search`, `store_evidence`, `retrieve_evidence` |
| Reporting | `generate_json_report`, `generate_markdown_report`, `generate_pdf_report`, `generate_executive_summary` |

Run any server standalone (stdio transport, for a local MCP client such as Claude Desktop/Code
or an MCP Inspector):

```bash
python mcp_servers/paimana/main.py
python mcp_servers/reporting/main.py --transport streamable-http --port 8107
```

Every tool returns a structured `status` (`OK`/`NOT_FOUND`/`NOT_AVAILABLE`/`ERROR`) rather than
raising — genuine gaps are reported honestly rather than fabricated (`predict_time_risk` is
always `NOT_AVAILABLE`, since no time-overrun model exists; `explain_prediction` is global
LightGBM feature importance, not a per-prediction SHAP explanation). `fetch_source`
(`backend/app/mcp/web/fetch.py`) is SSRF-safe: it range-checks every DNS-resolved address against
private/loopback/link-local/reserved ranges and never follows a redirect automatically.

Verify all 7 servers live, over the real MCP protocol, against the validation cohort:

```bash
python scripts/verify_mcp_servers.py
```

---

## Frontend

```bash
cd frontend && npm run dev
```

| Page | Purpose |
|---|---|
| `/` | Landing page (live backend status, links into the dashboard and AI analysis desk) |
| `/projects` | Portfolio dashboard — every ingested project with auto-loaded, color-coded health, a progress-vs-expected bar, trend arrow, and an interactive India map (Leaflet) |
| `/projects/{id}` | Project detail — Health/History/Review-Evidence/Web-Evidence/Diagnosis/Interventions tabs, the **AI Report Card** (runs every agent in parallel, persists to `localStorage`), and the project-scoped **ARIA Copilot** chat |
| `/analyze` | Portfolio-wide **ARIA Copilot** chat and free-text question box over `POST /api/v1/analyze` and `GET /api/v1/portfolio` |

The project-scoped **ARIA Copilot** additionally shows an expandable "Agent Reasoning Process"
trace and a collapsible "Data Sources & Evidence Grounding" panel. In both modes, the reply's
lead sentence adapts to the kind of question asked (schedule/timeline, intervention/mitigation,
risk-driver/cause, cost/budget) even when running on the deterministic fallback.

---

## Testing

```bash
cd backend
pytest                    # full suite (unit + integration)
pytest tests/unit         # fast, no DB
pytest tests/integration  # exercises the API + an in-memory/test DB
```

Tests are hermetic — every LLM call is mocked (`app.services.llm.groq_client.generate_text`),
so the suite never makes a real network call and never depends on `GROQ_API_KEY`/`GEMINI_API_KEY`
being set.

```bash
cd frontend
npm run lint
npm run typecheck
```

---

## License

Built as a submission for **Smart India Hackathon (SIH) 2.0**, problem statement from
MoSPI/IPMD. See `docs/` for the full problem statement and specification documents this system
was built against.
