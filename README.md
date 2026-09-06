# Project Monitoring AI

AI-Powered Predictive Project Monitoring & Early-Warning Platform (SIH 2.0 — MoSPI/IPMD).

Identifies infrastructure projects at risk of future cost overrun, time overrun, or
implementation problems, using **point-in-time** ML prediction plus an agentic layer that
explains, investigates, and recommends action. See [`docs/`](docs/) for the full SRS,
Solution Architecture, PRD, and Agentic Specification.

> Development principle: build the smallest working system first, validate it on the
> 5-project validation cohort, then progressively add intelligence, RAG, web evidence,
> multi-agent orchestration, MCP, evaluation, observability, cost tracking, and production
> hardening. See [`docs/development_phases.md`](docs/development_phases.md) for the full
> phase plan (Phase 0 → Phase 18). **This repository is currently at Phase 12.**

## Repository layout

```text
backend/         FastAPI application (api, core, models, schemas, services, repositories)
frontend/        Next.js dashboard
agents/          Specialist agents (coordinator, history, health, prediction, ...)
mcp_servers/     MCP server process entrypoints (Phase 12) - server code itself lives under
                 backend/app/mcp/<name>/, mirroring backend/app/services/<domain>/
ml/              Model training, feature engineering, inference, evaluation
rag/             Review-report ingestion/retrieval pipeline
data/            Raw / processed / feature / validation-cohort data
evaluation/      Agent + ML evaluation suites
observability/   Tracing, metrics, logging config
cost_tracking/   LLM/tool cost attribution
security/        Auth, policies, guardrails
prompts/         Versioned agent prompts
scripts/         One-off / operational scripts
docs/            SRS, Solution Architecture, PRD, Agentic Specification
model/           Pretrained model artifacts (source-of-record, not modified by the app)
project/         Raw Flash Report CSVs for the 5-project validation cohort
```

## Prerequisites

- Python 3.12+
- Node.js 20+
- Docker / Docker Compose (optional, for the full local stack)

## Local development (without Docker)

### Backend

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate        # Windows
# source .venv/bin/activate   # macOS/Linux
pip install -r requirements-dev.txt
cp ../.env.example ../.env    # then edit as needed
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

Run a migration (once models exist):

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

## Local development (with Docker Compose)

```bash
cp .env.example .env
docker compose up --build
```

This starts PostgreSQL, Redis, the API, and the frontend. Vector DB, object storage, and
MCP server containers are introduced in later phases.

## Configuration

All configuration is externalized via environment variables (see `.env.example`) and loaded
through `backend/app/core/config.py` (`pydantic-settings`). Never commit a real `.env` file.

## Point-in-time discipline

This system predicts and explains project risk **as of a chosen snapshot month**, using only
data available at or before that month. Any feature, evidence, or event with a timestamp
after the snapshot must never reach a prediction — this is enforced starting in the feature
engineering phase and is treated as a `DATA_LEAKAGE_DETECTED` failure if violated. See
`docs/SRS_AI_Powered_Predictive_Project_Monitoring.md` sections 1, 33, and DR-005.

## Validation cohort

Five projects (under `project/`) are the initial forward-looking validation cohort — projects
whose revised cost has not yet diverged from the originally approved cost (i.e. no cost
overrun has been recorded against them yet). They are early-warning test cases, not confirmed
cost-overrun labels, and their source records are never modified by the application.

## Data ingestion (Phase 1)

```bash
cd backend
python -m venv .venv && .venv/Scripts/activate && pip install -r requirements-dev.txt
alembic upgrade head
cd ..
python scripts/ingest_flash_reports.py
```

Profiles and ingests `data/raw/flash_reports/*.csv` (a working copy of `project/`, which stays
untouched) into `projects`, `project_monthly_observations`, `project_events`, and
`data_quality_issues`, and seeds `validation_cohort`. See
`backend/app/services/ingestion/` and `docs/development_phases.md` for details.

## Feature store (Phase 2)

```bash
python scripts/build_features.py
```

Computes one point-in-time feature vector per `(project_id, snapshot_month)` into
`project_monthly_features`, tagged with a versioned `feature_version` (`feature_versions`
table). Safe to re-run — feature rows are upserted and rebuilding is deterministic. See
`backend/app/services/features/formulas.py` for the exact, documented formulas.

