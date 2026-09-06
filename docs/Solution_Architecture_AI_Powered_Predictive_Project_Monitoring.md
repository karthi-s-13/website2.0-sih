# Solution Architecture Document
# AI-Powered Predictive Project Monitoring & Early Warning Platform

**Project:** SIH 2.0 – MoSPI/IPMD  
**Version:** 1.0  
**Document Type:** Solution Architecture  
**Status:** Proposed Architecture  
**Primary Objective:** Predict, diagnose, explain, and recommend actions for cost escalation, schedule delay, and implementation risks in Central Sector Infrastructure Projects.

---

## 1. Executive Summary

This solution is a hybrid **AI + ML + analytics + RAG + web intelligence + agentic orchestration** platform for proactive monitoring of infrastructure projects.

The platform is designed around one principle:

> **Predict → Detect → Diagnose → Explain → Recommend → Monitor**

The system does not make the LLM responsible for numerical prediction or deterministic calculations. Instead:

- **ML models** predict future cost/time overrun risk.
- **Analytics/rules engines** calculate project health and baseline deviations.
- **Anomaly detection** identifies unusual project behavior.
- **Project History Agent** reconstructs what happened over time.
- **Review Report Agent** extracts findings from official review reports.
- **Web Intelligence Agent** discovers relevant external evidence.
- **Evidence Agent** verifies and classifies evidence.
- **Risk Diagnosis Agent** identifies likely causes and risk drivers.
- **Intervention Agent** recommends monitoring/intervention actions.
- **Coordinator Agent** orchestrates the complete workflow.
- **MCP servers** expose controlled tools to agents.
- **Evaluation, observability, cost, security, and audit layers** operate across the entire platform.

The final output is a decision-support package for a monitoring officer or senior decision maker rather than an unexplained model score.

---

# 2. Problem Context

The platform is intended for monitoring Central Sector Infrastructure Projects tracked by the Ministry of Statistics and Programme Implementation (MoSPI), Infrastructure & Project Monitoring Division (IPMD).

The project-monitoring environment contains:

- project master information;
- approved and revised cost;
- original and revised completion dates;
- monthly expenditure;
- physical progress;
- milestones;
- project status;
- implementing agency information;
- historical Flash Reports;
- Review Reports;
- external information relevant to implementation risks.

The challenge is not merely to display historical status.

The objective is to identify projects that may become problematic **before cost escalation, schedule delay, or implementation failure becomes fully visible**.

---

# 3. Architecture Goals

## 3.1 Primary Goals

1. Predict future cost-overrun probability.
2. Predict future time-overrun probability.
3. Detect abnormal project behavior.
4. Compare project performance against approved baselines.
5. Reconstruct project history.
6. Identify probable risk drivers.
7. Incorporate official review-report evidence.
8. Incorporate relevant external web evidence.
9. Generate explainable project risk scores.
10. Recommend appropriate monitoring/intervention actions.
11. Provide evidence-backed decision support.
12. Maintain complete agent/tool/model execution traces.
13. Track AI and infrastructure cost.
14. Evaluate agents and models continuously.
15. Prevent data leakage in predictive modelling.
16. Support project-level and portfolio-level analysis.

---

# 4. Architecture Principles

## 4.1 Separation of Responsibilities

| Capability | Primary Technology |
|---|---|
| Source-of-record data | PostgreSQL |
| Historical project data | PostgreSQL / data lake |
| Numerical prediction | ML models |
| Deterministic metrics | Python analytics/rules engine |
| Anomaly detection | Statistical/ML engine |
| Document retrieval | RAG |
| Semantic search | Vector database |
| External evidence | Web search |
| Reasoning/synthesis | LLM agents |
| Agent orchestration | Coordinator Agent / LangGraph or custom workflow |
| Tool access | MCP |
| Model lifecycle | MLflow/model registry |
| Observability | OpenTelemetry + Prometheus + Grafana + logs |
| Evaluation | Agent + ML evaluation suite |
| Cost attribution | Cost tracking service |
| Audit | Immutable audit records |

## 4.2 Point-in-Time Principle

For a prediction made at month **T**:

> Only information available on or before T may be used as predictive input.

No future revised cost, future completion date, future expenditure, or post-T event may leak into the model features.

## 4.3 Evidence Separation

Every conclusion must identify its origin:

- `PAIMANA_DATA`
- `ML_PREDICTION`
- `ANALYTICS`
- `REVIEW_REPORT`
- `WEB_EVIDENCE`
- `LLM_INFERENCE`
- `RULE_ENGINE`

The system must never present an LLM inference as an official project fact.

## 4.4 Human-in-the-Loop

The platform is a decision-support system.

The final authority remains with the authorized monitoring officer/decision maker.

---

# 5. High-Level Solution Architecture

```text
                           ┌─────────────────────────────┐
                           │        DECISION MAKER       │
                           │ Officer / Analyst / Admin   │
                           └──────────────┬──────────────┘
                                          │
                                          ▼
                           ┌─────────────────────────────┐
                           │       WEB APPLICATION        │
                           │ Dashboard + AI Assistant     │
                           └──────────────┬──────────────┘
                                          │
                                          ▼
                    ┌─────────────────────────────────────────┐
                    │          API / APPLICATION LAYER        │
                    │ Auth • RBAC • Session • Request Control │
                    └───────────────────┬─────────────────────┘
                                        │
                                        ▼
                         ┌─────────────────────────────┐
                         │       COORDINATOR AGENT     │
                         │ Planner / Router / State    │
                         └──────────────┬──────────────┘
                                        │
                 ┌──────────────────────┼───────────────────────┐
                 │                      │                       │
                 ▼                      ▼                       ▼
       ┌─────────────────┐   ┌─────────────────┐    ┌─────────────────┐
       │ DATA & HEALTH   │   │ PREDICTION &    │    │ INTELLIGENCE    │
       │ AGENT GROUP     │   │ ANOMALY GROUP   │    │ AGENT GROUP     │
       └────────┬────────┘   └────────┬────────┘    └────────┬────────┘
                │                     │                      │
                ▼                     ▼                      ▼
       History / Health       Cost / Time ML         Review / Web / Evidence
       Timeline / Metrics     Anomaly Detection     Intelligence
                │                     │                      │
                └─────────────────────┼──────────────────────┘
                                      ▼
                             ┌────────────────────┐
                             │ RISK FUSION AGENT  │
                             └─────────┬──────────┘
                                       ▼
                             ┌────────────────────┐
                             │ RISK DIAGNOSIS     │
                             │ Drivers / Causes   │
                             └─────────┬──────────┘
                                       ▼
                             ┌────────────────────┐
                             │ INTERVENTION AGENT │
                             └─────────┬──────────┘
                                       ▼
                             ┌────────────────────┐
                             │ REPORTING AGENT    │
                             └─────────┬──────────┘
                                       ▼
                             ┌────────────────────┐
                             │ DECISION PACKAGE   │
                             └────────────────────┘


       ============================================================
                            MCP CONTROL PLANE
       ============================================================

        PAIMANA MCP | ML MCP | Analytics MCP | Document MCP
        Web MCP | Knowledge MCP | Reporting MCP

       ============================================================
                               TOOLS
       ============================================================

        SQL | Feature Store | ML Model | Python
        Statistics | Rules | PDF | OCR | RAG
        Vector Search | Web Search | Source Verification
        Timeline | Evidence | Report Generation

       ============================================================
                         CROSS-CUTTING PLANE
       ============================================================

       Security | Guardrails | Audit | Evaluation
       Observability | Cost Tracking | Model Registry
       Prompt Registry | Configuration | Alerts
```

