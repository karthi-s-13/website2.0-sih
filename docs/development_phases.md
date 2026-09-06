# Development Phases

Execution order for this repository. Each phase should be built and validated before the
next begins — do not skip ahead (e.g. do not jump directly to the Coordinator Agent phase
before data, ML, and health/analytics exist).

| Phase | Name |
|---|---|
| 0 | Requirements & repository setup |
| 1 | Data ingestion & data quality |
| 2 | Point-in-time feature engineering |
| 3 | ML prediction service |
| 4 | Project health & deterministic analytics |
| 5 | Five-project validation |
| 6 | Project history intelligence |
| 7 | Review-report RAG |
| 8 | Web intelligence |
| 9 | Risk diagnosis & evidence fusion |
| 10 | Intervention recommendation |
| 11 | Coordinator Agent |
| 12 | MCP architecture |
| 13 | Dashboard & decision interface |
| 14 | Evaluation suite |
| 15 | Observability & cost tracking |
| 16 | Security, audit & guardrails |
| 17 | End-to-end integration |
| 18 | Production readiness |

## Status

- **Phase 0 — complete.** Backend (FastAPI) and frontend (Next.js) scaffolds, configuration
  system, Docker Compose, test structure, logging foundation, and migration system (Alembic)
  are in place. Health (`/api/health`) and readiness (`/api/v1/ready`, checks the database)
  endpoints work.
- **Phase 1 — complete.** `backend/app/services/ingestion/` normalizes the two real Flash
  Report CSV layouts (`report_month` vs `edition`+`record_type`; `notes` vs `record_status`),
  validates against the required data-quality rules, and upserts into `projects`,
  `project_monthly_observations`, `project_milestones` (empty — the source data has no
  milestone fields, so none are fabricated), `project_events` (deterministically derived),
  and `data_quality_issues` (nothing is silently dropped). `raw_observations` preserves every
  source row verbatim. Run `python scripts/ingest_flash_reports.py` to profile
  (`data/validation/profile_report.{json,md}`) and ingest `data/raw/flash_reports/*.csv`
  (copied from `project/`, which stays untouched). Note: `revised_cost_crore` is populated
  in the raw data for almost every row — it mirrors `original_cost_crore` until a project
  actually gets a cost revision, so "no revised cost yet" means "not yet diverged from
  original", not "field is null" (confirmed: only one row, project 619054's first
  observation, has it null, because the project was too new to have been assigned one).
