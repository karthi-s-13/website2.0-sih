# Software Requirements Specification (SRS)

# AI-Powered Predictive Project Monitoring & Decision Intelligence Platform

**Project:** SIH 2.0 -- MoSPI / IPMD\
**Document Type:** Software Requirements Specification\
**Version:** 1.0\
**Status:** Proposed\
**Architecture:** Multi-Agent + MCP + ML + RAG + Analytics\
**Primary Pattern:** Coordinator Agent → Specialist Agents → MCP Servers
→ Tools\
**Document Purpose:** Define the functional, non-functional, technical,
integration, data, security, observability, evaluation, and operational
requirements for implementation.

------------------------------------------------------------------------

# 1. Introduction

## 1.1 Purpose

This Software Requirements Specification defines the requirements for an
AI-powered predictive project-monitoring platform designed to support
infrastructure project monitoring.

The system shall combine structured project data, historical monthly
observations, machine-learning prediction, deterministic project-health
analytics, anomaly detection, document intelligence, web intelligence,
evidence verification, risk diagnosis, intervention recommendations, and
decision-support reporting.

The system shall follow:

> **Predict → Diagnose → Verify → Prescribe → Monitor**

This document converts the product requirements into
implementation-oriented software requirements.

------------------------------------------------------------------------

## 1.2 Scope

The software shall provide:

1.  Project identification and retrieval.
2.  Longitudinal project-history reconstruction.
3.  Project-health calculation.
4.  Cost-overrun prediction.
5.  Time-overrun prediction capability.
6.  Anomaly detection.
7.  Review-report intelligence.
8.  RAG-based document retrieval.
9.  Web intelligence.
10. Evidence verification.
11. Risk fusion and diagnosis.
12. Intervention recommendation.
13. Monthly change detection.
14. Project-level reporting.
15. Portfolio-level analytics.
16. Conversational project analysis.
17. MCP-based controlled tool access.
18. Agent evaluation.
19. End-to-end observability.
20. LLM/tool cost tracking.
21. Authentication, authorization, guardrails and auditability.

------------------------------------------------------------------------

# 2. Definitions and Acronyms

  -----------------------------------------------------------------------
  Term                                Definition
  ----------------------------------- -----------------------------------
  PAIMANA                             Project monitoring platform/data
                                      source used by the system

  IPMD                                Infrastructure & Project Monitoring
                                      Division

  MoSPI                               Ministry of Statistics and
                                      Programme Implementation

  OCMS                                Earlier project monitoring
                                      repository

  ML                                  Machine Learning

  LLM                                 Large Language Model

  RAG                                 Retrieval-Augmented Generation

  MCP                                 Model Context Protocol

  Agent                               Specialized software component
                                      capable of planning/reasoning/tool
                                      use

  Coordinator Agent                   Primary orchestration agent

  Tool                                Deterministic executable capability

  Risk Score                          Normalized project risk indicator

  Snapshot Month                      Date/month at which a prediction is
                                      generated

  Point-in-Time                       Using only information available at
                                      the prediction timestamp

  Evidence                            Information supporting a claim

  Feature                             Input variable used by an ML model

  MCP Server                          Controlled gateway exposing
                                      tools/resources to agents

  Trace                               End-to-end execution record

  RBAC                                Role-Based Access Control

  P95                                 95th percentile latency

  PRD                                 Product Requirements Document

  SRS                                 Software Requirements Specification
  -----------------------------------------------------------------------

------------------------------------------------------------------------

# 3. System Objectives

## 3.1 Primary Objective

The system shall identify projects that are likely to experience future
cost or schedule problems before those problems materially occur.

## 3.2 Secondary Objectives

The system shall:

-   Explain why a project is risky.
-   Show historical project behavior.
-   Detect abnormal current behavior.
-   Retrieve supporting evidence.
-   Identify external issues.
-   Recommend monitoring/intervention actions.
-   Track changes month over month.
-   Provide portfolio-level risk intelligence.
-   Maintain complete execution traces.
-   Measure agent quality.
-   Track operational cost.

------------------------------------------------------------------------

# 4. System Context

``` text
                         USER
                           |
                           v
                    WEB APPLICATION
                           |
                           v
                     API GATEWAY
                           |
                           v
                  COORDINATOR AGENT
                           |
        +------------------+------------------+
        |                  |                  |
        v                  v                  v
   DATA AGENTS        ML/HEALTH AGENTS   INTELLIGENCE AGENTS
        |                  |                  |
        +------------------+------------------+
                           |
                           v
                    RISK DIAGNOSIS
                           |
                           v
                  EVIDENCE VERIFICATION
                           |
                           v
                    INTERVENTION
                           |
                           v
                     REPORTING
                           |
                           v
                     USER/DASHBOARD


                    MCP LAYER
        +------------+------------+------------+
        |            |            |            |
     PAIMANA       ML         ANALYTICS     DOCUMENT
        |            |            |            |
      WEB        KNOWLEDGE      TOOLS        TOOLS


                CONTROL PLANE
        Evaluation | Observability | Cost
        Security   | Audit          | Governance
```

------------------------------------------------------------------------

# 5. User Roles

## 5.1 Administrator

Permissions:

-   Manage users.
-   Manage roles.
-   Configure system.
-   Manage agent configuration.
-   Manage MCP servers.
-   View system health.
-   View cost information.
-   View evaluation results.
-   Manage model registry.

## 5.2 Monitoring Officer

Permissions:

-   Search projects.
-   View project details.
-   Run project analysis.
-   View risk.
-   View evidence.
-   View recommendations.
-   View project history.

## 5.3 Senior Decision Maker

Permissions:

-   All officer functions.
-   Portfolio analysis.
-   Risk ranking.
-   Ministry/sector analytics.
-   Executive reports.
-   Alerts.

## 5.4 Analyst

Permissions:

-   Project search.
-   Historical analysis.
-   Analytics.
-   Reports.
-   Evidence retrieval.

## 5.5 Auditor

Permissions:

-   Read-only access to:
    -   Audit records
    -   Agent traces
    -   Evidence
    -   Predictions
    -   Model versions
    -   System decisions

------------------------------------------------------------------------

# 6. Functional Requirements

# FR-001 User Authentication

The system shall authenticate users before accessing protected
functions.

### Requirements

-   Support secure login.
-   Maintain user session.
-   Enforce role-based permissions.
-   Reject unauthorized requests.
-   Record authentication events.

------------------------------------------------------------------------

# FR-002 Role-Based Access Control

The system shall enforce permissions based on user role.

### Requirements

-   Each API endpoint shall define required permission.
-   Each agent shall define permitted tools.
-   Each MCP server shall enforce tool permissions.
-   Unauthorized tool execution shall be rejected.

------------------------------------------------------------------------

# FR-003 Project Search

The system shall allow users to search projects.

### Search parameters