---

# 6. Logical Architecture Layers

The system is divided into the following layers.

```text
Layer 1   User Experience
Layer 2   API & Security
Layer 3   Coordinator / Agent Orchestration
Layer 4   Specialized Agents
Layer 5   MCP Capability Layer
Layer 6   Tools
Layer 7   Data / ML / RAG / Web Services
Layer 8   Persistence
Layer 9   Cross-Cutting Control Plane
```

---

# 7. Layer 1 – User Experience

## 7.1 Web Dashboard

Recommended technology:

- React
- Next.js
- TypeScript
- Tailwind CSS
- Charting library

### Dashboard views

1. Portfolio overview.
2. High-risk projects.
3. Cost-overrun risk.
4. Time-overrun risk.
5. Project health.
6. Expenditure vs progress.
7. Project timeline.
8. Risk drivers.
9. Review report findings.
10. External evidence.
11. Recommended interventions.
12. AI project assistant.
13. Historical trend.
14. What changed since last month.
15. Model explanation.
16. Evidence trace.
17. Agent execution trace for authorized users.

---

# 8. Layer 2 – API and Application Layer

Recommended technology:

- Python
- FastAPI
- Pydantic
- JWT/OAuth-compatible authentication
- PostgreSQL

## Responsibilities

- authentication;
- authorization;
- request validation;
- project lookup;
- analysis requests;
- report generation;
- session management;
- rate limiting;
- API versioning;
- audit logging;
- response formatting.

## Example APIs

```text
POST /api/v1/projects/{project_id}/analyse

GET  /api/v1/projects/{project_id}

GET  /api/v1/projects/{project_id}/history

GET  /api/v1/projects/{project_id}/health

GET  /api/v1/projects/{project_id}/predictions

GET  /api/v1/projects/{project_id}/risk

GET  /api/v1/projects/{project_id}/evidence

GET  /api/v1/projects/{project_id}/recommendations

GET  /api/v1/portfolio/risk

GET  /api/v1/traces/{trace_id}

GET  /api/v1/models

GET  /api/v1/evaluations
```

---

# 9. Layer 3 – Coordinator Agent

The Coordinator Agent is the central orchestration component.

It should **not perform all analysis itself**.

Its responsibilities are:

1. Understand the user request.
2. Identify project(s).
3. Determine required analysis.
4. Build execution plan.
5. Select appropriate agents.
6. Run independent tasks in parallel.
7. Maintain shared state.
8. Enforce budgets.
9. Handle failures.
10. Request additional analysis when evidence is insufficient.
11. Aggregate outputs.
12. Pass results to risk fusion.
13. Produce final decision package.

## 9.1 Coordinator Workflow

```text
User Query
   ↓
Intent Detection
   ↓
Project Identification
   ↓
Authorization Check
   ↓
Create Analysis Context
   ↓
Build Execution Plan
   ↓
Parallel Agent Execution
   ├── Data Intelligence
   ├── Project History
   ├── Health
   ├── Prediction
   ├── Anomaly
   ├── Review Report
   └── Web Intelligence
   ↓
Evidence Verification
   ↓
Risk Fusion
   ↓
Diagnosis
   ↓
Intervention
   ↓
Final Report
   ↓
Audit + Trace + Cost
   ↓
User
```

---

# 10. Agent Hierarchy

```text
COORDINATOR AGENT
│
├── DATA INTELLIGENCE AGENT
│   ├── Project Identification
│   ├── Data Validation
│   └── Data Completeness
│
├── PROJECT HISTORY AGENT
│   ├── Monthly History
│   ├── Event Reconstruction
│   └── Timeline Reconstruction
│
├── PROJECT HEALTH AGENT
│   ├── Cost Health
│   ├── Schedule Health
│   ├── Physical Progress
│   └── Expenditure-Progress Divergence
│
├── PREDICTION AGENT
│   ├── Cost Overrun Model
│   ├── Time Overrun Model
│   └── Risk Probability
│
├── ANOMALY AGENT
│   ├── Trend Anomaly
│   ├── Expenditure Anomaly
│   ├── Progress Anomaly
│   └── Behavioral Change
│
├── REVIEW REPORT AGENT
│   ├── Document Retrieval
│   ├── Project Mapping
│   └── Finding Extraction
│
├── WEB INTELLIGENCE AGENT
│   ├── Query Planning
│   ├── Search
│   ├── Source Filtering
│   └── Evidence Extraction
│
├── EVIDENCE AGENT
│   ├── Evidence Classification
│   ├── Source Verification
│   └── Confidence Assessment
│
├── RISK DIAGNOSIS AGENT
│   ├── Driver Identification
│   ├── Root Cause Analysis
│   └── Risk Narrative
│
├── INTERVENTION AGENT
│   ├── Recommended Action
│   ├── Monitoring Level
│   └── Escalation Recommendation
│
└── REPORTING AGENT
    ├── Executive Summary
    ├── Detailed Analysis
    └── Evidence-backed Report
```

---

# 11. Agent Responsibilities

## 11.1 Data Intelligence Agent

Inputs:

- project ID;
- monthly records;
- project master data.

Outputs:

```json
{
  "project_id": "617279",
  "data_quality": "GOOD",
  "latest_observation": "2023-12",
  "missing_fields": [],
  "observation_count": 30
}
```

It must not alter source-of-record data.

---

# 12. Project History Agent

Purpose:

> Answer “What happened to this project?”

It reconstructs:

- approval;
- original cost;
- original completion date;
- monthly expenditure;
- physical progress;
- revised values;
- milestones;
- status changes;
- important events.

Example output:

```text
Project History
----------------
Approval:
Original Cost:
Original Completion:
Latest Expenditure:
Latest Physical Progress:
Major Changes:
Timeline:
Risk-Relevant Events:
```

---

# 13. Project Health Agent

This is primarily a deterministic analytics component.

## 13.1 Cost Utilisation

```text
Cost Utilisation =
Cumulative Expenditure / Original Approved Cost × 100
```

## 13.2 Schedule Utilisation

```text
Schedule Utilisation =
Elapsed Project Duration / Original Project Duration × 100
```

## 13.3 Progress-Expenditure Divergence

```text
Divergence =
Cost Utilisation - Physical Progress
```

A large positive divergence can indicate that expenditure is progressing materially faster than physical progress.

This is a monitoring indicator, not automatically proof of inefficiency.

## 13.4 Schedule Progress

Where appropriate:

```text
Expected Progress =
Elapsed Duration / Planned Duration × 100
```

Then:

```text
Schedule Progress Gap =
Actual Physical Progress - Expected Progress
```

The calculation rules must be documented and versioned.

---

# 14. Prediction Agent

The Prediction Agent invokes registered ML models.

## 14.1 Cost Overrun Model

Input:

- point-in-time project features;
- historical observations;
- approved baseline;
- permitted engineered features.

Output:

```json
{
  "risk_type": "cost_overrun",
  "probability": 0.82,
  "risk_level": "HIGH",
  "prediction_horizon_months": 12,
  "model_version": "cost-risk-v3"
}
```

## 14.2 Time Overrun Model

Same architecture:

```json
{
  "risk_type": "time_overrun",
  "probability": 0.71,
  "risk_level": "HIGH",
  "prediction_horizon_months": 12,
  "model_version": "time-risk-v1"
}
```

## 14.3 Model Input Rule

The prediction service must enforce:

```text
feature_timestamp <= prediction_timestamp
```

Future observations must be rejected.

---

# 15. Anomaly Detection Agent

Anomaly detection is separate from supervised prediction.

It identifies unusual current behavior such as:

- sudden expenditure increase;
- unusual progress stagnation;
- unexpected change in monthly pattern;
- expenditure-progress mismatch;
- abnormal project trajectory.

Possible methods:

- Isolation Forest;
- robust z-score;
- rolling statistics;
- change-point detection;
- clustering;
- temporal anomaly models.

Output:

```json
{
  "anomaly": true,
  "type": "progress_expenditure_divergence",
  "severity": "HIGH",
  "detected_at": "2023-12",
  "explanation": "Expenditure increased substantially while physical progress remained comparatively low."
}
```

---

# 16. Review Report Intelligence Agent

The Review Report Agent handles official review documents.

## Pipeline

```text
PDF
 ↓
Document Validation
 ↓
Text Extraction
 ↓
OCR if required
 ↓
Page/section segmentation
 ↓
Project ID/entity extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Store
 ↓
Hybrid Retrieval
 ↓
Evidence Extraction
```

It should preserve:

- document name;
- page number;
- section;
- project identifier;
- source date;
- extracted statement;
- retrieval score.

The Review Report should be treated as supporting evidence and not automatically as an ML feature.

---

# 17. RAG Architecture

```text
             DOCUMENT INGESTION
                     │
        ┌────────────┼────────────┐
        ▼            ▼            ▼
      PDF          OCR        Metadata
        └────────────┼────────────┘
                     ▼
                  Chunking
                     ▼
                Embeddings
                     ▼
              Vector Database
                     │
             ┌───────┴────────┐
             ▼                ▼
       Semantic Search    Metadata Filter
             └───────┬────────┘
                     ▼
                Reranking
                     ▼
               Context Builder
                     ▼
                    LLM
                     ▼
          Citation-backed Answer
```

Recommended:

- PyMuPDF for PDF extraction;
- OCR where necessary;
- NVIDIA Nemotron 3 Embed 1B or equivalent embedding model;
- Qdrant or pgvector;
- optional reranker;
- page-aware metadata.

---

# 18. Web Intelligence Agent

The Web Intelligence Agent provides external context.

Potential topics:

- land acquisition;
- environmental/forest clearance;
- court cases;
- contractor issues;
- tender disputes;
- funding issues;
- utility shifting;
- local opposition;
- statutory approvals;
- construction constraints;
- major implementation events.

## Search workflow

```text
Project Context
     ↓
Query Planner
     ↓
Targeted Web Queries
     ↓
Search Results
     ↓
Source Quality Filter
     ↓
Source Verification
     ↓
Evidence Extraction
     ↓
Date Validation
     ↓
Evidence Store
```

Every external finding must contain:

```text
Source
Publication Date
Retrieved Date
Claim
Evidence
Project Relevance
Potential Impact
Confidence
```

The system should distinguish official sources from news reports and other secondary sources.

---

# 19. Evidence Agent

The Evidence Agent prevents unsupported claims.

## Evidence classes

| Class | Meaning |
|---|---|
| PAIMANA_DATA | Direct structured project data |
| REVIEW_REPORT | Official review-document evidence |
| WEB_EVIDENCE | External source evidence |
| ML_PREDICTION | Model-generated probability |
| ANALYTICS | Deterministic calculation |
| RULE_ENGINE | Explicit rule result |
| LLM_INFERENCE | Model-generated interpretation |

## Evidence policy

Every important risk statement should be traceable to one or more evidence objects.

---

# 20. Risk Fusion Architecture

Risk Fusion combines independent signals.

```text
                 ML Cost Risk
                      │
                 ML Time Risk
                      │
                Health Metrics
                      │
                Anomalies
                      │
                Project History
                      │
               Review Findings
                      │
                Web Evidence
                      │
                      ▼
               RISK FUSION ENGINE
                      │
          ┌───────────┼───────────┐
          ▼           ▼           ▼
       Cost Risk   Time Risk   Execution Risk
          └───────────┼───────────┘
                      ▼
                 Overall Risk
```

A risk score must not be an arbitrary LLM-generated number.

Where a combined score is used, its formula/weights must be explicit, versioned, and evaluated.

---

# 21. Risk Categories

Recommended categories:

```text
COST RISK
TIME RISK
PROGRESS RISK
EXPENDITURE RISK
MILESTONE RISK
IMPLEMENTATION RISK
EXTERNAL RISK
DATA CONFIDENCE
OVERALL PROJECT RISK
```

Example:

```json
{
  "cost_risk": 0.82,
  "time_risk": 0.71,
  "progress_risk": 0.76,
  "implementation_risk": 0.68,
  "overall_risk": 0.77,
  "risk_level": "HIGH"
}
```

---

# 22. Risk Diagnosis Agent

The Diagnosis Agent answers:

> Why is this project becoming risky?

It combines:

- model outputs;
- health metrics;
- trends;
- anomalies;
- history;
- review evidence;
- web evidence.

It should produce ranked drivers.

Example:

```text
Top Risk Drivers
1. High expenditure relative to physical progress
2. Persistent schedule progress gap
3. Repeated milestone slippage
4. External evidence of implementation constraints
5. Historical trajectory associated with overrun risk
```

Each driver must contain evidence and confidence.

---

# 23. Intervention Recommendation Agent

The Intervention Agent converts diagnosis into actionable recommendations.

Example mapping:

| Risk Driver | Potential Monitoring Action |
|---|---|
| Expenditure ahead of progress | Review expenditure vs physical achievement |
| Schedule gap | Review critical-path milestones |
| Land issue | Request land-acquisition status/action plan |
| Clearance issue | Track approval dependency |
| Contractor issue | Review contract/contractor status |
| Funding issue | Verify fund availability/release |
| Milestone slippage | Increase milestone monitoring frequency |

Recommendations should be framed as decision support, not autonomous government decisions.

---

# 24. Monitoring Level

The platform can classify projects into:

```text
NORMAL
WATCH
ELEVATED
HIGH
CRITICAL
```

Example policy:

```text
NORMAL
  ↓
Routine monitoring

WATCH
  ↓
Closer monthly review

ELEVATED
  ↓
Targeted review of identified drivers

HIGH
  ↓
Senior-level monitoring / intervention review

CRITICAL
  ↓
Immediate human review and escalation
```

The thresholds must be configurable and approved by project-monitoring authorities.

---

# 25. “What Changed Since Last Month?”

This should be a first-class capability.

The system compares:

```text
Current Month
      vs
Previous Month
      vs
Historical Trend
```

It reports:

- expenditure change;
- physical progress change;
- schedule gap change;
- risk probability change;
- new anomalies;
- new review findings;
- new web evidence;
- changed milestones;
- changed recommendations.

Example:

```text
Risk increased from MEDIUM to HIGH.

Key changes:
- Expenditure increased by X%.
- Physical progress increased by Y%.
- Progress-expenditure divergence widened.
- New milestone slippage detected.
- Cost-overrun probability increased from A to B.
```

---

# 26. MCP Architecture

MCP is used as the controlled capability boundary between agents and tools.

```text
                 AGENTS
                    │
                    ▼
             MCP CLIENT LAYER
                    │
       ┌────────────┼────────────┐
       ▼            ▼            ▼
 PAIMANA MCP     ML MCP     ANALYTICS MCP
       │            │            │
       ▼            ▼            ▼
      SQL        Models       Python/Rules

       ┌────────────┼────────────┐
       ▼            ▼            ▼
 DOCUMENT MCP    WEB MCP    KNOWLEDGE MCP
       │            │            │
       ▼            ▼            ▼
 PDF/OCR/RAG    Search      Vector DB
```

---

# 27. MCP Servers

## 27.1 PAIMANA MCP

Tools:

```text
get_project
get_project_history
get_monthly_observations
get_milestones
get_latest_status
get_project_metadata
```

## 27.2 ML MCP

Tools:

```text
predict_cost_risk
predict_time_risk
get_model_metadata
get_feature_schema
get_model_explanation
```

## 27.3 Analytics MCP

Tools:

```text
calculate_cost_utilisation
calculate_schedule_utilisation
calculate_progress_gap
calculate_expenditure_progress_divergence
calculate_trend
calculate_statistics
```

## 27.4 Document MCP

Tools:

```text
search_documents
retrieve_chunks
get_page
extract_project_findings
get_document_metadata
```

## 27.5 Web MCP

Tools:

```text
search_web
fetch_source
verify_source
extract_evidence
```

## 27.6 Knowledge MCP

Tools:

```text
vector_search
hybrid_search
retrieve_evidence
store_evidence
```

## 27.7 Reporting MCP

Tools:

```text
generate_summary
generate_pdf
generate_markdown
generate_json
```

---

# 28. Tool Security

Every tool call must pass:

```text
Agent Identity
      ↓
Authorization
      ↓
Tool Permission
      ↓
Input Validation
      ↓
Budget Check
      ↓
Tool Execution
      ↓
Output Validation
      ↓
Audit
```

Tools must be allow-listed.

Agents must never receive unrestricted database or operating-system access.

---

# 29. Tool Registry

Example:

```yaml
tool:
  name: predict_cost_risk
  server: ml-mcp
  permission: prediction.execute
  risk_level: medium
  timeout_seconds: 15
  cost_class: model_inference
  audit_required: true
```

---

# 30. Agent State Architecture

Use a shared structured state rather than uncontrolled conversational text.

Example:

```json
{
  "trace_id": "trace-123",
  "project_id": "617279",
  "analysis_date": "2023-12-31",
  "user_intent": "complete_project_risk_analysis",
  "project_data": {},
  "health_metrics": {},
  "predictions": {},
  "anomalies": [],
  "history": {},
  "review_evidence": [],
  "web_evidence": [],
  "risk_drivers": [],
  "recommendations": [],
  "confidence": {},
  "budget": {},
  "errors": []
}
```

---

# 31. Execution Graph

```text
START
  │
  ▼
Authenticate
  │
  ▼
Identify Project
  │
  ▼
Load Point-in-Time Dataset
  │
  ├───────────────┬────────────────┬────────────────┐
  ▼               ▼                ▼                ▼
History         Health         Prediction        Anomaly
  │               │                │                │
  └───────────────┴────────────────┴────────────────┘
                          │
                          ▼
                 Review Report Agent
                          │
                          ▼
                  Web Intelligence
                          │
                          ▼
                  Evidence Verification
                          │
                          ▼
                     Risk Fusion
                          │
                          ▼
                    Diagnosis
                          │
                          ▼
                   Intervention
                          │
                          ▼
                    Final Report
                          │
                          ▼
                 Trace + Audit + Cost
                          │
                          ▼
                         END
```

Independent branches should run in parallel where possible.

---

# 32. Failure and Graceful Degradation

The system must not fail completely when one intelligence source is unavailable.

Example:

```text
Web Search unavailable
       ↓
Continue with PAIMANA + ML + Review Report
       ↓
Mark external evidence unavailable
       ↓
Reduce confidence where appropriate
```

Similarly:

```text
Review Report unavailable
       ↓
Continue with structured data + ML + analytics
```

The final report must explicitly disclose missing evidence.

---

# 33. Data Architecture

## 33.1 Operational Database

Recommended:

**PostgreSQL**

Core tables:

```text
users
roles
permissions
projects
project_monthly_observations
project_milestones
project_events
predictions
risk_scores
risk_drivers
anomalies
recommendations
documents
document_chunks
evidence
agent_runs
tool_runs
traces
model_registry
feature_versions
audit_logs
cost_records
evaluation_runs
```

---

# 34. Data Flow Architecture

```text
PAIMANA / OCMS / CSV / API
          │
          ▼
     Raw Data Zone
          │
          ▼
    Data Validation
          │
          ▼
      Clean Dataset
          │
          ▼
 Temporal Feature Engineering
          │
     ┌────┴────┐
     ▼         ▼
 Feature     Analytics
 Store       Engine
     │         │
     ▼         ▼
 ML Engine   Health Engine
     │         │
     └────┬────┘
          ▼
      Risk Layer
```

---

# 35. Feature Store / Feature Management

Features should be versioned.

Example:

```text
feature_version = v3

features:
- cost_utilisation
- schedule_utilisation
- physical_progress
- expected_progress
- progress_gap
- expenditure_progress_divergence
- monthly_expenditure_growth
- progress_growth
- project_age
- remaining_duration
- sector
- ministry
```

The exact production feature list must be determined from the validated training dataset and leakage analysis.

---

# 36. ML Lifecycle

```text
Historical Data
     ↓
Data Cleaning
     ↓
Temporal Dataset Construction
     ↓
Feature Engineering
     ↓
Leakage Audit
     ↓
Train / Validation / Test
     ↓
Model Training
     ↓
Evaluation
     ↓
Calibration
     ↓
Model Registry
     ↓
Approval
     ↓
Deployment
     ↓
Prediction
     ↓
Monitoring
     ↓
Retraining
```

Recommended tools:

- scikit-learn;
- XGBoost/LightGBM where appropriate;
- MLflow.

---

# 37. ML Evaluation

Required metrics:

```text
ROC-AUC
PR-AUC
Precision
Recall
F1
Brier Score
Calibration
False Positive Rate
False Negative Rate
```

Use time-aware validation.

Example:

```text
Train:      Jan 2021 – Dec 2022
Validation: Jan 2023 – Jun 2023
Test:       Jul 2023 – Dec 2023
```

The actual periods should be determined from available data.

Do not randomly split temporal observations when that would create future-to-past leakage.

---

# 38. Agent Evaluation Suite

The system requires an independent evaluation framework.

## 38.1 Coordinator Evaluation

Measure:

- correct routing;
- correct tool selection;
- unnecessary tool calls;
- plan completeness;
- failure recovery;
- budget compliance.

## 38.2 History Agent Evaluation

Measure:

- factual accuracy;
- chronology accuracy;
- completeness;
- project identification accuracy.