- **Phase 2 — complete.** `backend/app/services/features/` computes a versioned
  (`feature_version="features-v1"`, registered in `feature_versions`) point-in-time feature
  vector per `(project_id, snapshot_month)`, one row per observed month, into
  `project_monthly_features`. Pipeline stages match the spec exactly: Temporal Filter
  (`filter_point_in_time`) → Feature Engineering (`compute_feature_vector`, pure/unit-tested,
  `backend/app/services/features/formulas.py`) → Point-in-Time Validation
  (`validate_point_in_time`, raises `DataLeakageError`/`DATA_LEAKAGE_DETECTED` from
  `app/core/errors.py` if any input postdates the snapshot — the exception type the top-level
  spec's section 1 anticipated) → Feature Store. Two scales are used deliberately:
  `cost_utilisation`/`expenditure_progress_divergence` are ratios (0-1ish); progress-related
  features stay in percentage points to match `physical_progress_percent` directly — documented
  in `FEATURE_VERSION_DESCRIPTION` alongside the code. `expenditure_growth` (relative rate) is
  distinct from `monthly_expenditure_growth` (absolute crore delta) — both were listed as
  separate core features. Rolling features use a trailing 3-month window
  (`ROLLING_WINDOW_MONTHS`). Run `python scripts/build_features.py` after ingestion. Verified
  against real Postgres: rebuilding is idempotent and produces byte-identical values (checksum
  match before/after rebuild) — the exit criterion.
- **Phase 3 — complete.** Integrated `model/lightgbm_cost_overrun_model.pkl` (a joblib-dumped
  dict: an sklearn `Pipeline` of `[FeatureEngineer, SimpleImputer, LGBMClassifier]`, plus
  `optimal_threshold`, `oof_metrics`, `trained_at`, `raw_feature_cols`) without retraining it.
  The pickle's custom `pipeline.feature_engineering.FeatureEngineer` step isn't importable as
  shipped — `ml/pipeline/feature_engineering.py` is a compatibility shim that restores its
  *fitted state* exactly (pickle does this automatically) and reconstructs its transform
  *logic* from hard evidence (raw/engineered column names, training medians, missing-indicator
  flags — see `docs/model_integration_notes.md` for the full derivation and every assumption
  flagged explicitly). A runtime check in `backend/app/services/prediction/model_loader.py`
  asserts the reconstruction's output columns match the fitted imputer's `feature_names_in_`
  on every load. `backend/app/services/prediction/service.py` enforces point-in-time
  correctness independently (reuses Phase 2's `filter_point_in_time`/`validate_point_in_time`)
  and never passes revised cost to the model. `POST /api/v1/projects/{project_id}/predict`
  matches the spec's exact request/response shape; predictions are logged to a `predictions`
  table (model_version + feature_version on every row). `GET /api/v1/projects` and
  `GET /api/v1/models` support a simple frontend view at `/projects`. Run
  `python scripts/predict_validation_cohort.py` after Phase 1 ingestion. Verified against real
  Postgres: all 5 validation projects produce valid predictions (probability in [0,1], a valid
  risk level, `leakage_check: PASSED`) at their own latest observed month — the exit criterion.
- **Phase 4 — complete.** `backend/app/services/health/` computes deterministic project-health
  metrics — no LLM, no ML model, plain arithmetic over point-in-time observations
  (`cost_utilisation`, `schedule_utilisation`, `physical_progress`, `expected_progress`,
  `progress_gap`, `expenditure_progress_divergence`, a `recent_trend` object, and
  `milestone_health`, which honestly reports `NOT_AVAILABLE` since the real source data has no
  milestone fields — never fabricated). Formulas and thresholds are unit-tested against the
  Phase 4 spec's own worked example (68.4/74.2/52.1/74.2/-22.1/16.3 → `overall_health: WATCH`)
  reproduced exactly. `overall_health` (`NORMAL/WATCH/ELEVATED/HIGH/CRITICAL`) is the worse of a
  schedule-shortfall tier and a divergence tier, bumped one level on a `STAGNANT` recent trend —
  thresholds are named constants in `formulas.py`, tunable later against evaluation data (Phase
  14), not buried magic numbers. Computed live (no new table — nothing here needs storing to be
  reproducible). `GET /api/v1/projects/{project_id}/health` (optional `?as_of=`, defaults to the
  latest observed month). The `/projects` frontend page now auto-loads health for every project
  on load (color-coded `overall_health` badge, a progress-vs-expected bar, trend arrow) beside
  the existing on-demand ML risk column. Verified against real Postgres: all 5 validation
  projects return valid health metrics over the real HTTP API — the exit criterion.
- **Phase 5 — complete.** `scripts/validate_cohort.py` generates a per-project validation
  report (`data/validation/project_01/` … `project_05/`, each with `report.md` and
  `report.json`) and a `portfolio_summary.md` / `.json` for all 5 forward-looking
  early-warning projects. Each report covers: Project Profile, Current Health (deterministic,
  Phase 4), ML Cost-Overrun Risk (Phase 3 prediction with leakage check), Historical Trend
  (observation timeline, derived events), Data Quality (issues from Phase 1 ingestion),
  Prediction Timestamp, and a Revised Cost Interpretation that correctly states: *"No revised
  cost is currently recorded as of the selected observation date. The ML probability is a
  forward-looking risk estimate, not a confirmed outcome."* — never claiming a definite
  overrun or definite safety. All five projects produce `leakage_check: PASSED` and valid
  predictions. Results are deterministic: re-running the script on the same ingested data
  reproduces identical metric values (health, probability, risk level) — the exit criterion.
  Portfolio summary: Project 01 (617069, ELEVATED/LOW 13.0%), Project 02 (619054, WATCH/LOW
  8.8%), Project 03 (616672, WATCH/LOW 3.8%), Project 04 (617184, ELEVATED/LOW 2.0%),
  Project 05 (617279, WATCH/LOW 0.8%).
- **Phase 6 — complete.** `backend/app/services/history/` is the Project History Agent — the
  first LLM-using component. Split cleanly in two: `timeline.py` is pure, deterministic Python
  (no LLM, no network) that turns observations/events/DQ-issues/health/predictions into a
  chronological `timeline`, `major_changes`, and `historical_risk_signals`, each entry tagged
  `OBSERVED_FACT` (raw data or a plain diff), `INFERRED_TREND` (a threshold/pattern judgment —
  health tiers, non-monotonic flags), or `MODEL_PREDICTION` (strictly Phase 3's output).
  `llm.py` calls Gemini (`google-genai`, model `gemini-3.6-flash`) for exactly one thing: the
  `current_state` narrative, grounded only in that already-finished evidence — never used to
  compute a fact, trend, or prediction. Graceful degradation throughout: no API key, a failed
  call, or an output-guardrail violation (the same forbidden-phrase check from Phase 5 — no
  "will definitely overrun"/"will definitely not overrun") all fall back to a deterministic
  template summary, never a raised error. `GET /api/v1/projects/{project_id}/history` (optional
  `?question=`, defaults to *"What happened to this project?"*, and `?as_of=`). Verified live
  against real Postgres + the real Gemini API (not mocked): the model's actual response
  correctly distinguished "observed data shows...", "Deterministic trend analysis
  indicates...", used the required exact phrase *"No revised cost is currently recorded..."*,
  and called the ML output "a forward-looking risk estimate, not a confirmed outcome" — with
  zero forbidden phrases, unprompted. The `/projects` frontend page gained a "History" toggle
  per project with a free-text question box, showing the narrative, risk signals, and full
  timeline with color-coded evidence-type badges. The 147 automated tests mock the LLM call (so
  the suite stays hermetic/fast); the LLM's own success/failure/guardrail paths are unit-tested
  directly against a stubbed `google.genai.Client`. Exit criterion: a user can ask "What
  happened to this project?" for any of the 5 validation projects and get a chronological,
  evidence-backed answer — confirmed for all 5, live.
- **Phase 7 — complete.** `backend/app/services/rag/` is the Review Report RAG pipeline, built
  against the real PDFs in `review reprot/` (9 monthly editions, March 2025 – January 2026,
  copied untouched into `data/raw/review_reports/`). Inspecting the actual files first paid
  off: they turned out to be **national sector-aggregate infrastructure bulletins** (Power,
  Coal, Steel, Cement, Fertilizers, Petroleum, Roads, Railways, Shipping & Ports, Civil
  Aviation, Telecommunications — the documents' own stated 11 components), not project-level
  write-ups — zero of the 5 validation projects' names/codes appear anywhere in any of the 9
  PDFs (verified by full-text search before writing a line of pipeline code). The design
  follows from that finding: `metadata.py`'s `sector` detection uses the reports' own stated
  vocabulary (not invented), `project_id` tagging is honestly left null except where a project
  name/agency literally appears, and `ministry` is left unset rather than assumed (no
  letterhead/ministry name was found in the extracted text — the cover page is an unlabeled
  image). Pipeline stages match the spec exactly: `extraction.py` (PyMuPDF, with an OCR
  fallback via `pytesseract` that activates automatically wherever Tesseract is installed —
  blocked by this sandbox's lack of elevation, so it degrades gracefully here, coded to work
  elsewhere) → `chunking.py` (page-aware — a chunk never spans two pages) → `metadata.py` →
  `embeddings.py` (Gemini `gemini-embedding-001`, 768-dim, asymmetric `RETRIEVAL_DOCUMENT`/
  `RETRIEVAL_QUERY` task types) → `vector_store.py` (pgvector, reusing the existing Postgres —
  no separate vector DB service) → `retrieval.py` (hybrid: vector + keyword search combined by
  Reciprocal Rank Fusion, then a deterministic keyword-boost rerank — no LLM in this half at
  all) → `answer.py` (the only LLM-touched step: composes the final answer, must cite a real
  `(document_name, page)` pair or explicitly say no relevant evidence was found, guardrail-
  checked, falls back to a deterministic citation-bearing answer otherwise). A real rate limit
  was hit and handled for real during ingestion (the free-tier embeddings quota): `embeddings.py`
  retries 429s with exponential backoff and paces batches; `ingest_directory` commits after each
  document so a later failure can't discard earlier progress. `GET
  /api/v1/projects/{project_id}/review-evidence` (optional `?question=`). Verified against real
  Postgres + the real Gemini API: ingested all 9 PDFs (705 chunks, zero errors after the retry
  fix) via `python scripts/ingest_review_reports.py`, then ran
  `python scripts/ask_review_evidence.py` for all 5 validation projects — every answer correctly
  and explicitly stated the project was not named in any excerpt, described only the general
  sector-level context actually found, and never implied a false direct connection. Exit
  criterion confirmed live: every retrieved answer, for all 5 projects, carried real
  `(document_name, page)` citations (5 each) drawn from the actual indexed PDFs.
- **Phase 8 — complete.** `backend/app/services/web/` is the Web Intelligence Agent, matching
  the spec's exact workflow (Project Context → Risk Context → Query Planner → Search → Source
  Filtering → Source Fetch → Claim Extraction → Date Verification → Project Relevance →
  Evidence Store). No search provider existed yet (`.env` had none); asked the user, who chose
  **Tavily** — a single API key, same pattern as `GEMINI_API_KEY` (Phase 6/7), no new SDK
  dependency (`httpx`, already a dependency, calls it directly). `trigger.py` is a hard gate
  (`should_trigger`) — search never runs on every request (spec §96.5 anti-pattern): only when
  `overall_health`/ML `risk_level` is `HIGH`/`CRITICAL`, an explicit `force=true`, or a future
  `for_diagnosis=true` from Phase 9. `query_planner.py` is deterministic, not LLM-based: it maps
  whichever risk-driver categories are actually present (high ML risk, schedule-behind,
  expenditure-ahead, a non-monotonic data-quality issue, a stagnant trend) onto a bounded subset
  (≤4) of the spec's 12 topics — never all 12 at once. `trust.py` classifies every source into
  the spec's TIER 1–5 (`.gov.in`/`.nic.in` → TIER 1, agency-domain match → TIER 2, a curated
  news-domain list → TIER 3, else TIER 4, unresolvable → TIER 5), stored as `source_quality` on
  every row so a low-trust finding is never silently treated as authoritative.
  `claim_extraction.py` makes one bounded Gemini call per topic-query batch (not per result),
  grounded only in the batch's own returned snippets, JSON-structured (`finding`,
  `project_relevance`); an unset key, a failed call, or invalid/mismatched-length output falls
  back to a deterministic truncated-snippet + keyword-overlap-relevance extraction — same
  guardrail shape as `history/llm.py`/`rag/answer.py`. Results persist to a new `web_evidence`
  table (evidence store, mirrors spec §22's Evidence object for a web source) with a
  content-addressed `evidence_id` (`sha256(project_id:topic:url)`) so re-running the same query
  updates rather than duplicates. `GET /api/v1/projects/{project_id}/web-evidence` (optional
  `?force=`, `?as_of=`). Graceful degradation throughout (PRD §65): one topic's search failure
  never blocks the others, and no `TAVILY_API_KEY` yields an honest `warnings` list with zero
  evidence — never a fabricated finding. The `/projects` frontend page gained a "Web" tab
  (Check / Force search) showing trigger status, topics searched, warnings, and evidence cards
  (source, trust-derived quality badge, date + verification confidence, finding, relevance,
  URL). Verified: 49 new backend tests pass (search/LLM calls mocked, hermetic), full suite
  (249 tests) green; `python scripts/ask_web_evidence.py` against all 5 validation projects
  confirms the trigger gate correctly stays silent by default (none are HIGH/CRITICAL, matching
  the Phase 5 portfolio summary) and, under `--force`, runs the full pipeline with an honest
  "TAVILY_API_KEY is not configured" warning per topic and zero fabricated evidence; the same
  behavior was confirmed live over the real HTTP API and in the browser (screenshot of both the
  untriggered and forced states rendering correctly) — the exit criterion, pending a real
  `TAVILY_API_KEY` for live evidence. A real `TAVILY_API_KEY` was added right after — see Phase 9.
- **Phase 9 — complete.** Evidence Fusion & Risk Diagnosis: answers "why is this project at
  risk?" by combining ML (Phase 3), Health (Phase 4), History (Phase 6), Review evidence
  (Phase 7), Web evidence (Phase 8), and a new Anomaly module. `development_phases.md` never
  allocated Anomaly its own phase number, but the SRS requires it (FR-014) and Phase 9 cannot
  fuse an input that doesn't exist — `backend/app/services/anomaly/` fills that gap: pure
  z-score statistics over each project's own historical monthly deltas (no LLM), detecting
  `EXPENDITURE_ACCELERATION`, `SUDDEN_PROGRESS_DECLINE`, `PROGRESS_STAGNATION`,
  `EXPENDITURE_PROGRESS_DIVERGENCE` (abrupt month-over-month jump, distinct from Health's
  absolute-level framing), and `SCHEDULE_DETERIORATION`; a z-score is only computed with ≥3
  prior deltas as baseline, else the check is skipped rather than fabricated.
  `UNEXPECTED_MILESTONE_CHANGES` stays honestly `NOT_AVAILABLE` (no milestone data, same as
  Phase 4). `GET /api/v1/projects/{project_id}/anomalies`.
  `backend/app/services/evidence/fusion.py` normalizes all six sources into one pool, each
  item tagged with **exactly one** of the user's six categories — never mixed:
  `PAIMANA_STRUCTURED_DATA` (raw `ProjectEvent` facts), `ANALYTICAL_INFERENCE` (Health tiers +
  Anomaly + non-monotonic DQ flags — the same classification Phase 6 already gives those),
  `MODEL_INFERENCE` (the ML prediction), `REVIEW_REPORT` (Phase 7 citations),
  `OFFICIAL_EXTERNAL_SOURCE`/`SECONDARY_SOURCE` (Phase 8 web evidence split by its stored
  `trust_tier`). Evidence IDs are deterministic (sha256 of stable parts) for non-persisted
  sources — reproducible, same precedent Phase 4/6 already set; web evidence reuses its real
  `web_evidence` row ID. `backend/app/services/diagnosis/drivers.py` deterministically detects
  risk drivers (schedule gap, expenditure divergence, data-quality concern, stagnation,
  anomaly-only drivers, dormant milestone check, and "External constraint: {topic}" for a
  strong web finding not already covered by an internal signal — SRS FR-026's own example),
  reusing `DRIVER_TOPIC_MAP` from Phase 8's query planner (a pure constant) to link a driver to
  the web/review evidence that supports it — closing the loop between why Phase 8 searched and
  what that search backs. Every driver's `evidence_ids` is built strictly from the fused pool;
  a driver with no evidence is dropped rather than emitted empty. `risk_fusion.py` is a
  deterministic, versioned (`risk-fusion-v1`) weighted score (cost ML risk 0.30, schedule
  health 0.20, divergence health 0.20, anomaly severity 0.20, external evidence 0.10 —
  deliberately smallest, unverified sources must never dominate per FR-020), renormalized over
  whichever dimensions actually have data; `overall_risk`'s label reuses
  `prediction.risk.risk_level_for_probability` directly (FR-025 is byte-for-byte the same
  0–100 → LOW/MODERATE/ELEVATED/HIGH/CRITICAL scale already built in Phase 3, not a second
  vocabulary). `GET /api/v1/projects/{project_id}/diagnosis` (optional `?as_of=`,
  `?include_web=`) returns the user's exact `overall_risk`/`drivers[].{rank,driver,severity,
  evidence_ids}` core plus `risk_score`, `confidence`, `fusion_version`, and the full evidence
  pool. No new tables beyond Phase 8's `web_evidence` — Anomaly and Diagnosis are both fully
  deterministic/reproducible from already-persisted data, recomputed live (same precedent as
  Health and History). The `/projects` frontend page gained a "Diagnosis" tab (risk badge,
  score, confidence, ranked driver cards with category-badged evidence, full evidence pool).
  Verified: 54 new backend tests pass (web/review calls mocked, hermetic), full suite
  (303 tests) green; `python scripts/diagnose_projects.py` run live against real Postgres with
  real Gemini and Tavily keys for all 5 validation projects — every driver carried resolvable,
  correctly-categorized evidence (never mixed categories), Gemini's free-tier rate limit was
  hit repeatedly during the run and each claim-extraction call degraded to its deterministic
  fallback exactly as designed (zero fabricated findings), and every project's `overall_risk`
  matched its independently-computed `risk_score` via `risk_level_for_probability` — the exit
  criterion, confirmed live over the real HTTP API and in the browser (screenshot of the
  Diagnosis tab rendering correctly, zero console errors).
- **Phase 10 — complete.** Intervention Agent: translates Phase 9's diagnosed drivers into
  monitoring actions - "What should the monitoring authority look at next?" - never an
  autonomous administrative decision. Fully deterministic, no LLM (matches Risk Fusion's own
  documented preference, spec section 23, and keeps a "never issue an administrative decision"
  requirement structurally enforceable rather than dependent on prompt-following).
  `backend/app/services/intervention/mapping.py` is a plain lookup table, Driver Classification
  → Action Mapping → Responsible Review Area (spec section 25's exact workflow), from each Phase
  9 driver's stable `driver_key` to one of the seven action types the user's spec names
  (`REVIEW`, `VERIFICATION`, `MONITORING`, `INFORMATION_REQUEST`, `MILESTONE_REVIEW`,
  `COST_PROGRESS_REVIEW`, `IMPLEMENTATION_REVIEW`) — e.g. `EXPENDITURE_AHEAD` →
  `COST_PROGRESS_REVIEW`, "Review expenditure against physical achievement" (byte-for-byte the
  spec's own section-25 example), `SUDDEN_PROGRESS_DECLINE` → `VERIFICATION`, an
  `EXTERNAL_CONSTRAINT:<topic>` driver → `VERIFICATION` naming the topic (since by construction
  that evidence is unverified/lower-confidence — the correct action is to verify it, not act on
  it). This required one small additive change to Phase 9: `Driver` gained a `driver_key` field
  (e.g. `"SCHEDULE_BEHIND"`) alongside its existing human-readable `driver` label, so Phase 10
  can branch on a stable machine key instead of string-matching label text — backward compatible,
  existing Phase 9 consumers unaffected. `assert_not_administrative_decision` is a forbidden-
  phrase guardrail (same shape as `history/llm.py`'s) checked against every generated
  action/reason string, defense-in-depth alongside the structural guarantee that the action
  templates never describe an executed act. `service.py` runs Phase 9's `diagnose_project`, maps
  every driver to a recommendation (`priority` = the driver's own severity, `evidence_ids` =
  the driver's own evidence, so every recommendation is exit-criterion-traceable back to real
  evidence), and adds one additional `MONITORING`-type recommendation ("increase monitoring
  frequency") whenever `overall_risk` is `MODERATE` or worse, carrying a `suggested_monitoring_
  level` per FR-028's `NORMAL|ENHANCED|PRIORITY|CRITICAL` scale (mapped from `overall_risk`).
  `GET /api/v1/projects/{project_id}/interventions` (optional `?as_of=`, `?include_web=`)
  returns the user's exact `recommendations[].{priority,action,reason,evidence_ids}` core plus
  `action_type`, `review_area`, `driver`, and `monitoring_level` per FR-027's full field list.
  The `/projects` frontend page gained an "Interventions" tab (overall risk badge, suggested
  monitoring level, and recommendation cards with priority/action-type badges, action, reason,
  and evidence count). Verified: 28 new backend tests pass (including a guardrail test that
  every action-map template itself passes `assert_not_administrative_decision`), full suite
  (333 tests) green; `python scripts/recommend_interventions.py` run live against real Postgres
  for all 5 validation projects — every recommendation carried a real, non-empty evidence
  reference and used only review/verification/monitoring/information-request language, never a
  decision — confirmed live over the real HTTP API and in the browser (screenshot of the
  Interventions tab rendering correctly, zero console errors), the exit criterion.
- **Phase 11 — complete.** Coordinator Agent: the root agent that connects every capability
  (Phases 3–10) into one workflow driven by a single natural-language request. Two design facts
  drove the architecture:
  1. **The spec's 12 named stages don't map 1:1 onto 12 service calls.** Phase 9's
     `diagnose_project` already internally runs Health + Prediction + Anomaly + Review + Web +
     Evidence Fusion + Risk Fusion + Diagnosis in one call, and Phase 10's `recommend_
     interventions` already internally calls `diagnose_project` again. `backend/app/services/
     coordinator/planning.py` plans in terms of the actual distinct calls (`PROJECT`, `HISTORY`,
     `HEALTH`, `PREDICTION`, `ANOMALY`, `REVIEW`, `WEB`, `DIAGNOSIS`, `INTERVENTION`) rather than
     the spec's 12 illustrative names, so nothing gets silently duplicated. `INTENT_PLAN` matches
     the user's spec examples exactly: `COST_RISK`/`TIME_RISK` → `PROJECT, PREDICTION`;
     `PROJECT_HEALTH` → `PROJECT, HEALTH`; `COMPLETE_PROJECT_ANALYSIS`/`REPORT_GENERATION`/
     `INTERVENTION` → `PROJECT, HISTORY, INTERVENTION` (the last call alone already covers every
     other stage). Risk-triggered expansion (spec §30) reuses the exact `{"HIGH","CRITICAL"}`
     sets already defined in Phase 8's `web/trigger.py`.
  2. **A Reporting Agent (spec §26) never got its own phase number** — same situation as Phase
     9's Anomaly gap. `backend/app/services/reporting/` fills it: `builder.py` deterministically
     assembles a `Report` (current health, cost-overrun risk, an honestly-`NOT_AVAILABLE` time-
     overrun note — no second ML model was ever built, key changes, top risk drivers, evidence,
     recommended actions, confidence/data-quality, model versions, and a `human_review_required`
     flag per spec §48's rule: CRITICAL risk, an unavailable model, or low diagnosis confidence)
     from whatever the Coordinator actually computed — every field stays `None`/empty when its
     stage never ran, never backfilled. `narrative.py` is the one LLM call (same guardrail shape
     as `history/llm.py`), writing only the executive-summary paragraph, grounded strictly in
     the already-built facts.

  `backend/app/services/coordinator/`: `intent.py` (13-way classification, one bounded Gemini
  call + a deterministic keyword fallback covering every intent); `resolution.py` (project
  identity resolution, spec §8 — an explicit `project_id` short-circuits everything; free-text
  matching filters a stoplist of recurring infrastructure-title vocabulary like "transmission"/
  "system"/"power" before comparing, so a query has to actually *name* a project's distinctive
  part, not just share domain jargon with dozens of unrelated ones — `RESOLVED`/`AMBIGUOUS`/
  `NOT_FOUND`); `budget.py` (a wall-clock deadline, spec §52 — a stage due after the deadline is
  recorded `SKIPPED`, spec §67's vocabulary); `state.py` (the shared `AnalysisState`, spec §9);
  `stages.py` (one function per call, each catching its own exceptions and recording
  SUCCESS/FAILED rather than raising — spec §46/47 graceful degradation, a failed `WEB` call
  never blocks `HISTORY`); `portfolio.py` (batch Health+ML ranking across every ingested
  project, spec §7.4/§34, with an optional deep-dive diagnosis reserved for the top-N highest-
  risk projects only — cost-aware routing, spec §53); `service.py` (`run_analysis`: classify →
  resolve → plan → execute → expand if triggered → report).

  **Parallel execution is genuinely implemented**, not just documented: `HISTORY` and
  `DIAGNOSIS`/`INTERVENTION` are independent, and the latter (its own sequential Review/Web
  calls) is the slow path, so when a plan contains both, `service.py` runs them concurrently via
  `ThreadPoolExecutor`, each on its own `Session` derived from the caller's own engine
  (`session.get_bind()`, not the global `SessionLocal` — verified live against real Postgres,
  where this matters). Discovered live in testing: a single shared in-memory sqlite connection
  (`StaticPool`, used by every prior phase's hermetic test fixtures) is not safe under genuine
  concurrent cursor use from separate OS threads — corrupts unrelated queries with bizarre
  errors. Fixed by adding a `parallel: bool` parameter (default `True`); the backend test suite
  runs with `parallel=False` (deterministic, sqlite-safe) while true concurrency is exercised
  live in `scripts/run_coordinator.py` against real Postgres.

  `POST /api/v1/analyze` (`{"query", "project_id"?, "as_of"?}`) and `GET /api/v1/portfolio`. The
  frontend gained a new `/analyze` page (query box, example questions, project picker, rendered
  report, portfolio ranking table), linked from `/projects` and the homepage. No MCP layer (Phase
  12's job), no auth (nothing in this codebase implements it yet), no OpenTelemetry (Phase 15's
  job) — `stage_results` gives a real, lightweight execution trace instead.

  Verified: 63 new backend tests pass (hermetic — every LLM/network call mocked, `parallel=
  False`), full suite (402 tests) green, stable across repeated runs; `python scripts/
  run_coordinator.py` run live against real Postgres + real Gemini/Tavily for all 5 spec-§57
  "golden questions" — every question routed to exactly the intent/plan the spec's own examples
  predict ("What is the cost-overrun probability?" → `COST_RISK` → `PROJECT, PREDICTION`; "What
  is the current health?" → `PROJECT_HEALTH` → `PROJECT, HEALTH`), and every Gemini call hit the
  free-tier rate limit (429) during the run yet every code path degraded to its deterministic
  fallback exactly as designed — zero crashes, zero fabricated data; `--portfolio` reproduced
  Phase 5's known validation-cohort risk ordering exactly. Confirmed live over the real HTTP API
  and in the browser (screenshots of a narrow-plan report, a full-plan report with drivers/
  evidence/recommendations, and the portfolio ranking table, zero console errors) — the exit
  criterion.

- **Phase 12 — complete.** MCP Architecture: an additive interface layer over Phases 1–11's
  already-built services — the Coordinator (`backend/app/services/coordinator/`) is untouched
  and still calls every service directly in-process exactly as Phase 11 left it (its tested
  `ThreadPoolExecutor` parallel path and all 63 of its own tests are unaffected). Seven MCP
  servers, one per `mcp_servers/<name>/` directory (`paimana`, `ml`, `analytics`, `documents`,
  `web`, `knowledge`, `reporting`), built on the official `mcp` Python SDK's `FastMCP`
  (`mcp==1.29.1`, added to `backend/requirements.txt`; required bumping `pydantic` to `2.13.5`
  and adding `sse-starlette==1.8.2` pinned below the version that would otherwise require a
  `starlette` newer than FastAPI 0.115.6 tolerates — verified with `pip check` and the full
  402-test baseline suite passing unchanged before any new code was added). Server code lives
  at `backend/app/mcp/<name>/{schemas.py,service.py}` (mirroring the existing
  `backend/app/services/<domain>/` convention exactly, importing those services directly) with
  thin `mcp_servers/<name>/main.py` process entrypoints supporting both `stdio` (local/dev
  clients — verified live end-to-end as a real MCP client subprocess, not just in-process
  `FastMCP.call_tool`) and `streamable-http` (future containerized deployment, fixed ports
  8101–8107) transports via a `--transport` flag. Every tool returns a structured `status`
  field (`OK`/`NOT_FOUND`/`NOT_AVAILABLE`/`ERROR`) rather than raising across the protocol
  boundary — the same "honest `NOT_AVAILABLE`, never fabricate" discipline every prior phase
  already follows, just applied at the MCP boundary (`backend/app/mcp/_shared.py::
  error_envelope`, never downgrading a `DATA_LEAKAGE_DETECTED` to merely unavailable).
  **PAIMANA MCP** (`get_project`, `get_monthly_observations`, `get_milestones`,
  `get_project_events`) required one small additive repository function, `get_milestones` in
  `project_repository.py` (didn't exist before — milestones were only ever queried inline).
  **ML MCP** (`predict_cost_risk`, `predict_time_risk`, `get_model_metadata`,
  `get_feature_schema`, `explain_prediction`) honestly reports `predict_time_risk` as
  `NOT_AVAILABLE` (no time-overrun model was ever built) and `explain_prediction` as
  `explanation_type: GLOBAL_FEATURE_IMPORTANCE` — the LightGBM classifier's own
  `feature_importances_`, defensively name-resolved rather than trusted at face value: live
  inspection of the real model artifact confirmed `SimpleImputer(add_indicator=True)` widens
  its 23 named columns to 31 actual classifier inputs (8 `missingindicator_*` columns, from
  `imputer.indicator_.features_`), **and** that the classifier's own `feature_name_` attribute
  — despite matching that length — is entirely meaningless (`"Column_0"`, `"Column_1"`, ...,
  since sklearn never passed real column names through to LightGBM), so real names are always
  reconstructed from `FEATURE_COLUMNS` + the indicator columns, never read off the classifier;
  a dedicated unit test (`test_mcp_ml_feature_names.py`) pins this against the real artifact so
  a future model swap can't silently regress to reporting `"Column_N"` labels as if they meant
  something. **Analytics MCP** (`calculate_health` plus 6 thin per-metric wrappers,
  `detect_anomaly`) introduces `HEALTH_FORMULA_VERSION = "health-v1"` in `health/formulas.py`
  (Phase 4 never versioned its own formulas explicitly); `calculate_expected_progress` uses its
  own more specific `"linear-v1"` version tag (Phase 2's own FR-009 method id) rather than
  `health-v1`, a deliberate, documented deviation. **Document MCP** and **Knowledge MCP** share
  one new helper, `backend/app/mcp/_shared.py::run_hybrid_or_keyword_search`, rather than
  duplicating the embedding-fallback-to-keyword-search logic `rag/service.py` already
  established; Document MCP required two new read-only repository functions (`get_document`,
  `get_chunks_by_page`, plus `get_chunks_by_indexes`/`list_chunks`/`count_chunks`) in a new
  `document_repository.py`. `find_project_mentions`, tested live against all 5 validation-cohort
  projects, reconfirms Phase 7's own finding exactly: `evidence_found=True` for every project
  (the corpus always surfaces some sector-level context) while the answer itself explicitly
  states no direct project mention was found — never a fabricated direct match. **Web MCP**'s
  `fetch_source` (`backend/app/mcp/web/fetch.py`) is the one genuinely new security-sensitive
  component — resolves and range-checks every DNS-returned address against
  private/loopback/link-local/reserved/multicast/unspecified ranges before connecting (blocks
  `127.0.0.1`, `10.0.0.0/8`, the `169.254.169.254` cloud-metadata address, `::1`, by IP range,
  not string-matching), never follows a redirect (returns it to the caller as `status:
  "REDIRECT"` to re-validate from scratch — closes the classic SSRF-via-redirect bypass by
  construction), and streams with a hard byte cap; documented as pre-flight DNS validation, not
  a fully DNS-rebinding-proof pinned-connection transport — an explicit, accepted trade-off
  given this project's minimal-new-infra preference, not a silent gap. **Knowledge MCP**'s
  `store_evidence`/`retrieve_evidence` are explicitly scoped to Phase 8's `web_evidence` table
  only — Phase 9's in-memory `FusedEvidence` is never persisted by any tool — documented in the
  tool's own docstring; `evidence_id` generation reuses Phase 8's own content-addressed formula
  by promoting `web/service.py`'s previously-private `_evidence_id` to a public `evidence_id`
  function (one rename, one call-site update) rather than duplicating the hash logic.
  **Reporting MCP** (`generate_json_report`, `generate_markdown_report`, `generate_pdf_report`,
  `generate_executive_summary`) reuses `reporting/builder.py` and `reporting/narrative.py`
  exactly as the Coordinator does, via a new `orchestration.py::build_full_report` that
  deliberately also calls `stages.run_health`/`stages.run_prediction` before Coordinator's own
  `FULL_PLAN` sequence (`HISTORY` + `INTERVENTION`) — closing a real, live-confirmed gap where
  Coordinator's own `REPORT_GENERATION` plan alone never separately populates
  `state.health`/`state.prediction` (only `run_intervention` runs, which doesn't set them),
  without touching `coordinator/stages.py` itself; a dedicated integration test asserts
  `current_health`/`cost_overrun_risk` come back populated, and a live run against real
  Postgres + Gemini + Tavily confirmed it directly (both fields non-null; Gemini's free-tier
  rate limit was hit repeatedly mid-run, same as every prior phase's live runs, and every
  narrative call degraded to its deterministic fallback exactly as designed). Markdown
  rendering is pure deterministic templating (no LLM); PDF rendering reuses PyMuPDF (already a
  Phase 7 dependency) with manual line-by-line layout and page-break pagination (chosen over
  `insert_textbox` for deterministic, unit-testable pagination) — no new PDF dependency added.
  Verified: 67 new backend tests pass (LLM/network calls mocked via the same
  `google.genai.Client`-blocking pattern `test_coordinator_service.py` established, or gated
  behind an opt-in `MCP_TEST_REAL_NETWORK=1` env flag for the one genuine real-network
  `fetch_source` test; pgvector-dependent Document/Knowledge tests skip when Postgres isn't
  reachable, same as `test_rag_vector_store.py`), full suite (470 collected, 469 passed, 1
  opt-in test skipped) green; `python scripts/verify_mcp_servers.py` connected to all 7 servers
  as a real MCP client over the actual stdio subprocess protocol (not just in-process
  `FastMCP.call_tool`) and called every tool — PAIMANA's four tools for all 5 validation-cohort
  projects individually, every other server's tools for a representative project — with zero
  protocol-level failures and every tool's own `status` field honest and correctly shaped
  (including `predict_time_risk`'s permanent `NOT_AVAILABLE` and `fetch_source`'s correct
  `REJECTED`/`UNSAFE_HOST` for a loopback URL) — the exit criterion, confirmed live.

## Critical, cross-phase principle: point-in-time prediction

For any prediction made at snapshot month `T`, only data with `feature_timestamp <= T` may be
used. Future revised cost, future revised completion date, future expenditure, future
progress, future events, future review findings, and future web evidence must never be used
as features for a historical prediction. A violation must be flagged as
`DATA_LEAKAGE_DETECTED` and the prediction must be blocked. This applies starting in Phase 2
and is re-validated in Phase 5 (the five-project cohort) and Phase 14 (evaluation).

## Validation cohort (Phase 5)

The five projects under `project/` are forward-looking early-warning cases — they do not yet
carry a revised cost. They must not be treated as confirmed cost-overrun labels. A
`validation_cohort` table (see SRS DR/DB sections) tracks `cohort_id`, `project_id`,
`as_of_date`, `reason_selected`, `status`, `notes`. Original source records for these
projects are never modified.