-   Project ID
-   Project name
-   Ministry
-   Department
-   Agency
-   State
-   Sector
-   Risk level
-   Date
-   Status

### Natural-language search

Example:

> Show high-risk projects where expenditure is high but physical
> progress is low.

------------------------------------------------------------------------

# FR-004 Project Identification

The Project Identification Agent shall identify the canonical project
record.

### Inputs

-   Project ID
-   Project name
-   Natural-language query
-   Ministry
-   Agency
-   State

### Outputs

``` json
{
  "project_id": "...",
  "project_name": "...",
  "ministry": "...",
  "agency": "...",
  "state": "...",
  "sector": "...",
  "confidence": 0.99
}
```

------------------------------------------------------------------------

# FR-005 Project Metadata Retrieval

The system shall retrieve:

-   Project name
-   Project ID
-   Ministry
-   Department
-   Agency
-   Sector
-   State
-   Original cost
-   Revised cost
-   Original start date
-   Original completion date
-   Revised completion date where available
-   Current status

------------------------------------------------------------------------

# FR-006 Project History

The Project History Agent shall reconstruct chronological project
history.

### Requirements

The system shall:

-   Retrieve monthly observations.
-   Sort observations chronologically.
-   Detect significant changes.
-   Track expenditure.
-   Track physical progress.
-   Track milestones.
-   Track revisions.
-   Track status changes.

### Output

The system shall provide both structured data and natural-language
summary.

------------------------------------------------------------------------

# FR-007 Project Timeline

The Project Timeline Agent shall generate a timeline of important
events.

Example:

``` text
Approval
  ↓
Project Execution
  ↓
Progress Update
  ↓
Milestone Delay
  ↓
Progress Slowdown
  ↓
Expenditure Acceleration
  ↓
Review Observation
  ↓
Risk Escalation
```

------------------------------------------------------------------------

# FR-008 Project Health Calculation

The system shall calculate project-health indicators deterministically.

## Required metrics

### Cost Utilisation

``` text
Cumulative Expenditure / Original Approved Cost
```

### Schedule Utilisation

``` text
Elapsed Duration / Original Project Duration
```

### Progress Gap

``` text
Expected Physical Progress - Actual Physical Progress
```

### Expenditure-Progress Divergence

``` text
Expenditure Utilisation - Physical Progress
```

### Trend indicators

The system shall calculate:

-   Monthly progress change.
-   Monthly expenditure change.
-   Progress slope.
-   Expenditure slope.
-   Acceleration/deceleration.
-   Consecutive stagnant months.

------------------------------------------------------------------------

# FR-009 Expected Progress Calculation

The system shall support a configurable expected-progress calculation.

The calculation method shall be explicitly versioned.

The method must account for:

-   Original start date.
-   Original completion date.
-   Snapshot date.

Future information shall not be used when calculating a historical
snapshot.

------------------------------------------------------------------------

# FR-010 Cost-Overrun Prediction

The system shall provide cost-overrun probability using a registered ML
model.

### Input requirements

Features must correspond to information available at or before the
snapshot month.

### Output

``` json
{
  "project_id": "...",
  "snapshot_month": "...",
  "probability": 0.82,
  "horizon_months": 12,
  "model_version": "cost-overrun-v3"
}
```

### Mandatory metadata

-   Model ID
-   Model version
-   Feature version
-   Snapshot month
-   Prediction timestamp
-   Prediction horizon

------------------------------------------------------------------------

# FR-011 Time-Overrun Prediction

The system shall support a time-overrun prediction model.

The implementation shall support:

-   Probability of future time overrun.
-   Expected delay duration where a validated model is available.
-   Model versioning.
-   Point-in-time features.

------------------------------------------------------------------------

# FR-012 Input Validation for ML

Before invoking an ML model, the system shall verify:

-   Required fields exist.
-   Data types are valid.
-   Values are within expected ranges.
-   Snapshot month is valid.
-   Feature version is compatible.
-   Model version is available.
-   No future feature is included.

Invalid input shall not be sent to the model.

------------------------------------------------------------------------

# FR-013 Model Registry

The system shall maintain a registry containing:

-   Model ID.
-   Version.
-   Training period.
-   Dataset identifier.
-   Feature set.
-   Target definition.
-   Prediction horizon.
-   Validation metrics.
-   Calibration metrics.
-   Deployment status.
-   Creation date.
-   Approval status.

------------------------------------------------------------------------

# FR-014 Anomaly Detection

The system shall identify unusual project behavior.

### Required anomaly types

-   Expenditure acceleration.
-   Progress stagnation.
-   Sudden progress decline.
-   Expenditure-progress divergence.
-   Schedule deterioration.
-   Unexpected milestone changes.

The anomaly engine shall return:

``` json
{
  "anomaly_detected": true,
  "anomaly_type": "...",
  "severity": "HIGH",
  "score": 0.91,
  "evidence": []
}
```

------------------------------------------------------------------------

# FR-015 Review Report Processing

The system shall ingest review reports.

### Processing pipeline

``` text
PDF
 ↓
Parser/OCR
 ↓
Page Extraction
 ↓
Table Extraction
 ↓
Chunking
 ↓
Metadata Enrichment
 ↓
Embedding
 ↓
Vector Database
```

------------------------------------------------------------------------

# FR-016 Document Metadata

Each indexed document chunk shall support metadata such as:

-   Document ID
-   Document name
-   Document date
-   Page number
-   Project ID
-   Ministry
-   Sector
-   Document type
-   Source type
-   Upload date

------------------------------------------------------------------------

# FR-017 Review Evidence Retrieval

The Review Report Agent shall retrieve project-specific findings.

### Output

``` json
{
  "project_id": "...",
  "finding": "...",
  "report_name": "...",
  "report_date": "...",
  "page": 127,
  "severity": "HIGH",
  "source_type": "OFFICIAL_REPORT"
}
```

------------------------------------------------------------------------

# FR-018 RAG Retrieval

The RAG system shall support:

-   Semantic retrieval.
-   Metadata filtering.
-   Top-K retrieval.
-   Optional reranking.
-   Source/page preservation.
-   Project-specific filtering.

The system shall not treat retrieved text as verified fact without
source attribution.

------------------------------------------------------------------------

# FR-019 Web Intelligence

The Web Intelligence Agent shall search external information.

### Search categories

-   Land acquisition.
-   Environmental clearance.
-   Forest clearance.
-   Court cases.
-   Contractor issues.
-   Tender issues.
-   Funding.
-   Utility shifting.
-   Regulatory approvals.
-   Local issues.
-   Natural events.
-   Construction bottlenecks.

### Web result requirements

Each relevant result should contain:

-   Source.
-   Title.
-   Publication date where available.
-   Finding.
-   Relevance.
-   Potential project impact.
-   Source confidence.

------------------------------------------------------------------------

# FR-020 Web Evidence Verification