## 38.3 RAG Evaluation

Measure:

- retrieval precision;
- retrieval recall;
- citation correctness;
- groundedness;
- answer relevance.

## 38.4 Web Agent Evaluation

Measure:

- source relevance;
- source quality;
- date correctness;
- claim/evidence matching;
- unsupported claim rate.

## 38.5 Intervention Evaluation

Measure:

- action relevance;
- driver-action consistency;
- completeness;
- human expert rating.

## 38.6 End-to-End Evaluation

Benchmark questions should include:

```text
What is the current project health?
What is the probability of cost overrun?
Why is the project high risk?
What changed this month?
What evidence supports the risk?
What intervention should be considered?
```

---

# 39. Evaluation Dataset

Maintain a golden dataset:

```text
evaluation/
├── coordinator_cases.jsonl
├── history_cases.jsonl
├── rag_cases.jsonl
├── web_cases.jsonl
├── prediction_cases.csv
├── diagnosis_cases.jsonl
├── intervention_cases.jsonl
└── end_to_end_cases.jsonl
```

Every model/agent release should be evaluated against this dataset.

---

# 40. Observability Architecture

Observability is a first-class architectural layer.

```text
                    APPLICATION
                        │
              ┌─────────┼─────────┐
              ▼         ▼         ▼
            Logs      Metrics    Traces
              │         │         │
              └─────────┼─────────┘
                        ▼
                 OpenTelemetry
                        │
          ┌─────────────┼─────────────┐
          ▼             ▼             ▼
     Prometheus       Grafana      Log Store
                                      │
                                      ▼
                                  Loki/ELK
```

---

# 41. Distributed Tracing

Each request receives:

```text
request_id
trace_id
session_id
user_id
project_id
analysis_id
```

Example:

```text
Trace
 ├── Coordinator
 │    ├── History Agent
 │    │    ├── PAIMANA MCP
 │    │    └── SQL Tool
 │    │
 │    ├── Prediction Agent
 │    │    └── ML MCP
 │    │         └── Model Inference
 │    │
 │    ├── Review Agent
 │    │    └── Document MCP
 │    │
 │    └── Web Agent
 │         └── Web MCP
 │
 ├── Risk Fusion
 └── Reporting
```

---

# 42. Observability Metrics

## System Metrics

```text
request_count
error_rate
latency
throughput
CPU
memory
database_latency
queue_depth
```

## Agent Metrics

```text
agent_runs
agent_success_rate
agent_failure_rate
agent_latency
agent_depth
tool_calls_per_agent
```

## LLM Metrics

Where provider telemetry is available:

```text
input_tokens
output_tokens
total_tokens
LLM_latency
model_name
model_version
```

## ML Metrics

```text
prediction_count
prediction_latency
model_version
prediction_distribution
drift indicators
```

---

# 43. Cost Tracking Architecture

Cost tracking must work at:

```text
User
 ↓
Request
 ↓
Analysis
 ↓
Agent
 ↓
Tool
 ↓
LLM/model/API call
```

Example:

```text
Analysis Cost
 ├── Coordinator LLM
 ├── History Agent LLM
 ├── Prediction inference
 ├── Review RAG
 │    ├── embedding
 │    └── LLM
 ├── Web search
 ├── Diagnosis LLM
 └── Reporting LLM
```

## Cost record

```json
{
  "trace_id": "trace-123",
  "agent": "diagnosis_agent",
  "provider": "provider-x",
  "model": "model-y",
  "input_tokens": 5000,
  "output_tokens": 1200,
  "tool_cost": 0.01,
  "estimated_cost": 0.04
}
```

---

# 44. Cost Controls

Every analysis should have configurable budgets.

```yaml
limits:
  max_execution_seconds: 120
  max_agent_depth: 5
  max_agent_turns: 30
  max_tool_calls: 50
  max_web_searches: 10
  max_llm_calls: 20
  max_cost_per_request: 1.00
```

If the budget is exceeded:

```text
Stop non-critical enrichment
        ↓
Preserve completed analysis
        ↓
Return partial result
        ↓
Explain unavailable components
```

---

# 45. Security Architecture

```text
User
 ↓
Authentication
 ↓
RBAC
 ↓
API Gateway
 ↓
Agent Authorization
 ↓
MCP Authorization
 ↓
Tool Permission
 ↓
Data Access
```

## Security requirements

- TLS;
- encrypted secrets;
- role-based access;
- least privilege;
- audit logging;
- input validation;
- output validation;
- prompt injection protection;
- SSRF protection for web tools;
- domain allow/deny controls where required;
- database parameterization;
- secure file handling;
- malware scanning where appropriate.

---

# 46. Prompt Injection Protection

Documents and websites must be treated as **untrusted content**.

Rules:

```text
Retrieved document text ≠ system instruction
Web page text ≠ agent instruction
PDF text ≠ tool permission
External content ≠ authorization
```

The system must not follow instructions found inside retrieved documents unless they are explicitly part of the user's task and safe to process.

---

# 47. Guardrails

## Input Guardrails

- project ID validation;
- query validation;
- authorization;
- request limits.

## Tool Guardrails

- allow-list;
- schema validation;
- timeout;
- rate limit;
- budget check.

## Output Guardrails

- JSON schema;
- evidence requirement;
- confidence;
- source attribution;
- hallucination checks.

---

# 48. Audit Architecture

Audit records should include:

```text
user
timestamp
project
request
agent
tool
model
model_version
input reference
output reference
decision
evidence
authorization result
```

The audit trail must support reconstruction of:

> Who asked what, which agents/tools ran, what data/model versions were used, and what evidence supported the response.

---

# 49. Storage Architecture

```text
                    STORAGE
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
   PostgreSQL       Object Store    Vector DB
        │              │              │
Structured Data     PDFs/Reports    Embeddings
Predictions         Raw Files       Chunks
Audit               Artifacts       Evidence
```

Recommended:

- PostgreSQL;
- MinIO/S3-compatible object storage;
- Qdrant or pgvector;
- Redis for caching/state where needed.

---

# 50. Cache Architecture

Use caching for:

- project metadata;
- historical project data;
- repeated RAG retrieval;
- repeated web results where policy permits;
- model metadata;
- configuration.

Do not cache sensitive or time-sensitive information beyond its defined freshness policy.

---

# 51. Event-Driven Extensions

For production scale, introduce an event bus.

```text
Data Updated
     ↓
Event Bus
     ↓
Prediction Job
     ↓
Health Calculation
     ↓
Risk Recalculation
     ↓
Alert Generation
```

Possible technology:

- Kafka;
- RabbitMQ;
- Redis Streams.

For an SIH prototype, this can initially be replaced by scheduled/background jobs.

---

# 52. Monthly Processing Pipeline

```text
Monthly Data Received
       ↓
Schema Validation
       ↓
Data Quality Check
       ↓
Project Matching
       ↓
Temporal Validation
       ↓
Feature Generation
       ↓
Prediction
       ↓
Health Calculation
       ↓
Anomaly Detection
       ↓
Risk Recalculation
       ↓
Changed-Risk Detection
       ↓
Alerts
       ↓
Dashboard Update
```

---

# 53. Portfolio Risk Architecture

Project-level risk can be aggregated by:

- ministry;
- sector;
- state;
- implementing agency;
- risk category;
- cost band;
- project age.

Portfolio dashboard:

```text
Total Projects
      │
      ├── Normal
      ├── Watch
      ├── Elevated
      ├── High
      └── Critical
```

Additional portfolio analytics:

```text
High cost-risk projects
High time-risk projects
Projects with worsening risk
Projects with abnormal divergence
Projects lacking recent data
Projects requiring human review
```

---

# 54. Alert Architecture

Alert types:

```text
NEW_HIGH_RISK
RISK_ESCALATION
COST_RISK_INCREASE
TIME_RISK_INCREASE
ANOMALY_DETECTED
MILESTONE_RISK
DATA_QUALITY_FAILURE
MODEL_FAILURE
AGENT_FAILURE
BUDGET_EXCEEDED
```

Alerts should contain:

```text
Project
Risk
Change
Reason
Evidence
Recommended next step
Timestamp
```

---

# 55. Reporting Architecture

The Reporting Agent creates:

## Executive Report

```text
Project
Overall Risk
Cost Risk
Time Risk
Key Changes
Top Drivers
Evidence
Recommended Actions
```

## Detailed Report

```text
Project Profile
Historical Timeline
Cost Analysis
Schedule Analysis
Physical Progress
Prediction
Anomalies
Review Findings
Web Evidence
Risk Diagnosis
Recommendations
Model Information
Evidence References
```

---

# 56. Complete Project Analysis Output

A project analysis response should contain:

```json
{
  "project": {},
  "data_quality": {},
  "health": {},
  "predictions": {},
  "anomalies": [],
  "history": {},
  "review_evidence": [],
  "web_evidence": [],
  "risk": {},
  "risk_drivers": [],
  "recommendations": [],
  "confidence": {},
  "model_versions": {},
  "trace_id": "trace-123"
}
```

---

# 57. Explainability Architecture

For ML:

- feature importance;
- SHAP where appropriate;
- probability;
- calibration;
- model version.

For analytics:

- formula;
- input values;
- calculation timestamp.

For RAG:

- document;
- page;
- section;
- chunk.

For web:

- source;
- publication date;
- extracted claim.

For LLM:

- evidence references;
- structured reasoning summary;
- no fabricated citations.

---

# 58. Model and Prompt Registry

Maintain versioning for:

```text
ML models
Prompts
Agent configurations
Tool schemas
Risk thresholds
Feature definitions
Evaluation datasets
```

Example:

```text
model_version: cost-risk-v3
prompt_version: diagnosis-v5
feature_version: features-v3
risk_policy_version: policy-v2
```

This enables reproducibility.

---

# 59. Deployment Architecture

## Development

```text
Docker Compose
 ├── frontend
 ├── api
 ├── coordinator
 ├── mcp servers
 ├── postgres
 ├── qdrant
 ├── redis
 ├── minio
 └── observability
```

## Production

```text
                 Load Balancer
                       │
                  API Gateway
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
     API Pods      Coordinator      Workers
                       │
             ┌─────────┼─────────┐
             ▼         ▼         ▼
           Agents    MCP Pods   Jobs
             │         │
             └─────────┼─────────┘
                       ▼
               Data Services
        ┌──────────┬──────────┬──────────┐
        ▼          ▼          ▼          ▼
    PostgreSQL   Vector DB  Object     Redis
                            Storage
```

Recommended production platform:

- Kubernetes;
- Docker;
- managed PostgreSQL where available;
- object storage;
- monitoring stack.

---

# 60. Repository Architecture

```text
project-monitoring-ai/
│
├── api/
│   ├── routes/
│   ├── schemas/
│   ├── middleware/
│   └── main.py
│
├── agents/
│   ├── coordinator/
│   ├── data_intelligence/
│   ├── history/
│   ├── health/
│   ├── prediction/
│   ├── anomaly/
│   ├── review/
│   ├── web/
│   ├── evidence/
│   ├── diagnosis/
│   ├── intervention/
│   └── reporting/
│
├── mcp_servers/
│   ├── paimana/
│   ├── ml/
│   ├── analytics/
│   ├── documents/
│   ├── web/
│   ├── knowledge/
│   └── reporting/
│
├── tools/
│   ├── database/
│   ├── ml/
│   ├── analytics/
│   ├── pdf/
│   ├── ocr/
│   ├── rag/
│   ├── web/
│   ├── evidence/
│   └── reporting/
│
├── models/
│   ├── training/
│   ├── inference/
│   ├── registry/
│   └── artifacts/
│
├── rag/
│   ├── ingestion/
│   ├── chunking/
│   ├── embeddings/
│   ├── retrieval/
│   └── reranking/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── features/
│   └── validation/
│
├── evaluation/
│   ├── datasets/
│   ├── agent_eval/
│   ├── rag_eval/
│   ├── ml_eval/
│   └── e2e/
│
├── observability/
│   ├── tracing/
│   ├── metrics/
│   └── logging/
│
├── cost_tracking/
│   ├── collectors/
│   ├── calculators/
│   └── reports/
│
├── security/
│   ├── auth/
│   ├── policies/
│   └── guardrails/
│
├── prompts/
│   ├── coordinator/
│   ├── diagnosis/
│   ├── intervention/
│   └── reporting/
│
├── configs/
│
├── migrations/
│
├── tests/
│   ├── unit/
│   ├── integration/
│   ├── security/
│   ├── performance/
│   └── e2e/
│
├── frontend/
│
├── docker/
├── k8s/
├── docs/
└── README.md
```

---

# 61. Recommended Technology Stack

| Layer | Recommended Technology |
|---|---|
| Frontend | React / Next.js |
| Backend | Python / FastAPI |
| Agent orchestration | LangGraph or custom state-machine orchestration |
| LLM | Open-source/approved LLM |
| ML | scikit-learn, XGBoost, LightGBM |
| Model registry | MLflow |
| MCP | MCP Python/TypeScript |
| Database | PostgreSQL |
| Vector DB | Qdrant / pgvector |
| Cache | Redis |
| Object storage | MinIO/S3 |
| PDF | PyMuPDF |
| OCR | Tesseract/PaddleOCR or approved equivalent |
| Embeddings | NVIDIA Nemotron 3 Embed 1B or equivalent |
| Search | Approved web search provider |
| API | FastAPI |
| Containers | Docker |
| Production | Kubernetes |
| Tracing | OpenTelemetry |
| Metrics | Prometheus |
| Dashboards | Grafana |
| Logs | Loki/ELK |
| Testing | pytest |
| CI/CD | GitHub Actions/GitLab CI/Jenkins |

---

# 62. End-to-End Example

User asks:

> “Give me the complete risk analysis for Project X.”

## Step 1 – Coordinator

Identifies intent:

```text
complete_project_risk_analysis
```

## Step 2 – Project Identification

Project ID is resolved.

## Step 3 – Data Intelligence

Retrieves latest valid point-in-time data.

## Step 4 – Parallel Analysis

```text
History Agent
Health Agent
Prediction Agent
Anomaly Agent
Review Agent
Web Agent
```

run concurrently where possible.

## Step 5 – Evidence

Evidence Agent verifies findings.

## Step 6 – Risk Fusion

Combines:

```text
Cost Prediction
Time Prediction
Health
Anomalies
History
Review
External Evidence
```