## ML prediction (Phase 3)

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
reconstructs it from evidence, and what remains genuine, flagged uncertainty (mainly the
`kw_*` keyword lists). `GET /api/v1/models` returns model metadata (version, training metrics).
`GET /api/v1/projects` lists ingested projects.

## Project health (Phase 4)

```bash
curl http://localhost:8000/api/v1/projects/617069/health
```

Deterministic project-health metrics — cost/schedule utilisation, physical vs. expected
progress, expenditure-progress divergence, a recent trend, and milestone health (honestly
`NOT_AVAILABLE` — the real source data has no milestone fields). No ML, no LLM: plain
arithmetic in `backend/app/services/health/formulas.py`, computed live (nothing to persist for
it to stay reproducible). Optional `?as_of=YYYY-MM-DD` (defaults to the project's latest
observed month).

## Project History Agent (Phase 6)

```bash
python scripts/ask_project_history.py
python scripts/ask_project_history.py --question "Why is this project risky?"
```

The first LLM-using component. `GET /api/v1/projects/{project_id}/history` (optional
`?question=`, defaults to *"What happened to this project?"*, and `?as_of=`) answers with a
chronological, evidence-backed `timeline`, `major_changes`, and `historical_risk_signals` —
all built deterministically in `backend/app/services/history/timeline.py` (no LLM) — plus a
`current_state` narrative written by Gemini (`backend/app/services/history/llm.py`), the *only*
LLM-touched field. Every evidence entry is tagged `OBSERVED_FACT`, `INFERRED_TREND`, or
`MODEL_PREDICTION`. Requires `GEMINI_API_KEY` in `.env` (see `.env.example`) — if unset, the
call fails, or the model's output violates the output guardrail (asserts a definite overrun/
no-overrun outcome), the agent transparently falls back to a deterministic template summary
(`summary_source: "DETERMINISTIC_FALLBACK"`) rather than blocking or fabricating.

## Review-Report RAG (Phase 7)

```bash
python scripts/ingest_review_reports.py
python scripts/ask_review_evidence.py
python scripts/ask_review_evidence.py --question "Any mention of land acquisition delays?"
```

Ingests `data/raw/review_reports/*.pdf` (copied from `review reprot/`, which stays untouched):
PyMuPDF text extraction with an OCR fallback (`pytesseract`, activates automatically wherever
Tesseract is installed — degrades gracefully otherwise), page-aware chunking (a chunk never
spans two pages), Gemini embeddings (`gemini-embedding-001`, 768-dim, stored in Postgres via
`pgvector` — no separate vector DB service needed), then hybrid retrieval (vector + keyword,
combined by Reciprocal Rank Fusion) with a deterministic keyword-boost rerank. `GET
/api/v1/projects/{project_id}/review-evidence` (optional `?question=`, defaults to *"What does
the latest review report say about this project?"*) answers via the same grounded-LLM-with-
guardrail pattern as Phase 6: every claim must cite a `(document_name, page)` pair actually
present in the retrieved chunks, or the agent falls back to a deterministic, still
citation-bearing answer. The real review reports turned out to be **national sector-aggregate
bulletins** (Power, Coal, Roads, Railways, etc. — confirmed by inspecting the actual PDFs), not
project-level write-ups, so most retrieval surfaces general sector-level context rather than a
direct project mention — the answer says so explicitly rather than implying a false connection.

## MCP servers (Phase 12)

Seven MCP servers expose Phases 1–11's capabilities as controlled tools over the standard
Model Context Protocol, additively — the Coordinator (`POST /api/v1/analyze`) still calls
every service directly in-process, unchanged. Each server is a standalone process built on
the official `mcp` SDK's `FastMCP`:

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
(`backend/app/mcp/web/fetch.py`) is SSRF-safe: it range-checks every DNS-resolved address
against private/loopback/link-local/reserved ranges and never follows a redirect automatically.

Verify all 7 servers live, over the real MCP protocol, against the 5-project validation cohort:

```bash
python scripts/verify_mcp_servers.py
```

## Frontend dashboard

```bash
cd frontend && npm run dev
```

Visit `/projects` for the dashboard: every ingested project with its health (auto-loaded,
color-coded `overall_health`, a progress-vs-expected bar, trend arrow), an on-demand "Predict"
button for the ML cost-overrun risk, and "History" / "Review Evidence" tabs with free-text
question boxes showing the narrative, citations, and (for History) the full timeline with
color-coded evidence-type badges.