External information shall be explicitly classified as external
evidence.

The system shall not represent an unverified external statement as an
official project fact.

------------------------------------------------------------------------

# FR-021 Evidence Classification

Every major claim shall support a source category:

``` text
OBSERVED
DERIVED
PREDICTED
OFFICIAL_EVIDENCE
EXTERNAL_EVIDENCE
RECOMMENDATION
```

------------------------------------------------------------------------

# FR-022 Evidence Verification

The Evidence Verification Agent shall validate important claims.

It shall check:

-   Source existence.
-   Source relevance.
-   Source type.
-   Numerical consistency.
-   Citation availability.
-   Evidence-to-claim relationship.

------------------------------------------------------------------------

# FR-023 Risk Diagnosis

The Risk Diagnosis Agent shall combine:

-   ML predictions.
-   Project health.
-   Anomalies.
-   Historical trends.
-   Milestone performance.
-   Review evidence.
-   External evidence.

It shall produce:

-   Overall risk.
-   Risk score.
-   Confidence.
-   Risk drivers.
-   Evidence references.

------------------------------------------------------------------------

# FR-024 Risk Fusion

The system shall support configurable risk fusion.

Possible inputs:

``` text
Cost ML Risk
Time ML Risk
Financial Health
Schedule Health
Progress Health
Milestone Risk
Anomaly Risk
Review Risk
External Risk
```

Risk weights and thresholds must be configurable and versioned.

------------------------------------------------------------------------

# FR-025 Risk Classification

The default configurable classification shall support:

``` text
0–29    LOW
30–49   MODERATE
50–69   ELEVATED
70–84   HIGH
85–100  CRITICAL
```

Actual thresholds shall be validated using historical evaluation data.

------------------------------------------------------------------------

# FR-026 Risk Driver Identification

The system shall identify the most important risk drivers.

Example:

``` text
1. Progress lag
2. Expenditure-progress divergence
3. Milestone slippage
4. Recent deterioration
5. External constraint
```

------------------------------------------------------------------------

# FR-027 Intervention Recommendation

The Intervention Agent shall generate recommendations based on diagnosed
risk.

Each recommendation shall contain:

-   Risk driver.
-   Recommended action.
-   Priority.
-   Reason.
-   Evidence.
-   Suggested monitoring level.

The agent shall not claim that an action has been performed unless an
authorized tool confirms it.

------------------------------------------------------------------------

# FR-028 Monitoring Level

The system shall support:

``` text
NORMAL
ENHANCED
PRIORITY
CRITICAL
```

Monitoring levels shall be configurable.

------------------------------------------------------------------------

# FR-029 What Changed

The system shall compare two project snapshots.

Required comparisons:

-   Physical progress.
-   Expenditure.
-   Risk score.
-   Cost probability.
-   Time probability.
-   Milestones.
-   Status.
-   New evidence.
-   New anomalies.

------------------------------------------------------------------------

# FR-030 Portfolio Analytics

The system shall support:

-   High-risk project count.
-   Critical project count.
-   Ministry risk distribution.
-   Sector risk distribution.
-   State risk distribution.
-   Cost-risk distribution.
-   Time-risk distribution.
-   Risk trend.
-   New risk escalations.

------------------------------------------------------------------------

# FR-031 Coordinator Agent

The Coordinator Agent shall:

1.  Understand the user request.
2.  Identify project(s).
3.  Create an execution plan.
4.  Select agents.
5.  Execute independent tasks in parallel where possible.
6.  Manage dependencies.
7.  Maintain shared state.
8.  Validate outputs.
9.  Request missing information.
10. Resolve conflicting outputs.
11. Generate final structured response.
12. Record execution trace.

------------------------------------------------------------------------

# FR-032 Agent Routing

The Coordinator shall route tasks according to intent.

Example:

``` text
"What is project history?"
    → History Agent

"Will cost overrun occur?"
    → Prediction Agent

"Why is risk high?"
    → Health + Prediction + Evidence + Diagnosis

"What changed?"
    → History + Comparison

"What should we do?"
    → Diagnosis + Intervention
```

------------------------------------------------------------------------

# FR-033 Parallel Agent Execution

Independent tasks shall be executed concurrently where safe.

Example:

``` text
History
Health
Prediction
Review Search
Web Search
```

may run in parallel.

Dependent tasks shall wait for prerequisite results.

------------------------------------------------------------------------

# FR-034 Agent State

The Coordinator shall maintain structured execution state.

``` json
{
  "trace_id": "...",
  "project_id": "...",
  "user_request": "...",
  "plan": [],
  "agent_results": {},
  "evidence": [],
  "predictions": {},
  "health_metrics": {},
  "risk": {},
  "recommendations": []
}
```

------------------------------------------------------------------------

# FR-035 MCP Architecture

All external capabilities shall be exposed through controlled MCP
servers.

Required MCP servers:

1.  PAIMANA MCP Server
2.  ML MCP Server
3.  Analytics MCP Server
4.  Document MCP Server
5.  Web Intelligence MCP Server
6.  Knowledge MCP Server

------------------------------------------------------------------------

# FR-036 PAIMANA MCP

Required tools:

``` text
get_project()
search_projects()
get_project_metadata()
get_latest_project_status()
get_project_monthly_history()
get_project_financial_history()
get_project_progress_history()
get_project_milestones()
compare_project_months()
```

------------------------------------------------------------------------

# FR-037 ML MCP

Required tools:

``` text
predict_cost_overrun()
predict_time_overrun()
calculate_risk_score()
get_model_metadata()
get_feature_importance()
validate_prediction_input()
run_batch_prediction()
```

------------------------------------------------------------------------

# FR-038 Analytics MCP

Required tools:

``` text
calculate_cost_utilisation()
calculate_schedule_utilisation()
calculate_expected_progress()
calculate_progress_gap()
calculate_expenditure_progress_divergence()
calculate_monthly_trend()
detect_anomaly()
calculate_project_health_score()
```

------------------------------------------------------------------------

# FR-039 Document MCP

Required tools:

``` text
search_document()
retrieve_document_chunk()
get_document_page()
extract_tables()
search_project_in_reports()
extract_project_findings()
get_report_metadata()
```

------------------------------------------------------------------------

# FR-040 Web MCP

Required tools:

``` text
search_web()
search_project_news()
search_government_updates()
search_tender_information()
search_clearance_information()
search_court_information()
extract_web_evidence()
verify_source()
```

------------------------------------------------------------------------

# FR-041 Knowledge MCP

Required tools:

``` text
semantic_search()
retrieve_context()
retrieve_project_evidence()
search_risk_knowledge()
search_intervention_playbook()
```

------------------------------------------------------------------------

# FR-042 Tool Registry

Every tool shall have:

``` text
tool_id
tool_name
description
input_schema
output_schema
version
permission
timeout
retry_policy
owner
mcp_server
audit_requirement
```