## Step 7 – Diagnosis

Produces ranked risk drivers.

## Step 8 – Intervention

Maps drivers to recommended monitoring actions.

## Step 9 – Reporting

Generates decision-ready report.

## Step 10 – Observability

Stores:

```text
trace
agent runs
tool runs
latencies
errors
tokens
cost
model versions
prompt versions
```

---

# 63. Example Decision Output

```text
PROJECT RISK: HIGH

Cost Overrun Risk: 82%
Time Overrun Risk: 71%

Key Indicators:
- Expenditure utilisation is high relative to physical progress.
- Schedule progress is below the expected trajectory.
- Recent monthly trend shows worsening divergence.
- An anomaly has been detected in the project trajectory.

Primary Risk Drivers:
1. Progress-expenditure divergence
2. Schedule progress gap
3. Historical trend
4. Review-report finding
5. External implementation evidence

Recommended Monitoring:
- Review expenditure against physical achievement.
- Review critical-path milestones.
- Validate current implementation constraints.
- Obtain updated action plan from implementing agency.

Evidence:
- Structured project data
- Historical project observations
- Review Report, page references
- External sources, where available

Model:
cost-risk-v3
time-risk-v1

Analysis Trace:
trace-123
```

The system must clearly label which statements are predictions, calculations, official evidence, external evidence, or LLM interpretation.

---

# 64. Performance Architecture

Target behavior:

| Operation | Target |
|---|---:|
| Simple project lookup | < 5 sec |
| Project analysis without web | < 30 sec |
| Complex analysis | < 60 sec |
| Batch prediction | Asynchronous |
| Dashboard query | < 3 sec |
| Vector retrieval | < 2 sec target |
| ML inference | < 5 sec target |

Targets should be validated during performance testing and adjusted according to deployment infrastructure.

---

# 65. Scalability

The architecture should support:

```text
~2,000 projects
       ↓
monthly observations
       ↓
batch prediction
       ↓
portfolio risk calculation
```

The agent layer should remain stateless where possible.

Long-running work should be delegated to workers.

---

# 66. Reliability

Required mechanisms:

- retries for transient failures;
- timeouts;
- circuit breakers where appropriate;
- idempotent jobs;
- queue-based background execution;
- checkpointed agent state;
- graceful degradation;
- health checks;
- database backups.

---

# 67. Backup and Disaster Recovery

Backup:

```text
PostgreSQL
Object Storage
Vector DB
Model Artifacts
Configuration
Evaluation Data
Audit Data
```

Recommended:

- daily database backups;
- versioned object storage;
- replicated critical data;
- tested restoration procedure.

---

# 68. CI/CD Architecture

```text
Developer
   ↓
Git
   ↓
Pull Request
   ↓
Unit Tests
   ↓
Lint / Type Check
   ↓
Security Scan
   ↓
Agent Evaluation
   ↓
ML Regression Evaluation
   ↓
Build Container
   ↓
Deploy Staging
   ↓
Integration Tests
   ↓
Approval
   ↓
Production
```

A model or prompt should not automatically reach production merely because application tests pass.

---

# 69. Testing Strategy

## Unit Tests

- formulas;
- feature engineering;
- model wrappers;
- parsers;
- tool schemas.

## Integration Tests

- API + database;
- agent + MCP;
- MCP + tools;
- RAG pipeline;
- ML inference.

## E2E Tests

```text
User
 → Coordinator
 → Agents
 → MCP
 → Tools
 → Risk
 → Report
```

## Security Tests

- authentication;
- authorization;
- prompt injection;
- SQL injection;
- SSRF;
- malicious documents;
- tool abuse.

## Performance Tests

- concurrent project analysis;
- portfolio queries;
- batch prediction;
- RAG retrieval;
- web search load.

---

# 70. Agent Quality Gates

An agent release must satisfy:

```text
Functional tests
      AND
Golden dataset evaluation
      AND
Safety evaluation
      AND
Cost budget
      AND
Latency target
      AND
Regression threshold
```

Otherwise it should not be promoted.

---

# 71. Data Quality Gates

Before prediction:

```text
Schema Valid
   AND
Project ID Valid
   AND
Observation Date Valid
   AND
No Future Data
   AND
Required Features Available
   AND
Feature Version Supported
```

If a mandatory condition fails:

```text
Prediction = NOT_AVAILABLE
Reason = DATA_QUALITY_FAILURE
```

Never fabricate a prediction.

---

# 72. Confidence Architecture

Confidence should be represented separately for:

```text
Prediction confidence
Data confidence
Evidence confidence
Diagnosis confidence
Recommendation confidence
```

Example:

```json
{
  "prediction_confidence": 0.86,
  "data_confidence": 0.94,
  "evidence_confidence": 0.79,
  "diagnosis_confidence": 0.76
}
```

These numbers should only be shown if they have a defined calculation/interpretation.

---

# 73. Key Architectural Decisions

## Decision 1

**Use ML for prediction, not the LLM.**

## Decision 2

**Use deterministic analytics for baseline/project-health calculations.**

## Decision 3

**Use RAG for long Review Reports and other documents.**

## Decision 4

**Use web search for external implementation context.**

## Decision 5

**Use MCP as the controlled tool boundary.**

## Decision 6

**Use a Coordinator Agent for orchestration.**

## Decision 7

**Use independent evaluation, observability, cost, and audit layers.**

## Decision 8

**Use point-in-time data for all predictive features.**

---

# 74. What Should NOT Be an Agent

Not every component needs an LLM.

Do **not** use an agent for:

```text
Cost utilisation calculation
Schedule utilisation calculation
Progress gap calculation
Database CRUD
ML inference
Statistical anomaly score
Schema validation
Authentication
Authorization
Budget arithmetic
```

These should be deterministic services/tools.

Agents should be used where planning, interpretation, synthesis, or evidence reasoning is actually needed.

---

# 75. Agent vs Tool Boundary

```text
AGENT
Reasoning
Planning
Routing
Synthesis
Interpretation
Recommendation

TOOL
Query
Calculate
Predict
Retrieve
Search
Extract
Store
Validate
```

Example:

```text
Prediction Agent
       ↓
ML MCP
       ↓
predict_cost_risk()
       ↓
ML Model
```

The agent decides **when and why** to call the prediction tool.

The tool performs the actual prediction.

---

# 76. Complete Control Plane

The production architecture should include the following control plane:

```text
┌─────────────────────────────────────────────────────────┐
│                    CONTROL PLANE                        │
├─────────────────────────────────────────────────────────┤
│ Security & RBAC                                         │
│ Guardrails                                               │
│ Audit                                                    │
│ Agent Evaluation                                         │
│ ML Evaluation                                            │
│ Observability                                            │
│ Cost Tracking                                            │
│ Model Registry                                           │
│ Prompt Registry                                          │
│ Tool Registry                                            │
│ Configuration Management                                 │
│ Data Quality                                             │
│ Alerting                                                 │
└─────────────────────────────────────────────────────────┘
```

---

# 77. Final Reference Architecture

```text
                                      USER
                                       │
                                       ▼
                            ┌────────────────────┐
                            │ WEB DASHBOARD / AI  │
                            │ PROJECT ASSISTANT   │
                            └──────────┬─────────┘
                                       │
                                       ▼
                            ┌────────────────────┐
                            │ API + AUTH + RBAC  │
                            └──────────┬─────────┘
                                       │
                                       ▼
                     ┌────────────────────────────────┐
                     │       COORDINATOR AGENT        │
                     │ Planner • Router • State       │
                     └───────────────┬────────────────┘
                                     │
              ┌──────────────────────┼───────────────────────┐
              │                      │                       │
              ▼                      ▼                       ▼
      ┌───────────────┐      ┌───────────────┐      ┌────────────────┐
      │ DATA / HEALTH │      │ PREDICTION /  │      │ INTELLIGENCE   │
      │ AGENTS        │      │ ANOMALY AGENTS│      │ AGENTS         │
      └───────┬───────┘      └───────┬───────┘      └───────┬────────┘
              │                      │                       │
       ┌──────┼──────┐        ┌──────┼──────┐         ┌────┼─────┐
       ▼      ▼      ▼        ▼      ▼      ▼         ▼    ▼     ▼
    History Health Timeline  Cost   Time  Anomaly   Review Web Evidence
       │      │      │        │      │      │         │    │
       └──────┴──────┴────────┴──────┴──────┴─────────┴────┘
                              │
                              ▼
                    ┌─────────────────────┐
                    │   EVIDENCE AGENT    │
                    │ Verify / Classify   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │   RISK FUSION       │
                    │ Cost / Time / Exec  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │  RISK DIAGNOSIS     │
                    │ Drivers / Causes    │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ INTERVENTION AGENT  │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │ REPORTING AGENT     │
                    └──────────┬──────────┘
                               │
                               ▼
                         DECISION MAKER


═══════════════════════════════════════════════════════════════════
                         MCP LAYER
═══════════════════════════════════════════════════════════════════

 PAIMANA MCP | ML MCP | Analytics MCP | Document MCP
 Web MCP | Knowledge MCP | Reporting MCP


═══════════════════════════════════════════════════════════════════
                          TOOL LAYER
═══════════════════════════════════════════════════════════════════

 SQL | Feature Store | ML Models | Python
 Statistics | Rules | PDF | OCR
 Vector Search | RAG | Web Search
 Source Verification | Timeline | Reporting


═══════════════════════════════════════════════════════════════════
                          DATA LAYER
═══════════════════════════════════════════════════════════════════

 PostgreSQL | Qdrant/pgvector | MinIO/S3 | Redis
 PAIMANA/OCMS | Flash Reports | Review Reports
 ML Artifacts | Evaluation Data


═══════════════════════════════════════════════════════════════════
                       CONTROL PLANE
═══════════════════════════════════════════════════════════════════

 Evaluation | Observability | Cost Tracking
 Security | Guardrails | Audit
 Model Registry | Prompt Registry | Tool Registry
 Data Quality | Alerts | Configuration
```

---

# 78. Implementation Phases

## Phase 1 – Data Foundation

- ingest Flash Reports;
- clean and normalize data;
- project identity resolution;
- monthly observation model;
- PostgreSQL schema;
- data quality checks.

## Phase 2 – ML Foundation

- reproduce current cost-overrun model;
- point-in-time feature pipeline;
- model registry;
- inference service;
- ML evaluation.

## Phase 3 – Project Intelligence

- project history;
- health metrics;
- timeline;
- anomaly detection;
- “what changed.”

## Phase 4 – RAG

- Review Report ingestion;
- OCR;
- chunking;
- embeddings;
- vector database;
- citations.

## Phase 5 – Agent Layer

- Coordinator;
- History;
- Health;
- Prediction;
- Review;
- Evidence;
- Diagnosis;
- Intervention;
- Reporting.

## Phase 6 – MCP

- PAIMANA MCP;
- ML MCP;
- Analytics MCP;
- Document MCP;
- Web MCP;
- Knowledge MCP.

## Phase 7 – Web Intelligence

- targeted search;
- source verification;
- evidence storage;
- external risk enrichment.

## Phase 8 – Control Plane

- observability;
- evaluation suite;
- cost tracking;
- audit;
- guardrails.

## Phase 9 – Dashboard

- portfolio dashboard;
- project dashboard;
- AI assistant;
- alerts;
- risk visualization.

## Phase 10 – Production Hardening

- security;
- performance;
- scalability;
- disaster recovery;
- CI/CD;
- Kubernetes deployment.

---

# 79. SIH Demonstration Flow

For the hackathon demonstration, use one project.

```text
1. Select Project
        ↓
2. Show historical project timeline
        ↓
3. Show current cost/progress health
        ↓
4. Run ML prediction
        ↓
5. Show cost-overrun probability
        ↓
6. Show time/risk indicators
        ↓
7. Show anomaly
        ↓
8. Retrieve relevant Review Report evidence
        ↓
9. Search relevant external evidence
        ↓
10. Diagnose top risk drivers
        ↓
11. Generate recommended interventions
        ↓
12. Show evidence-backed final decision
        ↓
13. Open trace showing agents → MCP → tools
        ↓
14. Show evaluation score / model version / cost
```

This demonstrates that the solution is not simply a chatbot.

It is a complete **predictive project-monitoring intelligence platform**.

---

# 80. Final Architecture Statement

The proposed system is a **hybrid agentic decision-support architecture**.

Its core design is:

```text
Historical Project Data
        +
Current Project Data
        +
ML Prediction
        +
Deterministic Health Analytics
        +
Anomaly Detection
        +
Project History
        +
Review Report RAG
        +
External Web Intelligence
        +
Evidence Verification
        +
Risk Diagnosis
        +
Intervention Recommendation
        ↓
AI-Powered Project Decision Intelligence
```

The Coordinator Agent provides orchestration, but it does not replace specialized computational services.

MCP provides a controlled interface between agents and tools.

The evaluation suite validates both ML and agentic behavior.

Observability provides complete execution visibility.

Cost tracking provides per-request and per-agent resource attribution.

Security, audit, guardrails, model registry, prompt registry, and data-quality controls make the architecture suitable for controlled deployment.

The central outcome is:

> **Identify potentially problematic projects early, explain why they are becoming risky, provide evidence, and recommend where monitoring attention should be focused before cost or schedule overruns fully materialize.**

---

# 81. Architecture Success Criteria

The architecture is considered successful when it can:

- ingest and validate historical project observations;
- produce point-in-time predictions without future-data leakage;
- calculate project health deterministically;
- detect abnormal trajectories;
- reconstruct project history;
- retrieve relevant official report evidence;
- retrieve relevant external evidence;
- distinguish facts from predictions and inference;
- diagnose risk drivers;
- recommend appropriate monitoring actions;
- expose controlled capabilities through MCP;
- execute agents with traceability;
- measure agent/model quality;
- measure operational performance;
- attribute AI/tool costs;
- provide auditable decision-support outputs;
- degrade gracefully when enrichment sources are unavailable;
- scale from a single-project demonstration to portfolio-level monitoring.

---

# 82. One-Line Architecture

> **PAIMANA/OCMS Data + ML + Health Analytics + Anomaly Detection + Project History + Review-Report RAG + Web Intelligence → Coordinator Agent → Evidence Verification → Risk Fusion → Diagnosis → Intervention → Decision Dashboard, governed by MCP, Evaluation, Observability, Cost, Security, and Audit Control Planes.**