------------------------------------------------------------------------

# FR-043 Tool Permissions

Agents shall have explicit tool permissions.

Example:

``` text
Prediction Agent
 ├── predict_cost_overrun
 ├── predict_time_overrun
 └── get_model_metadata

Web Agent
 ├── search_web
 ├── search_project_news
 └── verify_source
```

Agents shall not invoke tools outside their permission set.

------------------------------------------------------------------------

# FR-044 Tool Failure Handling

Tools shall support:

-   Timeout.
-   Retry.
-   Error response.
-   Circuit breaking where appropriate.
-   Graceful degradation.

The system shall never fabricate tool results.

------------------------------------------------------------------------

# FR-045 Conversational Interface

The system shall support natural-language questions.

Examples:

``` text
Analyse Project X.

Why is Project X high risk?

What changed since last month?

Which projects are at highest cost-overrun risk?

Show evidence supporting this risk.

What action should be taken?
```

------------------------------------------------------------------------

# FR-046 Reporting

The Reporting Agent shall generate standardized reports containing:

1.  Project overview.
2.  Current status.
3.  Overall risk.
4.  Cost prediction.
5.  Time prediction.
6.  Project health.
7.  Historical trend.
8.  Anomalies.
9.  Risk drivers.
10. Official evidence.
11. External intelligence.
12. Monthly changes.
13. Recommendations.
14. Monitoring level.
15. Confidence.
16. Evidence.
17. Model information.

------------------------------------------------------------------------

# 7. Data Requirements

# DR-001 Project Data

The system shall support project-level fields including:

``` text
project_id
project_name
ministry
department
agency
sector
state
original_cost
revised_cost
original_start_date
original_completion_date
revised_completion_date
current_status
```

------------------------------------------------------------------------

# DR-002 Monthly Observation Data

The system shall support:

``` text
project_id
snapshot_month
cumulative_expenditure
physical_progress
milestone_status
project_status
```

Additional fields shall be supported as available.

------------------------------------------------------------------------

# DR-003 Temporal Integrity

Every observation shall have a timestamp/snapshot month.

The system shall preserve historical states.

------------------------------------------------------------------------

# DR-004 Feature Store

The feature store shall support:

``` text
project_id
snapshot_month
original_cost
cumulative_expenditure
elapsed_months
remaining_months
physical_progress
expected_progress
progress_gap
cost_utilisation
schedule_utilisation
monthly_expenditure_growth
monthly_progress_growth
milestone_delay_count
```

------------------------------------------------------------------------

# DR-005 Point-in-Time Rule

For a prediction at snapshot month T:

``` text
All features must satisfy:

feature_timestamp <= T
```

Future observations shall be excluded.

------------------------------------------------------------------------

# DR-006 Data Validation

The system shall validate:

-   Required fields.
-   Data types.
-   Numeric ranges.
-   Date consistency.
-   Duplicate records.
-   Missing values.
-   Invalid project IDs.
-   Temporal ordering.

------------------------------------------------------------------------

# DR-007 Data Versioning

The system shall record:

-   Dataset version.
-   Data ingestion time.
-   Data snapshot.
-   Feature version.
-   Processing pipeline version.

------------------------------------------------------------------------

# 8. Database Requirements

## 8.1 Relational Database

PostgreSQL or equivalent shall be used for structured information.

### Core tables

``` text
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

------------------------------------------------------------------------

# 9. Vector Database Requirements

The vector store shall support:

-   Embeddings.
-   Similarity search.
-   Metadata filtering.
-   Project filtering.
-   Document filtering.
-   Page-level retrieval.
-   Versioning.

Suitable technologies include Qdrant or pgvector.

------------------------------------------------------------------------

# 10. Object Storage Requirements

Object storage shall store:

-   Raw PDFs.
-   Processed documents.
-   Model artifacts.
-   Generated reports.
-   Evaluation datasets where appropriate.

------------------------------------------------------------------------

# 11. RAG Requirements

## RAG-001 Ingestion

Documents shall be processed into searchable chunks.

## RAG-002 Chunk Metadata

Every chunk shall retain:

-   Document ID.
-   Page number.
-   Project ID where known.
-   Report date.
-   Source type.

## RAG-003 Retrieval

The system shall retrieve relevant chunks based on:

-   Semantic similarity.
-   Metadata.
-   Project ID.
-   Date.
-   Document type.

## RAG-004 Citation

Retrieved evidence should retain source/page information.

------------------------------------------------------------------------

# 12. API Requirements

## POST

``` text
/api/v1/projects/{project_id}/analyse
```

Starts project analysis.

## GET

``` text
/api/v1/projects/{project_id}
```

Returns project metadata.

## GET

``` text
/api/v1/projects/{project_id}/history
```

Returns project history.

## GET

``` text
/api/v1/projects/{project_id}/risk
```

Returns current risk.

## GET

``` text
/api/v1/projects/{project_id}/predictions
```

Returns predictions.

## GET

``` text
/api/v1/projects/{project_id}/evidence
```

Returns evidence.

## GET

``` text
/api/v1/projects/{project_id}/recommendations
```

Returns recommendations.

## GET

``` text
/api/v1/portfolio/risk
```

Returns portfolio risk.

## GET

``` text
/api/v1/traces/{trace_id}
```

Returns execution trace for authorized users.

------------------------------------------------------------------------

# 13. API Response Standard

All APIs should support:

``` json
{
  "status": "success",
  "data": {},
  "trace_id": "...",
  "timestamp": "...",
  "errors": []
}
```

------------------------------------------------------------------------

# 14. Non-Functional Requirements

# NFR-001 Performance

Target initial system:

  Operation                                                    Target
  ------------------ ------------------------------------------------
  Simple query                                               \< 5 sec
  Project analysis     \< 30 sec where no external search is required
  Complex analysis                                          \< 60 sec
  Portfolio batch                                        Asynchronous

Targets shall be validated through performance testing.

------------------------------------------------------------------------

# NFR-002 Availability

Target production availability:

> 99.5%

------------------------------------------------------------------------

# NFR-003 Scalability

The system shall support:

-   Thousands of projects.
-   Millions of monthly observations.
-   Large document collections.
-   Concurrent users.
-   Batch prediction.

Components shall be independently scalable where practical.

------------------------------------------------------------------------

# NFR-004 Reliability

The system shall support:

-   Retries.
-   Timeouts.
-   Failure isolation.
-   Graceful degradation.
-   Circuit breakers.
-   Idempotent operations where appropriate.

------------------------------------------------------------------------

# NFR-005 Security

The system shall implement:

-   Authentication.
-   RBAC.
-   Least privilege.
-   Secure secrets.
-   Encrypted transport.
-   Secure storage.
-   Audit logs.
-   Tool permissions.

------------------------------------------------------------------------

# NFR-006 Data Privacy

The system shall avoid exposing data to agents/tools unless required for
the task.

Sensitive or restricted data shall be governed by access policies.

------------------------------------------------------------------------

# NFR-007 Explainability

High-risk decisions shall provide:

-   Risk score.
-   Prediction probability.
-   Major drivers.
-   Supporting evidence.
-   Model version.
-   Data snapshot.

------------------------------------------------------------------------

# NFR-008 Reproducibility

A completed analysis shall be reproducible from:

``` text
trace_id
data snapshot
feature version
model version
prompt version
agent version
tool versions
retrieved evidence
```

------------------------------------------------------------------------

# NFR-009 Maintainability

The architecture shall support independent updates to:

-   Agents.
-   Tools.
-   MCP servers.
-   ML models.
-   Prompts.
-   RAG pipelines.
-   UI.

------------------------------------------------------------------------

# NFR-010 Extensibility

The system shall allow future addition of:

-   New ML models.
-   New project-risk dimensions.
-   New agents.
-   New MCP servers.
-   New data sources.
-   New dashboards.

------------------------------------------------------------------------

# 15. Observability Requirements

# OBS-001 Trace

Every user request shall receive:

``` text
trace_id
request_id
session_id
```

------------------------------------------------------------------------

# OBS-002 Agent Trace

The trace shall record:

``` text
Coordinator
  ├── Agent
  │    ├── MCP call
  │    │    └── Tool
  │    └── Result
  └── Agent
```

------------------------------------------------------------------------

# OBS-003 Metrics

System metrics:

-   Request count.
-   Success rate.
-   Error rate.
-   P50 latency.
-   P95 latency.
-   P99 latency.
-   Throughput.

Agent metrics:

-   Agent execution count.
-   Agent failure rate.
-   Agent latency.
-   Tool calls.
-   Retry count.
-   Context size.

MCP metrics:

-   Availability.
-   Tool latency.
-   Tool failure rate.
-   Timeout rate.

------------------------------------------------------------------------

# OBS-004 LLM Telemetry

Track where available:

``` text
model
model_version
prompt_version
input_tokens
output_tokens
reasoning_tokens
cached_tokens
latency
time_to_first_token
```

------------------------------------------------------------------------

# OBS-005 Logs

Logs shall include structured fields:

``` text
timestamp
trace_id
agent
tool
mcp_server
status
latency
error
```

Logs shall not expose secrets.

------------------------------------------------------------------------

# 16. Cost Tracking Requirements

# COST-001 Token Tracking

The system shall track token usage per:

-   Request.
-   Agent.
-   Model.
-   User.
-   Project.

------------------------------------------------------------------------

# COST-002 Tool Cost

The system shall track tool usage and cost where applicable.

------------------------------------------------------------------------

# COST-003 Request Cost

Example:

``` text
Coordinator      ₹0.08
History Agent    ₹0.11
Prediction       ₹0.03
Review Agent     ₹0.21
Web Agent        ₹0.35
Risk Agent       ₹0.09
Reporting        ₹0.08
----------------------
Total            ₹0.95
```

Actual cost shall be calculated from configured provider/model pricing.

------------------------------------------------------------------------

# COST-004 Budget Controls

The system shall support:

``` text
max_cost_per_request
max_llm_calls
max_web_searches
max_agent_depth
max_execution_time
```

------------------------------------------------------------------------

# COST-005 Cost Dashboard

Administrators shall be able to view:

-   Cost per request.
-   Cost per agent.
-   Cost per model.
-   Cost per project.
-   Daily cost.
-   Monthly cost.
-   Ministry-level cost.
-   Sector-level cost.

------------------------------------------------------------------------

# 17. Agent Evaluation Requirements

# EVAL-001 Evaluation Dataset

The system shall maintain benchmark cases containing:

-   Project.
-   Query.
-   Expected result.
-   Expected evidence.
-   Expected risk.
-   Expected drivers.
-   Expected recommendation where applicable.

------------------------------------------------------------------------

# EVAL-002 Agent Evaluation

Evaluate:

### Coordinator

-   Task decomposition.
-   Agent selection.
-   Tool selection.
-   Plan completion.

### History

-   Project identification.
-   Chronology.
-   Data accuracy.

### RAG

-   Retrieval precision.
-   Retrieval recall.
-   Context relevance.
-   Groundedness.
-   Citation correctness.

### Prediction

-   Accuracy.
-   Calibration.
-   Input correctness.
-   Leakage.

### Web

-   Relevance.
-   Source credibility.
-   Evidence extraction.
-   Citation correctness.

### Risk

-   Risk classification.
-   Driver accuracy.
-   False positives.
-   False negatives.

### Intervention

-   Relevance.
-   Feasibility.
-   Risk-action alignment.

------------------------------------------------------------------------

# EVAL-003 End-to-End Evaluation

The system shall support complete workflows such as:

``` text
User Query
 ↓
Coordinator
 ↓
History
 ↓
Health
 ↓
Prediction
 ↓
Review
 ↓
Web
 ↓
Diagnosis
 ↓
Evidence
 ↓
Intervention
 ↓
Final Report
```

The final result shall be evaluated against benchmark expectations.

------------------------------------------------------------------------

# EVAL-004 Regression Testing

Every material change to:

-   Agent prompts.
-   Agent code.
-   Models.
-   Retrieval configuration.
-   MCP tools.

shall be evaluated against the benchmark before production deployment.

------------------------------------------------------------------------

# EVAL-005 Hallucination Testing

Evaluation shall identify:

-   Invented numbers.
-   Invented facts.
-   Invented sources.
-   Incorrect dates.
-   Incorrect project attributes.
-   Unsupported recommendations.

------------------------------------------------------------------------

# 18. Guardrail Requirements

## GR-001 Input Guardrail

Validate:

-   Project ID.
-   Query.
-   Parameters.
-   Permissions.
-   Tool eligibility.

## GR-002 Tool Guardrail

Validate:

-   Agent permission.
-   Input schema.
-   Tool availability.
-   Timeout.
-   Rate limits.

## GR-003 Output Guardrail

Check:

-   Unsupported claims.
-   Missing evidence.
-   Numerical inconsistencies.
-   Contradictions.
-   Source attribution.

------------------------------------------------------------------------

# 19. Audit Requirements

Every significant analysis shall record:

``` text
user
timestamp
project_id
trace_id

agent_versions
model_versions
prompt_versions

tools_called
mcp_servers

data_snapshot
retrieved_documents
web_sources

predictions
health_metrics
risk_result
recommendations
final_output
```

Audit records shall be immutable or protected against unauthorized
modification.

------------------------------------------------------------------------

# 20. Alert Requirements

## AL-001 Risk Alert

Trigger when:

``` text
risk_score >= configured_threshold
```

## AL-002 Risk Escalation

Trigger when:

``` text
current_risk - previous_risk >= configured_threshold
```

## AL-003 Prediction Alert

Trigger when:

``` text
cost_overrun_probability >= configured_threshold
```

## AL-004 Anomaly Alert

Trigger when:

``` text
anomaly_score >= configured_threshold
```

------------------------------------------------------------------------

# 21. Monthly Processing Requirements

The system shall support a monthly pipeline:

``` text
Monthly Data
     ↓
Validation
     ↓
Feature Generation
     ↓
ML Prediction
     ↓
Health Calculation
     ↓
Anomaly Detection
     ↓
Risk Fusion
     ↓
Risk Change Detection
     ↓
Alert
```

For high-risk projects:

``` text
Risk Detection
     ↓
Deep Investigation
     ↓
Review Intelligence
     ↓
Web Intelligence
     ↓
Diagnosis
     ↓
Intervention
```

------------------------------------------------------------------------

# 22. Batch Processing Requirements

The system shall support batch prediction for multiple projects.

Example:

``` text
1,000 projects
     ↓
Feature generation
     ↓
Batch ML prediction
     ↓
Health calculation
     ↓
Risk ranking
     ↓
Top 100
     ↓
Deep agentic investigation
```

Deep agentic investigation should be selectively executed to control
cost.

------------------------------------------------------------------------

# 23. Error Handling

The system shall use standardized errors.

``` json
{
  "status": "FAILED",
  "error_code": "ML_MODEL_UNAVAILABLE",
  "message": "Cost prediction model is unavailable",
  "trace_id": "..."
}
```

------------------------------------------------------------------------

# 24. Graceful Degradation

## Web unavailable

Use:

``` text
PAIMANA
+
Review Reports
+
ML
+
Analytics
```

## Review retrieval unavailable

Use:

``` text
PAIMANA
+
ML
+
Analytics
```

## ML unavailable

Show:

``` text
Project health
Historical trend
Anomaly results
```

and explicitly indicate:

> ML prediction unavailable.

The system shall never fabricate unavailable results.

------------------------------------------------------------------------

# 25. Security Architecture

``` text
User
 ↓
Authentication
 ↓
RBAC
 ↓
API Gateway
 ↓
Coordinator
 ↓
Agent Permission
 ↓
MCP Permission
 ↓
Tool
 ↓
Data
```

Security shall follow least-privilege principles.

------------------------------------------------------------------------

# 26. Deployment Architecture

## Development

``` text
Docker Compose
 ├── API
 ├── Frontend
 ├── PostgreSQL
 ├── Redis
 ├── Vector DB
 ├── MCP Servers
 └── ML Service
```

## Production

``` text
Load Balancer
      |
API Gateway
      |
Kubernetes
 ├── API Services
 ├── Agent Runtime
 ├── MCP Services
 ├── ML Services
 ├── RAG Services
 ├── Worker Services
 └── Monitoring
      |
Data Services
 ├── PostgreSQL
 ├── Redis
 ├── Vector DB
 └── Object Storage
```

------------------------------------------------------------------------

# 27. Recommended Technology Stack

  Component             Technology
  --------------------- -----------------------------------------
  Frontend              React / Next.js
  Backend               Python / FastAPI
  Agent orchestration   LangGraph or custom state orchestration
  MCP                   MCP-compatible Python/TypeScript
  ML                    scikit-learn / XGBoost / LightGBM
  Model registry        MLflow
  Database              PostgreSQL
  Vector DB             Qdrant / pgvector
  Cache                 Redis
  PDF processing        PyMuPDF + OCR
  Embeddings            NVIDIA Nemotron Embed 1B or equivalent
  Object storage        MinIO
  Tracing               OpenTelemetry
  Metrics               Prometheus
  Dashboards            Grafana
  Logging               Loki / Elasticsearch
  Tests                 pytest
  Containers            Docker
  Orchestration         Kubernetes when required

------------------------------------------------------------------------

# 28. Logical Component Structure

``` text
project-monitoring-ai/
│
├── api/
├── frontend/
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
│   └── knowledge/
│
├── tools/
├── models/
├── rag/
├── data/
├── evaluation/
├── observability/
├── cost_tracking/
├── security/
├── prompts/
├── configs/
└── tests/
```

------------------------------------------------------------------------

# 29. Detailed Execution Sequence

## 29.1 Project Analysis

``` text
1. User submits project query.
2. API authenticates user.
3. API creates trace ID.
4. Coordinator receives request.
5. Coordinator identifies project.
6. Project metadata is retrieved.
7. History Agent retrieves history.
8. Health Agent calculates metrics.
9. Prediction Agent prepares features.
10. ML MCP executes prediction.
11. Anomaly Agent checks current behavior.
12. Review Agent retrieves official evidence.
13. Web Agent retrieves external evidence.
14. Evidence Agent validates claims.
15. Diagnosis Agent determines risk.
16. Intervention Agent generates actions.
17. Reporting Agent produces report.
18. Output guardrail validates response.
19. Coordinator returns response.
20. Trace and cost records are stored.
```

------------------------------------------------------------------------

# 30. Risk Analysis Sequence

``` text
Project
  |
  +--> Cost Prediction
  |
  +--> Time Prediction
  |
  +--> Financial Health
  |
  +--> Schedule Health
  |
  +--> Progress Health
  |
  +--> Anomaly Detection
  |
  +--> History
  |
  +--> Review Evidence
  |
  +--> Web Evidence
          |
          v
     Evidence Verification
          |
          v
       Risk Fusion
          |
          v
      Risk Diagnosis
          |
          v
      Intervention
```

------------------------------------------------------------------------

# 31. Data Flow Requirements

## Data Ingestion

``` text
Source
 ↓
Ingestion
 ↓
Validation
 ↓
Normalization
 ↓
Temporal Alignment
 ↓
Storage
 ↓
Feature Generation
```

## Prediction

``` text
Feature Store
 ↓
Snapshot Validation
 ↓
ML MCP
 ↓
Model
 ↓
Prediction
 ↓
Prediction Store
```

## Document

``` text
PDF
 ↓
Extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Vector DB
 ↓
RAG
 ↓
Evidence
```

------------------------------------------------------------------------

# 32. Model Evaluation Requirements

For cost-overrun prediction, the system shall support:

-   ROC-AUC.
-   PR-AUC.
-   Precision.
-   Recall.
-   F1.
-   Brier score.
-   Calibration.
-   False-positive rate.
-   False-negative rate.

Time-based validation should be used for temporal project data.

------------------------------------------------------------------------

# 33. ML Data Leakage Requirements

The implementation shall explicitly prevent leakage from:

-   Future revised cost.
-   Future completion date revisions.
-   Future expenditure.
-   Future physical progress.
-   Future milestone results.
-   Future risk labels.
-   Any field created after the snapshot date.

The training/evaluation pipeline shall document feature availability
time.

------------------------------------------------------------------------

# 34. Explainability Requirements

For ML predictions, where supported, the system should provide:

-   Important features.
-   Direction of influence where available.
-   Model version.
-   Probability.
-   Calibration information.
-   Prediction horizon.

The system shall distinguish:

``` text
Model explanation
```

from

``` text
Administrative root cause
```

A model feature importance is not automatically proof of a real-world
cause.

------------------------------------------------------------------------

# 35. Agent Communication Contract

Agents should exchange structured results.

Example:

``` json
{
  "agent": "project_health",
  "status": "SUCCESS",
  "confidence": 0.96,
  "result": {
    "cost_utilisation": 0.58,
    "schedule_utilisation": 0.71,
    "progress_gap": -0.29
  },
  "evidence": [
    {
      "source": "project_monthly_data",
      "snapshot_month": "2023-12"
    }
  ]
}
```

------------------------------------------------------------------------

# 36. Agent Lifecycle

``` text
Receive Task
    ↓
Validate Input
    ↓
Plan
    ↓
Call Tools
    ↓
Validate Tool Results
    ↓
Reason
    ↓
Produce Structured Output
    ↓
Confidence
    ↓
Return Result
```

------------------------------------------------------------------------

# 37. Agent Limits

To prevent uncontrolled execution, the system shall support:

``` text
max_agent_depth
max_agent_turns
max_tool_calls
max_web_searches
max_execution_time
max_context_size
max_cost
```

------------------------------------------------------------------------

# 38. Prompt Injection Protection

External documents and web pages shall be treated as untrusted content.

The system shall:

-   Separate instructions from retrieved content.
-   Prevent retrieved text from overriding system policies.
-   Validate tool calls.
-   Restrict tool permissions.
-   Apply output validation.

------------------------------------------------------------------------

# 39. Web Source Trust

The Web Intelligence Agent shall classify source quality where possible:

``` text
OFFICIAL
REPUTABLE
SECONDARY
UNKNOWN
```

External information shall be presented with appropriate confidence.

------------------------------------------------------------------------

# 40. UI Requirements

## Project Page

Must contain:

``` text
Project Overview
Risk Summary
Prediction
Health
Trend
Timeline
Anomalies
Evidence
Recommendations
What Changed
Audit Information
```

## Portfolio Page

Must contain:

``` text
Total Projects
High Risk
Critical
Risk Trend
Ministry Distribution
Sector Distribution
Top Risk Projects
Recent Escalations
```

------------------------------------------------------------------------

# 41. Risk Visualization

The UI should provide:

-   Risk score.
-   Risk level.
-   Cost probability.
-   Time probability.
-   Progress trend.
-   Expenditure trend.
-   Risk trend.
-   Timeline.
-   Risk drivers.

Visualizations must be backed by actual stored values.

------------------------------------------------------------------------

# 42. Report Export

The system should support export of:

-   Project report.
-   Portfolio report.
-   Risk report.
-   Evidence report.

Supported formats may include:

-   PDF.
-   Markdown.
-   JSON.
-   CSV for tabular analytics.

------------------------------------------------------------------------

# 43. Configuration Requirements

Configuration shall be externalized.

Example:

``` yaml
risk:
  thresholds:
    low: 29
    moderate: 49
    elevated: 69
    high: 84

execution:
  max_agent_depth: 5
  max_tool_calls: 20
  max_execution_seconds: 60

rag:
  top_k: 10

alerts:
  high_risk_threshold: 70
```

Exact values must be configurable.

------------------------------------------------------------------------

# 44. Monitoring and Health Checks

Every service shall expose health status.

Examples:

``` text
/api/health
/api/ready
```

MCP servers shall expose health information where supported.

Health checks shall cover:

-   Database.
-   Redis.
-   Vector DB.
-   ML service.
-   MCP servers.
-   Object storage.

------------------------------------------------------------------------

# 45. Backup and Recovery

The system shall define backup procedures for:

-   PostgreSQL.
-   Vector database.
-   Object storage.
-   Model registry.
-   Configuration.
-   Audit records.

Recovery procedures shall be tested before production deployment.

------------------------------------------------------------------------

# 46. Disaster Recovery

The system shall define:

-   Recovery Point Objective.
-   Recovery Time Objective.
-   Backup frequency.
-   Restore procedure.
-   Service dependency map.

Exact RPO/RTO values shall be established during production
infrastructure planning.

------------------------------------------------------------------------

# 47. Acceptance Criteria

## AC-001

A valid project ID returns the correct project.

## AC-002

Project history is returned chronologically.

## AC-003

Project health metrics are calculated correctly.

## AC-004

Cost prediction uses only point-in-time features.

## AC-005

ML model version is stored with every prediction.

## AC-006

Risk explanations contain evidence.

## AC-007

External web claims are labelled as external evidence.

## AC-008

High-risk projects generate risk-aligned recommendations.

## AC-009

Every request has a trace ID.

## AC-010

Every agent/tool execution is observable.

## AC-011

LLM usage is attributable to a request and agent.

## AC-012

Evaluation benchmark can be executed automatically.

## AC-013

Unauthorized agents cannot access restricted tools.

## AC-014

System does not fabricate unavailable model/tool results.

## AC-015

Monthly updates can trigger risk recalculation.

------------------------------------------------------------------------

# 48. Test Strategy

## Unit Tests

Test:

-   Calculations.
-   Data validation.
-   API schemas.
-   Feature generation.
-   Tool functions.

## Integration Tests

Test:

-   Agent → MCP.
-   MCP → tool.
-   Tool → database.
-   Agent → RAG.
-   Agent → ML model.

## End-to-End Tests

Test:

``` text
User
 ↓
API
 ↓
Coordinator
 ↓
Agents
 ↓
MCP
 ↓
Tools
 ↓
Risk
 ↓
Report
```

## Security Tests

Test:

-   Unauthorized access.
-   Tool permission bypass.
-   Prompt injection.
-   Invalid input.
-   API abuse.

## Performance Tests

Test:

-   Concurrent users.
-   Batch prediction.
-   RAG retrieval.
-   Agent execution.
-   MCP latency.

------------------------------------------------------------------------

# 49. Production Readiness Checklist

## Data

-   [ ] Data validation implemented.
-   [ ] Temporal alignment implemented.
-   [ ] Point-in-time feature generation implemented.
-   [ ] Data versioning implemented.

## ML

-   [ ] Model registered.
-   [ ] Model evaluated.
-   [ ] Leakage checks completed.
-   [ ] Calibration evaluated.
-   [ ] Prediction API/MCP implemented.

## Agents

-   [ ] Coordinator implemented.
-   [ ] History Agent implemented.
-   [ ] Health Agent implemented.
-   [ ] Prediction Agent implemented.
-   [ ] Review Agent implemented.
-   [ ] Web Agent implemented.
-   [ ] Evidence Agent implemented.
-   [ ] Diagnosis Agent implemented.
-   [ ] Intervention Agent implemented.
-   [ ] Reporting Agent implemented.

## MCP

-   [ ] PAIMANA MCP.
-   [ ] ML MCP.
-   [ ] Analytics MCP.
-   [ ] Document MCP.
-   [ ] Web MCP.
-   [ ] Knowledge MCP.

## Platform

-   [ ] Authentication.
-   [ ] RBAC.
-   [ ] Guardrails.
-   [ ] Audit.
-   [ ] Observability.
-   [ ] Cost tracking.
-   [ ] Evaluation suite.
-   [ ] Error handling.
-   [ ] Backup.

------------------------------------------------------------------------

# 50. Implementation Phases

## Phase 1 -- Core Data and ML

``` text
Project Data
 ↓
Cleaning
 ↓
Feature Engineering
 ↓
Cost ML Model
 ↓
Project Health
```

## Phase 2 -- Core Agentic System

``` text
Coordinator
 ↓
History Agent
 ↓
Prediction Agent
 ↓
Health Agent
 ↓
Risk Diagnosis
```

## Phase 3 -- Evidence Intelligence

``` text
RAG
 ↓
Review Report Agent
 ↓
Evidence Verification
 ↓
What Changed
```

## Phase 4 -- External Intelligence

``` text
Web MCP
 ↓
Web Intelligence Agent
 ↓
External Risk
```

## Phase 5 -- Prescriptive Intelligence

``` text
Risk Diagnosis
 ↓
Intervention Agent
 ↓
Monitoring Recommendation
```

## Phase 6 -- Production Control Plane

``` text
Evaluation
Observability
Cost Tracking
Security
Audit
Model Registry
```

------------------------------------------------------------------------

# 51. Future Enhancements

Potential future capabilities:

-   Time-overrun forecasting.
-   Completion-date forecasting.
-   Cost escalation magnitude forecasting.
-   Comparable-project benchmarking.
-   Ministry-level risk forecasting.
-   Sector-specific models.
-   Automated monthly risk summaries.
-   Scenario simulation.
-   What-if analysis.
-   Advanced causal analysis.
-   Human feedback learning.
-   Automated model retraining pipelines.

------------------------------------------------------------------------

# 52. Final System Requirement

The completed system shall provide an integrated decision-support
workflow:

``` text
                    PROJECT
                       |
                       v
                 DATA LAYER
                       |
                       v
               ANALYTICS ENGINE
                       |
                       v
                ML PREDICTION
                       |
                       v
                AGENTIC ANALYSIS
                       |
       +---------------+---------------+
       |               |               |
       v               v               v
    HISTORY          REVIEW           WEB
       |               |               |
       +---------------+---------------+
                       |
                       v
               EVIDENCE VERIFY
                       |
                       v
                  RISK FUSION
                       |
                       v
                 DIAGNOSIS
                       |
                       v
                 INTERVENTION
                       |
                       v
                 FINAL REPORT
                       |
                       v
               DECISION MAKER
                       |
                       v
                MONITORING LOOP
```

------------------------------------------------------------------------

# 53. Architectural Quality Requirements

The system shall maintain the following separation of concerns:

``` text
LLM / Agents
    =
Planning + Reasoning + Synthesis

ML
    =
Prediction

Analytics
    =
Deterministic Calculations

Database
    =
Structured Source of Record

RAG
    =
Document Retrieval

Web Intelligence
    =
External Evidence Discovery

MCP
    =
Controlled Capability Access

Evaluation
    =
Quality Measurement

Observability
    =
Operational Visibility

Cost Tracking
    =
Resource Attribution

Audit
    =
Accountability
```

No single component should become the source of all system truth.

------------------------------------------------------------------------

# 54. Final Architecture

``` text
╔════════════════════════════════════════════════════════════════════╗
║                    USER / DECISION MAKER                          ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                         APPLICATION LAYER                         ║
║              Web UI | API | Auth | RBAC | Alerts                  ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                      COORDINATOR AGENT                            ║
║  Intent | Planning | Routing | State | Parallelism | Synthesis   ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
       +-----------------------+-----------------------+
       |                       |                       |
       v                       v                       v
 DATA INTELLIGENCE       PREDICTION/HEALTH       INTELLIGENCE
       |                       |                       |
       |                 +-----+-----+           +-----+-----+
       |                 |           |           |           |
       v                 v           v           v           v
   History             Cost       Time       Review       Web
   Timeline            ML         ML         RAG          Intel
   Data Quality        Anomaly    Health     Evidence
       |                 |           |           |           |
       +-----------------+-----------+-----------+-----------+
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                    EVIDENCE VERIFICATION                         ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                         RISK FUSION                              ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                       RISK DIAGNOSIS                              ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                       INTERVENTION                               ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
╔════════════════════════════════════════════════════════════════════╗
║                        REPORTING                                 ║
╚══════════════════════════════╤═════════════════════════════════════╝
                               |
                               v
                         DECISION MAKER


════════════════════════════════════════════════════════════════════
                         MCP LAYER
════════════════════════════════════════════════════════════════════

 PAIMANA MCP | ML MCP | Analytics MCP | Document MCP
 Web MCP     | Knowledge MCP

                               |
                               v

════════════════════════════════════════════════════════════════════
                           TOOLS
════════════════════════════════════════════════════════════════════

 SQL | ML Model | Python | Statistics | PDF | OCR | Vector Search
 Web Search | Source Verification | Timeline | Rules Engine


════════════════════════════════════════════════════════════════════
                      DATA / KNOWLEDGE
════════════════════════════════════════════════════════════════════

 PAIMANA | Flash Reports | Review Reports | Project History
 PostgreSQL | Vector DB | Object Storage | Feature Store


════════════════════════════════════════════════════════════════════
                     CROSS-CUTTING CONTROL PLANE
════════════════════════════════════════════════════════════════════

 Evaluation | Observability | Cost Tracking | Security
 Guardrails | Audit | Model Registry | Prompt Registry
```

------------------------------------------------------------------------

# 55. Final Requirement Summary

The software shall transform project monitoring from a primarily
descriptive workflow into an integrated predictive and decision-support
workflow.

The core execution chain shall be:

> **Project Data → Analytics → ML Prediction → Agentic Investigation →
> Evidence Verification → Risk Fusion → Diagnosis → Intervention →
> Decision → Continuous Monitoring**

The architectural contract shall be:

> **Coordinator Agent → Specialist Agents → MCP Servers → Deterministic
> Tools/Data**

The production control plane shall be:

> **Evaluation + Observability + Cost Tracking + Security + Audit +
> Governance**

The system shall preserve a clear distinction between:

> **Facts → Calculations → Predictions → External Evidence →
> Recommendations**

This separation is a mandatory architectural principle for reliability,
explainability, auditability and government-facing decision support.
