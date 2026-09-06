# Product Requirements Document (PRD)

# AI-Powered Predictive Project Monitoring & Decision Intelligence Platform

**Project:** SIH 2.0 -- MoSPI / IPMD\
**Document Type:** Product Requirements Document\
**Version:** 1.0\
**Status:** Proposed\
**Primary Users:** MoSPI/IPMD project-monitoring officers,
ministry/department officials, analysts, administrators\
**Primary Objective:** Predict project cost/time overrun risk early,
diagnose the underlying drivers, verify findings using evidence,
recommend interventions, and continuously monitor project health.

------------------------------------------------------------------------

## 1. Executive Summary

The proposed platform is an AI-powered, multi-agent project-monitoring
and decision-intelligence system for infrastructure projects monitored
by MoSPI/IPMD.

The platform combines:

-   Historical project data
-   Monthly project updates
-   Flash Reports
-   Review Reports
-   Machine-learning prediction models
-   Deterministic project-health analytics
-   Anomaly detection
-   Project-history reconstruction
-   Retrieval-Augmented Generation (RAG)
-   External web intelligence
-   Evidence verification
-   Risk fusion
-   Prescriptive intervention recommendations
-   Explainable decision support
-   Agent evaluation
-   Full observability
-   LLM/tool cost tracking
-   Auditability and governance

The system follows the lifecycle:

> **Predict → Diagnose → Verify → Prescribe → Monitor**

The platform should not treat the LLM as the source of numerical truth.
Numerical calculations, database operations, ML predictions and
deterministic risk rules must be executed through controlled tools.
Agents are responsible for planning, retrieval, interpretation, evidence
synthesis and decision support.

------------------------------------------------------------------------

# 2. Problem Statement

Large infrastructure projects can experience:

-   Cost escalation
-   Schedule delays
-   Slow physical progress
-   Expenditure-progress imbalance
-   Milestone slippage
-   Implementation bottlenecks
-   Approval and clearance issues
-   Land acquisition issues
-   Contractual problems
-   Resource constraints
-   External events

Traditional monitoring can identify problems after they become visible
in reported project outcomes.

The proposed system addresses the early-warning problem:

> Given the information available for a project up to the current
> reporting month, determine whether the project is likely to experience
> future cost or time overrun, explain why the project is becoming
> risky, identify supporting evidence, and recommend an appropriate
> monitoring/intervention action.

------------------------------------------------------------------------

# 3. Product Vision

## Vision

Build a trusted AI decision-support platform that enables
project-monitoring authorities to move from:

**Reactive Monitoring**

to

**Predictive → Diagnostic → Prescriptive Monitoring.**

## Product Goal

For every monitored project, the system should answer five questions:

1.  **What is happening?**
2.  **What is likely to happen?**
3.  **Why is it likely to happen?**
4.  **What evidence supports the assessment?**
5.  **What should the monitoring authority do next?**

------------------------------------------------------------------------

# 4. Product Principles

## 4.1 Evidence First

Every important conclusion must be traceable to:

-   PAIMANA/project data
-   Flash Reports
-   Review Reports
-   External sources
-   Deterministic calculations
-   ML predictions

## 4.2 Point-in-Time Prediction

The prediction engine must use only information available up to the
prediction/snapshot month.

Future revised cost, future delay, or future outcome information must
not leak into model features.

## 4.3 Tools for Truth, Agents for Reasoning

Agents should not invent:

-   Financial calculations
-   Dates
-   Percentages
-   ML predictions
-   Database records

Such operations must use tools.

## 4.4 Human Decision Authority

The system provides decision support. Final administrative decisions
remain with authorized officials.

## 4.5 Explainability

A high-risk classification must be accompanied by understandable risk
drivers and supporting evidence.

## 4.6 Source Separation

The system must distinguish:

-   Observed project data
-   Official report evidence
-   External web evidence
-   ML inference
-   Derived analytical metrics
-   Agent-generated recommendations

------------------------------------------------------------------------

# 5. Target Users

## 5.1 Primary User -- Project Monitoring Officer

Needs:

-   Project risk status
-   Cost-overrun probability
-   Time-overrun probability
-   Current health
-   Major risk drivers
-   Latest changes
-   Evidence
-   Recommended actions

## 5.2 Senior Decision Maker

Needs:

-   Portfolio-level risk
-   High-risk project list
-   Ministry/sector comparison
-   Critical alerts
-   Trend analysis
-   Intervention priorities
-   Executive summaries

## 5.3 Analyst

Needs:

-   Project history
-   Monthly data
-   Model predictions
-   Feature trends
-   Report search
-   Evidence retrieval
-   Comparative analytics

## 5.4 System Administrator

Needs:

-   Agent health
-   MCP health
-   Model versions
-   Usage
-   Cost
-   Errors
-   Evaluation metrics
-   Audit logs
-   User/RBAC management

------------------------------------------------------------------------

# 6. Product Scope

## In Scope

### Data

-   Project metadata
-   Original approved cost
-   Revised cost where available
-   Cumulative expenditure
-   Original start date
-   Original completion date
-   Revised completion date where available
-   Physical progress
-   Milestone information
-   Monthly project history
-   Flash Reports
-   Review Reports

### AI/ML

-   Cost-overrun prediction
-   Time-overrun prediction
-   Risk scoring
-   Anomaly detection
-   Trend analysis
-   Risk-driver identification

### Agentic AI

-   Coordinator Agent
-   Project Identification Agent
-   Project History Agent
-   Project Timeline Agent
-   Project Health Agent
-   Prediction Agent
-   Review Report Agent
-   Web Intelligence Agent
-   Evidence Verification Agent
-   Risk Diagnosis Agent
-   Intervention Agent
-   Reporting Agent

### Platform

-   MCP servers
-   Tool registry
-   RAG
-   Vector database
-   Observability
-   Evaluation suite
-   Cost tracking
-   Audit trail
-   RBAC
-   Dashboard
-   Alerts

## Out of Scope for Initial MVP

-   Automatic modification of official project records
-   Automatic administrative decisions
-   Automatic sanctions/approvals
-   Unverified claims from the web
-   Fully autonomous external communication
-   Automatic changes to government databases without authorization

------------------------------------------------------------------------

# 7. High-Level Architecture

``` text
                         USER / DECISION MAKER
                                  |
                                  v
                         Web Dashboard / API
                                  |
                                  v
                    +----------------------------+
                    |     COORDINATOR AGENT      |
                    |                            |
                    | Intent Understanding       |
                    | Planning                   |
                    | Agent Routing              |
                    | Context Management         |
                    | Result Validation          |
                    | Final Synthesis            |
                    +-------------+--------------+
                                  |
             +--------------------+--------------------+
             |                    |                    |
             v                    v                    v
      Data Intelligence     Prediction / Health   Intelligence
          Agents                Agents             Agents
             |                    |                    |
             +--------------------+--------------------+
                                  |
                                  v
                         Risk Diagnosis Agent
                                  |
                                  v
                       Evidence Verification Agent
                                  |
                                  v
                       Intervention Agent
                                  |
                                  v
                         Reporting Agent
                                  |
                                  v
                         Decision Dashboard


===========================================================
                    MCP / TOOL LAYER
===========================================================

       PAIMANA MCP       ML MCP       Analytics MCP
             |              |               |
       Document MCP     Web MCP       Knowledge MCP
             |              |               |
             +--------------+---------------+
                            |
                            v
                          TOOLS

===========================================================
                 CROSS-CUTTING CONTROL PLANE
===========================================================

 Evaluation | Observability | Cost Tracking | Security
 Audit      | Guardrails    | Model Registry | Governance
```

------------------------------------------------------------------------

# 8. Agent Architecture

## 8.1 Coordinator Agent

The Coordinator Agent is the primary orchestration component.

### Responsibilities

-   Understand user intent
-   Identify required project
-   Decompose complex requests
-   Select appropriate agents
-   Execute independent tasks in parallel
-   Manage task dependencies
-   Maintain working context
-   Validate agent outputs
-   Resolve conflicting evidence
-   Request additional evidence where required
-   Produce final structured result
-   Generate trace/audit metadata

### Example

User:

> Analyse project 617279 and determine whether it is at risk of cost or
> time overrun.

Coordinator plan:

``` text
1. Identify project
2. Retrieve latest project state
3. Retrieve monthly history
4. Calculate project health
5. Run cost-overrun prediction
6. Run time-overrun prediction
7. Detect anomalies
8. Search latest review reports
9. Search relevant external evidence
10. Diagnose risk drivers
11. Verify evidence
12. Recommend interventions
13. Produce final decision report
```

------------------------------------------------------------------------

# 9. Data Intelligence Agent Group

## 9.1 Project Identification Agent

### Purpose

Identify the canonical project record.

### Inputs

-   Project ID
-   Project name
-   Ministry
-   Agency
-   State
-   User query

### Outputs

``` json
{
  "project_id": "617279",
  "project_name": "...",
  "ministry": "...",
  "agency": "...",
  "state": "...",
  "confidence": 0.99
}
```

------------------------------------------------------------------------

## 9.2 Project History Agent

### Purpose

Reconstruct the longitudinal history of a project.

### Responsibilities

-   Retrieve monthly records
-   Organize chronological history
-   Detect major changes
-   Summarize expenditure progression
-   Summarize physical-progress progression
-   Identify milestone changes
-   Identify cost/date revisions
-   Identify status changes

### Output

``` json
{
  "project_id": "617279",
  "period": {
    "start": "2021-01",
    "end": "2023-12"
  },
  "history": [],
  "major_events": [],
  "trend_summary": ""
}
```

------------------------------------------------------------------------

## 9.3 Project Timeline Agent

Creates an event timeline:

``` text
Approval
   ↓
Execution
   ↓
Milestone
   ↓
Progress slowdown
   ↓
Expenditure acceleration
   ↓
Review observation
   ↓
Risk escalation
```

------------------------------------------------------------------------

# 10. Project Health Agent

The Project Health Agent combines deterministic analytics.

## Core Metrics

### Cost Utilisation

``` text
Cost Utilisation =
Cumulative Expenditure / Original Approved Cost
```

### Schedule Utilisation

``` text
Schedule Utilisation =
Elapsed Project Duration / Original Project Duration
```

### Progress Gap

``` text
Progress Gap =
Expected Physical Progress - Actual Physical Progress
```

### Expenditure-Progress Divergence

``` text
Divergence =
Expenditure Utilisation - Physical Progress
```

### Monthly Trend

Calculate:

-   Progress change
-   Expenditure change
-   Trend slope
-   Acceleration/deceleration
-   Consecutive stagnant months

### Output

``` json
{
  "cost_utilisation": 0.58,
  "schedule_utilisation": 0.71,
  "physical_progress": 0.42,
  "progress_gap": -0.29,
  "expenditure_progress_divergence": 0.16,
  "health_status": "HIGH_RISK"
}
```

------------------------------------------------------------------------

# 11. Prediction Agent

The Prediction Agent provides access to ML models.

## Initial Model

Cost-overrun model.

## Future Models

-   Time-overrun model
-   Implementation-risk model
-   Completion forecast
-   Cost escalation magnitude forecast

### Required properties

-   Versioned model
-   Point-in-time features
-   Input validation
-   Probability output
-   Prediction horizon
-   Model metadata
-   Feature version
-   Confidence/calibration information

### Example

``` json
{
  "project_id": "617279",
  "snapshot_month": "2023-12",
  "cost_overrun_probability": 0.82,
  "prediction_horizon_months": 12,
  "model_version": "cost-overrun-v3"
}
```

------------------------------------------------------------------------

# 12. Cost Overrun Prediction

## Objective

Estimate the probability that a project that has not yet experienced the
target future outcome will experience cost overrun within the defined
prediction horizon.

## Requirements

The model must:

-   Use only snapshot-date information
-   Prevent future-data leakage
-   Support probability output
-   Store model version
-   Store feature version
-   Store prediction timestamp
-   Store prediction horizon

## Evaluation

-   ROC-AUC
-   PR-AUC
-   Precision
-   Recall
-   F1
-   Brier score
-   Calibration
-   False-positive rate
-   False-negative rate

------------------------------------------------------------------------

# 13. Time Overrun Prediction

Future capability.

### Inputs

-   Original duration
-   Elapsed duration
-   Remaining duration
-   Physical progress
-   Progress trend
-   Milestone delays
-   Expenditure trend
-   Historical patterns

### Outputs

``` json
{
  "time_overrun_probability": 0.76,
  "expected_delay_months": 11
}
```

------------------------------------------------------------------------

# 14. Anomaly Detection Agent

The anomaly engine answers:

> Is the current behaviour unusual compared with the project's own
> historical pattern or comparable patterns?

### Detect

-   Sudden expenditure acceleration
-   Progress stagnation
-   Sudden progress decline
-   Unusual expenditure-progress divergence
-   Abrupt schedule deterioration
-   Unexpected milestone changes

### Example

``` text
Previous expenditure:
100 → 105 → 110

Current:
190

Physical progress:
42 → 43 → 43.5 → 44

Result:
HIGH expenditure-progress anomaly
```

------------------------------------------------------------------------

# 15. Review Report Intelligence Agent

## Purpose

Extract project-specific evidence from official reports.

### Pipeline

``` text
PDF
 ↓
Parser / OCR
 ↓
Page and table extraction
 ↓
Chunking
 ↓
Embedding
 ↓
Vector Database
 ↓
Retriever
 ↓
Review Report Agent
```

### Required evidence fields

``` json
{
  "project_id": "617279",
  "finding": "...",
  "report_name": "...",
  "report_date": "...",
  "page": 127,
  "severity": "HIGH",
  "source_type": "OFFICIAL_REPORT"
}
```

------------------------------------------------------------------------

# 16. Web Intelligence Agent

## Purpose

Identify external information that may explain or influence project
risk.

### Search categories

-   Land acquisition
-   Environmental clearance
-   Forest clearance
-   Court cases
-   Contractor disputes
-   Tender issues
-   Funding
-   Utility shifting
-   Approvals
-   Local issues
-   Natural events
-   Regulatory issues
-   Construction bottlenecks

### Output

``` json
{
  "source": "...",
  "publication_date": "...",
  "finding": "...",
  "potential_impact": "TIME_DELAY",
  "relevance": 0.91,
  "source_confidence": "MEDIUM"
}
```

Web information must be labelled as external evidence and must not
automatically become project fact.

------------------------------------------------------------------------

# 17. Evidence Verification Agent

The Evidence Verification Agent validates claims.

### Claim categories

``` text
OBSERVED
DERIVED
PREDICTED
EXTERNAL
RECOMMENDED
```

Example:

``` text
Claim:
Physical progress is significantly behind schedule.

Evidence:
PAIMANA monthly data

Classification:
DERIVED

Calculation:
Expected progress - actual progress
```

Another:

``` text
Claim:
A land acquisition issue may delay the project.

Evidence:
External article

Classification:
EXTERNAL

Confidence:
MEDIUM
```

------------------------------------------------------------------------

# 18. Risk Diagnosis Agent

Combines:

-   ML prediction
-   Project health
-   Anomalies
-   Historical trends
-   Review findings
-   External intelligence
-   Milestone status

### Output

``` json
{
  "overall_risk": "HIGH",
  "risk_score": 81,
  "confidence": 0.89,
  "drivers": [
    {
      "driver": "Progress lag",
      "severity": "HIGH"
    },
    {
      "driver": "Expenditure-progress divergence",
      "severity": "HIGH"
    }
  ]
}
```

------------------------------------------------------------------------

# 19. Risk Fusion Engine

Risk should not depend solely on the LLM.

Possible inputs:

``` text
ML Cost Risk
ML Time Risk
Financial Health
Schedule Health
Progress Health
Anomaly Risk
Milestone Risk
Review Evidence
External Risk
```

The fusion methodology must be configurable and validated using
historical data.

The system should support:

-   Rule-based fusion
-   Weighted scoring
-   Statistical calibration
-   ML-based meta-model in future versions

------------------------------------------------------------------------

# 20. Intervention Agent

## Purpose

Convert diagnosed risk into recommended monitoring actions.

### Examples

  -----------------------------------------------------------------------
  Risk Driver                         Recommended Action
  ----------------------------------- -----------------------------------
  Milestone delay                     Conduct milestone recovery review

  Progress stagnation                 Review implementation bottlenecks

  High expenditure / low progress     Investigate expenditure-output
                                      relationship

  Approval dependency                 Verify pending approvals

  Contractor issue                    Review contractual/resource
                                      constraints

  Schedule risk                       Request recovery schedule

  Cost risk                           Initiate cost-driver review
  -----------------------------------------------------------------------

Recommendations must include:

-   Risk driver
-   Action
-   Priority
-   Suggested responsible authority/area
-   Reason
-   Evidence
-   Monitoring frequency

------------------------------------------------------------------------

# 21. Reporting Agent

Generates:

-   Executive summary
-   Project risk report
-   Monthly change report
-   Ministry portfolio report
-   High-risk project report
-   Evidence report
-   Intervention report

------------------------------------------------------------------------

# 22. "What Changed Since Last Month?"

This should be a dedicated capability.

Compare:

``` text
Previous Month
      ↓
Current Month
```

Across:

-   Physical progress
-   Expenditure
-   Milestones
-   Schedule
-   Risk score
-   Cost-risk probability
-   Time-risk probability
-   New review findings
-   New external evidence

Output:

``` text
Risk increased from 71 → 81.

Physical progress:
40% → 42%

Expenditure:
₹X → ₹Y

New issue:
Milestone delay detected.

Conclusion:
Risk deterioration detected.
```

------------------------------------------------------------------------

# 23. MCP Architecture

The system must expose capabilities through domain-specific MCP servers.

## MCP Servers

``` text
PAIMANA MCP Server
ML MCP Server
Analytics MCP Server
Document MCP Server
Web Intelligence MCP Server
Knowledge MCP Server
```

------------------------------------------------------------------------

# 24. PAIMANA MCP Server

### Tools

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

# 25. ML MCP Server

### Tools

``` text
predict_cost_overrun()
predict_time_overrun()
calculate_risk_score()
get_model_metadata()
get_feature_importance()
validate_prediction_input()
run_batch_prediction()
```

The ML MCP server controls model execution and prevents agents from
directly manipulating model files.

------------------------------------------------------------------------

# 26. Analytics MCP Server

### Tools

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

# 27. Document MCP Server

### Tools

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

# 28. Web MCP Server

### Tools

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

# 29. Knowledge MCP Server

The Knowledge MCP Server exposes the RAG knowledge base.

### Sources

-   Review Reports
-   Flash Reports
-   Project documents
-   Government guidance
-   Risk taxonomy
-   Intervention playbooks
-   Historical project information

### Tools

``` text
semantic_search()
retrieve_context()
retrieve_project_evidence()
search_risk_knowledge()
search_intervention_playbook()
```

------------------------------------------------------------------------

# 30. Tool Registry

Every tool must have:

``` text
Tool ID
Tool name
Description
Input schema
Output schema
Version
Permission level
Timeout
Retry policy
Owner
MCP server
Audit requirement
```

Example:

``` json
{
  "tool_name": "predict_cost_overrun",
  "version": "1.0",
  "mcp_server": "ml-mcp",
  "permission": "READ",
  "timeout_seconds": 30
}
```

------------------------------------------------------------------------

# 31. Agent-to-Tool Policy

Agents must not call arbitrary tools.

``` text
Agent
 ↓
Permission Check
 ↓
Tool Registry
 ↓
MCP Server
 ↓
Tool
```

Each agent receives only the tools it requires.

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

------------------------------------------------------------------------

# 32. RAG Architecture

``` text
Documents
   |
   v
Document Ingestion
   |
   v
Parsing / OCR
   |
   v
Chunking
   |
   v
Metadata enrichment
   |
   v
Embedding Model
   |
   v
Vector Database
   |
   v
Retriever
   |
   v
Reranker
   |
   v
Agent Context
```

Metadata should include:

``` text
project_id
report_name
report_date
page_number
ministry
sector
document_type
source_type
upload_date
```

------------------------------------------------------------------------

# 33. Data Architecture

``` text
                     DATA SOURCES
                          |
        +-----------------+-----------------+
        |                 |                 |
     PAIMANA         Flash Reports     Review Reports
        |                 |                 |
        +-----------------+-----------------+
                          |
                          v
                  Ingestion Layer
                          |
                          v
               Validation / Cleaning
                          |
                          v
                Temporal Alignment
                          |
                          v
                   Feature Store
                    /          \
                   /            \
                  v              v
             ML Models       Analytics
                  \              /
                   \            /
                    v          v
                  Project Intelligence
```

------------------------------------------------------------------------

# 34. Recommended Storage

## PostgreSQL

Use for:

-   Project metadata
-   Monthly observations
-   User data
-   Risk results
-   Audit records
-   Agent execution metadata

## Object Storage

Use for:

-   PDFs
-   Raw reports
-   Model files
-   Generated reports

## Vector Database

Use for:

-   Document chunks
-   Embeddings
-   Evidence retrieval

## Redis

Use for:

-   Cache
-   Temporary agent state
-   Rate limiting
-   Task coordination

------------------------------------------------------------------------

# 35. Feature Store

Every ML feature must be tied to a snapshot month.

Example:

``` text
project_id
snapshot_month

original_cost
cumulative_expenditure

original_start_date
original_completion_date

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

The feature pipeline must enforce:

> feature_timestamp \<= prediction_timestamp

------------------------------------------------------------------------

# 36. Coordinator Execution Modes

## Mode A -- Simple Query

``` text
User
 ↓
Coordinator
 ↓
Single Agent
 ↓
Tool
 ↓
Answer
```

## Mode B -- Project Analysis

``` text
Coordinator
 ├── History
 ├── Health
 ├── Prediction
 ├── Review
 └── Web
        ↓
     Diagnosis
        ↓
    Intervention
        ↓
     Report
```

## Mode C -- Portfolio Analysis

``` text
Coordinator
 ↓
Portfolio Data
 ↓
Batch Analytics
 ↓
ML Batch Prediction
 ↓
Risk Ranking
 ↓
Top Risk Projects
 ↓
Deep Analysis
```

------------------------------------------------------------------------

# 37. Agent State Model

Each execution should maintain structured state.

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
  "recommendations": [],
  "final_response": null
}
```

------------------------------------------------------------------------

# 38. Observability Layer

Observability must cover the entire agentic system.

``` text
User Request
     |
Coordinator
     |
Agent
     |
MCP
     |
Tool
     |
Data
```

Every layer produces telemetry.

------------------------------------------------------------------------

# 39. Distributed Tracing

Each request receives:

``` text
trace_id
session_id
request_id
```

Example:

``` text
TRACE-001
 |
 +-- Coordinator
      |
      +-- History Agent
      |     |
      |     +-- PAIMANA MCP
      |           |
      |           +-- get_project_history
      |
      +-- Prediction Agent
      |     |
      |     +-- ML MCP
      |           |
      |           +-- predict_cost_overrun
      |
      +-- Review Agent
      |
      +-- Web Agent
      |
      +-- Risk Agent
      |
      +-- Intervention Agent
```

------------------------------------------------------------------------

# 40. Observability Metrics

## System Metrics

-   Request count
-   Success rate
-   Error rate
-   P50 latency
-   P95 latency
-   P99 latency
-   Throughput

## Agent Metrics

-   Agent execution count
-   Agent failure rate
-   Agent latency
-   Tool-call count
-   Retry count
-   Context size
-   Output quality

## MCP Metrics

-   MCP availability
-   Tool latency
-   Tool failure rate
-   Timeout rate
-   Retry rate

------------------------------------------------------------------------

# 41. LLM Observability

Track:

``` text
model
model_version
prompt_version
input_tokens
output_tokens
reasoning_tokens where available
cached_tokens where available
latency
time-to-first-token
total cost
```

Also track:

-   Prompt length
-   Retrieved context size
-   Number of tool calls
-   Number of agent turns

------------------------------------------------------------------------

# 42. Cost Tracking Layer

The platform must provide per-request cost attribution.

``` text
User Request
     |
     +-- Coordinator Cost
     |
     +-- History Agent Cost
     |
     +-- Prediction Agent Cost
     |
     +-- Review Agent Cost
     |
     +-- Web Agent Cost
     |
     +-- Risk Agent Cost
     |
     +-- Reporting Agent Cost
     |
     v
Total Request Cost
```

## Cost Dimensions

-   Per request
-   Per user
-   Per project
-   Per agent
-   Per model
-   Per MCP server
-   Per tool
-   Per day
-   Per month
-   Per ministry
-   Per sector

------------------------------------------------------------------------

# 43. Cost Optimization

Use the least expensive suitable execution mechanism.

``` text
Calculation
    → Analytics Tool

Database query
    → PAIMANA MCP

ML prediction
    → ML MCP

Document retrieval
    → RAG

Simple response
    → Lightweight LLM

Complex synthesis
    → Strong reasoning model
```

The system should support configurable budgets.

Example:

``` text
max_cost_per_request
max_llm_calls
max_web_searches
max_agent_depth
max_execution_time
```

------------------------------------------------------------------------

# 44. Agent Evaluation Suite

Evaluation is a core product capability.

``` text
                    Evaluation Suite
                           |
        +------------------+------------------+
        |                  |                  |
   Agent Tests         Tool Tests        E2E Tests
        |                  |                  |
        v                  v                  v
  Accuracy            Schema validity    Decision quality
  Grounding           Error handling     Evidence quality
  Relevance           Timeout            Risk consistency
  Hallucination       Permissions        Recommendation
```

------------------------------------------------------------------------

# 45. Evaluation Dataset

Create a fixed benchmark dataset.

``` text
evaluation/
├── projects/
│   ├── high_risk/
│   ├── medium_risk/
│   ├── low_risk/
│   └── normal/
│
├── questions/
│   ├── history/
│   ├── prediction/
│   ├── evidence/
│   ├── diagnosis/
│   └── intervention/
│
└── expected_outputs/
```

------------------------------------------------------------------------

# 46. Agent Evaluation Metrics

## Coordinator

-   Task decomposition accuracy
-   Agent selection accuracy
-   Tool selection accuracy
-   Plan completion
-   Final answer completeness

## History Agent

-   Project identification accuracy
-   Chronology accuracy
-   Data retrieval accuracy
-   Summary faithfulness

## RAG Agent

-   Retrieval precision
-   Retrieval recall
-   Context relevance
-   Groundedness
-   Citation correctness

## Prediction Agent

-   Input correctness
-   Model version correctness
-   Prediction accuracy
-   Calibration
-   Data leakage

## Web Agent

-   Source relevance
-   Source credibility
-   Evidence extraction
-   Citation correctness
-   Freshness

## Risk Agent

-   Risk classification accuracy
-   Risk-driver accuracy
-   False alarms
-   Missed risks
-   Consistency

## Intervention Agent

-   Recommendation relevance
-   Risk-action alignment
-   Feasibility
-   Evidence support

------------------------------------------------------------------------

# 47. End-to-End Evaluation

Example benchmark:

``` text
Question:
Analyse Project X.

Expected:

Risk:
HIGH

Cost risk:
HIGH

Time risk:
MEDIUM

Drivers:
1. Progress lag
2. Expenditure-progress divergence

Evidence:
Official report + project history

Action:
Enhanced monitoring
```

Evaluation compares the system output against the benchmark.

------------------------------------------------------------------------

# 48. LLM Evaluation

Use a combination of:

1.  Deterministic tests
2.  Ground-truth datasets
3.  LLM-as-judge
4.  Human expert review

LLM-as-judge must not be the sole quality-control mechanism.

------------------------------------------------------------------------

# 49. Hallucination Evaluation

The evaluation suite must identify:

-   Unsupported project facts
-   Invented numbers
-   Invented report findings
-   Incorrect citations
-   Fake web sources
-   Incorrect dates
-   Unsupported recommendations

Target:

> Critical project facts must be grounded in available evidence.

------------------------------------------------------------------------

# 50. Guardrail Layer

## Input Guardrails

Check:

-   Valid project identifier
-   Query size
-   Tool permissions
-   Prompt injection attempts
-   Unauthorized operations
-   Invalid parameters

## Tool Guardrails

Check:

-   Agent permission
-   Tool schema
-   Parameter validity
-   Rate limit
-   Timeout
-   Data-access policy

## Output Guardrails

Check:

-   Unsupported claims
-   Missing evidence
-   Invalid calculations
-   Contradictions
-   Missing source labels
-   Policy violations

------------------------------------------------------------------------

# 51. Security Architecture

``` text
User
 ↓
Authentication
 ↓
Authorization / RBAC
 ↓
API Gateway
 ↓
Coordinator
 ↓
Agent Permissions
 ↓
MCP Permissions
 ↓
Data Access
```

## Roles

### Administrator

Full configuration and system management.

### Monitoring Officer

Project analysis and monitoring.

### Senior Officer

Portfolio-level decision support.

### Analyst

Read-only analytical access.

### Auditor

Read-only audit and trace access.

------------------------------------------------------------------------

# 52. Auditability

Every decision must be reproducible.

Store:

``` text
user
timestamp
project_id
trace_id

agent versions
model versions
prompt versions

tools called
MCP servers
input snapshot

retrieved evidence
ML predictions
calculated metrics

risk result
recommendation
final output
```

------------------------------------------------------------------------

# 53. Model Registry

Use a model registry.

Each model should have:

``` text
model_id
version
training period
training dataset
features
target definition
prediction horizon
metrics
calibration
created_at
approved_by
status
```

Example:

``` text
cost-overrun-v3
status = production
```

------------------------------------------------------------------------

# 54. Model Governance

A production model must not change silently.

Required process:

``` text
Train
 ↓
Evaluate
 ↓
Validate
 ↓
Register
 ↓
Approve
 ↓
Deploy
 ↓
Monitor
 ↓
Retrain / Retire
```

------------------------------------------------------------------------

# 55. Alerting System

## Risk Alert

Trigger when:

``` text
risk_score >= threshold
```

## Risk Escalation

Trigger when:

``` text
current_risk - previous_risk >= threshold
```

## Prediction Alert

Trigger when:

``` text
cost_overrun_probability >= threshold
```

## Anomaly Alert

Trigger when:

``` text
anomaly_score >= threshold
```

------------------------------------------------------------------------

# 56. Risk Levels

Suggested initial taxonomy:

``` text
0–29   LOW
30–49  MODERATE
50–69  ELEVATED
70–84  HIGH
85–100 CRITICAL
```

These thresholds must be configurable and empirically validated.

------------------------------------------------------------------------

# 57. Project Dashboard

## Overview

Display:

``` text
Project Name
Project ID
Ministry
Sector
Agency
State
```

## Risk

``` text
Overall Risk
Risk Score
Cost Risk
Time Risk
Implementation Risk
```

## Health

``` text
Cost Utilisation
Schedule Utilisation
Physical Progress
Progress Gap
Expenditure-Progress Divergence
```

## Trend

``` text
Risk over time
Progress over time
Expenditure over time
```

## Evidence

``` text
PAIMANA
Review Reports
Web Intelligence
```

## Recommendations

``` text
Immediate Action
Medium-Term Action
Monitoring Frequency
```

------------------------------------------------------------------------

# 58. Portfolio Dashboard

Provide:

-   Total projects
-   High-risk projects
-   Critical projects
-   Ministry-wise risk
-   Sector-wise risk
-   State-wise risk
-   Cost-risk distribution
-   Time-risk distribution
-   Risk trend
-   New risk escalations
-   Risk reductions

------------------------------------------------------------------------

# 59. Project Search

Support:

``` text
Project ID
Project Name
Ministry
Department
Agency
State
Sector
Risk Level
Date
```

Natural-language search:

> Show high-risk infrastructure projects with high expenditure but low
> physical progress.

------------------------------------------------------------------------

# 60. Conversational Assistant

Example questions:

### Project

> What is the current risk of Project X?

### History

> What happened to this project over the last 12 months?

### Prediction

> Which projects are most likely to experience cost overrun?

### Diagnosis

> Why is this project high risk?

### Evidence

> What official evidence supports this risk?

### Change

> What changed since last month?

### Intervention

> What action should the monitoring authority take?

### Portfolio

> Which sectors have the highest concentration of high-risk projects?

------------------------------------------------------------------------

# 61. Decision Report

Every detailed analysis should follow a standardized format.

``` text
PROJECT RISK INTELLIGENCE REPORT

1. Project Overview

2. Current Status

3. Overall Risk

4. Cost-Overrun Prediction

5. Time-Overrun Prediction

6. Project Health

7. Historical Trend

8. Anomalies

9. Major Risk Drivers

10. Review Report Evidence

11. External Intelligence

12. What Changed Since Last Month?

13. Recommended Interventions

14. Monitoring Level

15. Confidence

16. Evidence & Sources

17. Model Information
```

------------------------------------------------------------------------

# 62. Example Final Output

``` text
PROJECT RISK: HIGH
Risk Score: 81/100

Cost Overrun Probability: 82%
Time Overrun Probability: 76%

Primary Risk Drivers:

1. Physical progress is behind expected progress.
2. Expenditure is advancing faster than physical progress.
3. Recent progress trend has weakened.
4. Milestone slippage has been detected.
5. Supporting evidence exists in the latest official review material.

Recommended Action:

Place project under enhanced monitoring and initiate
a milestone/progress recovery review.

Confidence: HIGH

Evidence:
- Project monthly data
- Official review report
- ML prediction
- Derived project-health metrics
```

------------------------------------------------------------------------

# 63. API Requirements

## Project Analysis

``` http
POST /api/v1/projects/{project_id}/analyse
```

## Project Risk

``` http
GET /api/v1/projects/{project_id}/risk
```

## Project History

``` http
GET /api/v1/projects/{project_id}/history
```

## Predictions

``` http
GET /api/v1/projects/{project_id}/predictions
```

## Evidence

``` http
GET /api/v1/projects/{project_id}/evidence
```

## Recommendations

``` http
GET /api/v1/projects/{project_id}/recommendations
```

## Portfolio

``` http
GET /api/v1/portfolio/risk
```

------------------------------------------------------------------------

# 64. Non-Functional Requirements

## Performance

Target initial MVP:

-   Simple query: \< 5 seconds
-   Project analysis: \< 30 seconds where external search is not
    required
-   Complex analysis: \< 60 seconds
-   Portfolio batch analysis: asynchronous

Targets should be validated under realistic infrastructure.

## Availability

Target:

> 99.5% for production API services.

## Scalability

The system should support:

-   Thousands of projects
-   Millions of monthly observations
-   Large report collections
-   Concurrent users
-   Batch prediction

## Reliability

-   Tool retry
-   Timeout
-   Circuit breaker
-   Graceful degradation
-   Failure isolation

------------------------------------------------------------------------

# 65. Graceful Degradation

If web search fails:

``` text
Use PAIMANA + Review Reports
```

If Review Report retrieval fails:

``` text
Use PAIMANA + ML + Analytics
```

If ML model fails:

``` text
Show analytical health indicators
and explicitly state that ML prediction is unavailable.
```

The system must never fabricate a missing result.

------------------------------------------------------------------------

# 66. Agent Failure Handling

Each agent should return:

``` json
{
  "status": "SUCCESS | PARTIAL | FAILED",
  "result": {},
  "error": null,
  "confidence": 0.0,
  "evidence": []
}
```

Coordinator behavior:

``` text
SUCCESS
 → continue

PARTIAL
 → continue with warning

FAILED
 → retry / alternative source / degrade gracefully
```

------------------------------------------------------------------------

# 67. Prompt Management

Prompts must be version controlled.

``` text
prompts/
├── coordinator/
├── project_history/
├── prediction/
├── review/
├── web/
├── risk/
├── intervention/
└── reporting/
```

Each prompt should have:

``` text
prompt_id
version
purpose
variables
expected output schema
evaluation status
```

------------------------------------------------------------------------

# 68. Configuration Management

Configurable parameters:

``` text
risk thresholds
model version
prediction horizon
agent timeout
MCP timeout
retry count
web search limit
RAG top-k
reranking threshold
cost budget
alert threshold
```

No critical threshold should be hidden inside agent prompts.

------------------------------------------------------------------------

# 69. Recommended Technology Stack

  Layer                 Technology
  --------------------- ------------------------------------------
  Frontend              React / Next.js
  Backend               Python / FastAPI
  Agent orchestration   LangGraph or custom orchestration
  MCP                   MCP-compatible Python/TypeScript servers
  ML                    scikit-learn / XGBoost / LightGBM
  Model registry        MLflow
  SQL                   PostgreSQL
  Vector DB             Qdrant / pgvector
  Cache                 Redis
  PDF processing        PyMuPDF + OCR
  Embeddings            NVIDIA Nemotron Embed 1B or equivalent
  Object storage        MinIO
  Tracing               OpenTelemetry
  Metrics               Prometheus
  Dashboard             Grafana
  Logs                  Loki / Elasticsearch
  Tests                 pytest
  Containers            Docker
  Orchestration         Kubernetes when required

------------------------------------------------------------------------

# 70. Repository Structure

``` text
project-monitoring-ai/
│
├── apps/
│   ├── api/
│   ├── frontend/
│   └── admin-dashboard/
│
├── agents/
│   ├── coordinator/
│   ├── data_intelligence/
│   ├── prediction/
│   ├── project_health/
│   ├── review_intelligence/
│   ├── web_intelligence/
│   ├── evidence/
│   ├── risk_diagnosis/
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
│   ├── database/
│   ├── ml/
│   ├── statistics/
│   ├── documents/
│   ├── web/
│   └── search/
│
├── models/
│   ├── cost_overrun/
│   ├── time_overrun/
│   └── risk/
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── features/
│   └── evaluation/
│
├── rag/
│   ├── ingestion/
│   ├── chunking/
│   ├── embeddings/
│   ├── retrieval/
│   └── reranking/
│
├── evaluation/
│   ├── datasets/
│   ├── agent_tests/
│   ├── rag_tests/
│   ├── model_tests/
│   ├── integration_tests/
│   └── benchmarks/
│
├── observability/
│   ├── tracing/
│   ├── metrics/
│   ├── logging/
│   └── dashboards/
│
├── cost_tracking/
│   ├── token_tracker/
│   ├── model_cost/
│   ├── tool_cost/
│   └── budget_manager/
│
├── security/
│   ├── auth/
│   ├── rbac/
│   ├── guardrails/
│   └── audit/
│
├── prompts/
├── configs/
├── tests/
├── docker/
└── docs/
```

------------------------------------------------------------------------

# 71. MVP Definition

The first implementation should not attempt every capability.

## MVP Phase 1

Implement:

``` text
PAIMANA/Flash Report Data
        ↓
Data Cleaning
        ↓
Feature Engineering
        ↓
Cost ML Model
        ↓
Project Health
        ↓
Coordinator Agent
        ↓
Project History Agent
        ↓
Risk Diagnosis
        ↓
Dashboard
```

## MVP Phase 2

Add:

``` text
Review Report RAG
Anomaly Detection
What Changed
Evidence Verification
```

## MVP Phase 3

Add:

``` text
Web Intelligence
Intervention Agent
Time Overrun Model
Portfolio Intelligence
Alerts
```

## Production Phase

Add:

``` text
Full MCP architecture
Evaluation suite
Observability
Cost tracking
RBAC
Audit
Model registry
Automated monitoring
```

------------------------------------------------------------------------

# 72. Acceptance Criteria

## AC-01 -- Project Identification

Given a valid project ID, the system returns the correct canonical
project record.

## AC-02 -- Historical Analysis

The system reconstructs monthly project history in chronological order.

## AC-03 -- Cost Prediction

The system produces a cost-overrun probability using a registered model
and snapshot-date features.

## AC-04 -- No Data Leakage

No feature may use information occurring after the prediction snapshot.

## AC-05 -- Health Analysis

The system calculates cost, schedule and physical-progress metrics
deterministically.

## AC-06 -- Evidence

High-risk explanations contain supporting evidence.

## AC-07 -- Source Attribution

The system distinguishes official data, reports, web evidence,
calculations and ML predictions.

## AC-08 -- Recommendations

High-risk projects produce risk-aligned recommended actions.

## AC-09 -- Observability

Every agent/tool execution produces a trace.

## AC-10 -- Cost Tracking

LLM and tool costs are attributable to requests and agents.

## AC-11 -- Evaluation

Agent and end-to-end benchmark tests can be executed automatically.

## AC-12 -- Auditability

A completed analysis can be reconstructed using its trace ID.

------------------------------------------------------------------------

# 73. Success Metrics

## Prediction

-   Improved recall of future overrun projects
-   Good probability calibration
-   Reduced false negatives
-   Stable performance on time-based validation

## Agent System

-   High groundedness
-   Low hallucination rate
-   High evidence retrieval accuracy
-   High tool-call success rate

## Operations

-   Low failure rate
-   Low P95 latency
-   Predictable cost per analysis
-   High system availability

## Decision Support

-   High-quality risk explanations
-   Correct identification of risk drivers
-   Actionable recommendations
-   Positive expert evaluation

------------------------------------------------------------------------

# 74. Key Risks and Mitigations

  Risk                         Mitigation
  ---------------------------- --------------------------------------------
  Data leakage                 Point-in-time feature pipeline
  Poor data quality            Validation and data-quality agent
  LLM hallucination            Evidence verification + structured outputs
  Incorrect web information    Source verification + confidence
  Agent loops                  Max-depth / max-turn limits
  High LLM cost                Cost-aware routing
  Tool failures                Retry + graceful degradation
  Model drift                  Monitoring + model registry
  False alarms                 Calibration + threshold optimization
  Missed risks                 Recall-focused evaluation
  Unauthorized access          RBAC + MCP permissions
  Lack of explainability       Evidence and model metadata
  Non-reproducible decisions   Full audit trail

------------------------------------------------------------------------

# 75. End-to-End Example

User asks:

> Analyse the risk of Project 617279.

### Step 1 -- Coordinator

Identifies required workflow.

### Step 2 -- Project Identification

Retrieves canonical project.

### Step 3 -- History

Retrieves monthly history.

### Step 4 -- Health

Calculates:

``` text
Cost utilisation
Schedule utilisation
Progress gap
Expenditure-progress divergence
```

### Step 5 -- ML

Runs cost-overrun prediction.

### Step 6 -- Anomaly

Checks recent project behavior.

### Step 7 -- Review

Retrieves project-specific official evidence.

### Step 8 -- Web

Searches current external issues.

### Step 9 -- Diagnosis

Combines all evidence.

### Step 10 -- Verification

Checks every important claim.

### Step 11 -- Intervention

Generates recommended actions.

### Step 12 -- Reporting

Creates final project risk intelligence report.

### Step 13 -- Observability

Stores complete trace.

### Step 14 -- Cost Tracking

Calculates execution cost.

### Step 15 -- Evaluation

Logs quality metrics where applicable.

------------------------------------------------------------------------

# 76. Final Decision Pipeline

``` text
                 PROJECT DATA
                      |
                      v
              DATA VALIDATION
                      |
                      v
              FEATURE ENGINE
                      |
          +-----------+-----------+
          |                       |
          v                       v
     ML PREDICTION          PROJECT HEALTH
          |                       |
          +-----------+-----------+
                      |
                      v
              ANOMALY DETECTION
                      |
                      v
             PROJECT HISTORY
                      |
          +-----------+-----------+
          |                       |
          v                       v
     REVIEW REPORT           WEB INTELLIGENCE
          |                       |
          +-----------+-----------+
                      |
                      v
              EVIDENCE VERIFY
                      |
                      v
               RISK FUSION
                      |
                      v
              RISK DIAGNOSIS
                      |
                      v
               INTERVENTION
                      |
                      v
              FINAL DECISION
                      |
                      v
             OFFICER DASHBOARD


       ─────────────────────────────────
       OBSERVABILITY
       EVALUATION
       COST TRACKING
       SECURITY
       AUDIT
       GOVERNANCE
       ─────────────────────────────────
```

------------------------------------------------------------------------

# 77. Product Differentiator

The platform should be positioned as more than an AI chatbot.

It is a:

> **Predictive Project Monitoring and Decision Intelligence Platform**

with five integrated capabilities:

### 1. Predict

Predict future cost/time overrun risk.

### 2. Diagnose

Identify the major drivers of risk.

### 3. Verify

Ground conclusions in project data, reports and external evidence.

### 4. Prescribe

Recommend monitoring/intervention actions.

### 5. Monitor

Continuously compare new monthly information and identify risk
escalation.

------------------------------------------------------------------------

# 78. Final Product Definition

The completed platform should provide a single interface where an
authorized decision maker can select any monitored project and receive:

``` text
PROJECT
   |
   +-- Current Status
   |
   +-- Historical Timeline
   |
   +-- Financial Health
   |
   +-- Schedule Health
   |
   +-- Physical Progress
   |
   +-- Cost-Overrun Probability
   |
   +-- Time-Overrun Probability
   |
   +-- Anomalies
   |
   +-- Risk Score
   |
   +-- Risk Drivers
   |
   +-- Official Evidence
   |
   +-- External Intelligence
   |
   +-- What Changed
   |
   +-- Recommended Actions
   |
   +-- Monitoring Priority
   |
   +-- Confidence
   |
   +-- Complete Evidence Trail
   |
   +-- Model / Data Version
   |
   +-- Audit Trace
```

The final architecture therefore becomes:

> **Data → Analytics → ML Prediction → Agentic Investigation → Evidence
> Verification → Risk Fusion → Intervention → Decision → Continuous
> Monitoring**

with:

> **MCP → controlled tools and data access**

and:

> **Evaluation + Observability + Cost Tracking + Security + Audit →
> production-grade control plane.**

------------------------------------------------------------------------

# 79. Definition of Done

The product is considered ready for the initial production pilot when:

-   [ ] Project data is available through a controlled data layer.
-   [ ] Historical monthly project data can be reconstructed.
-   [ ] Cost-overrun model is registered and callable through ML MCP.
-   [ ] Point-in-time feature generation is implemented.
-   [ ] Project health metrics are deterministic and tested.
-   [ ] Coordinator can orchestrate multi-agent workflows.
-   [ ] Project History Agent works reliably.
-   [ ] Review Report RAG retrieves project-specific evidence.
-   [ ] Web Intelligence Agent returns source-attributed evidence.
-   [ ] Risk Diagnosis combines analytical and evidence signals.
-   [ ] Intervention Agent generates risk-aligned actions.
-   [ ] Reporting Agent produces standardized reports.
-   [ ] MCP servers enforce tool boundaries.
-   [ ] RBAC is implemented.
-   [ ] Guardrails are implemented.
-   [ ] Complete traces are available.
-   [ ] Token/tool cost is tracked.
-   [ ] Agent evaluation benchmark is available.
-   [ ] Regression tests run automatically.
-   [ ] Model versions are registered.
-   [ ] Audit records are retained.
-   [ ] System gracefully handles tool/model failures.
-   [ ] Dashboard exposes project and portfolio risk.
-   [ ] Human decision makers can inspect evidence before acting.

------------------------------------------------------------------------

# 80. Summary

The proposed system is a multi-agent predictive monitoring platform
centered around a **Coordinator Agent**.

The Coordinator does not replace deterministic analytics or ML. Instead,
it orchestrates specialized capabilities:

``` text
Coordinator Agent
        |
        +-- Data Intelligence
        +-- Project History
        +-- Project Health
        +-- Prediction
        +-- Anomaly Detection
        +-- Review Intelligence
        +-- Web Intelligence
        +-- Evidence Verification
        +-- Risk Diagnosis
        +-- Intervention
        +-- Reporting
```

Those agents access capabilities through:

``` text
MCP Servers
      |
      +-- PAIMANA
      +-- ML
      +-- Analytics
      +-- Documents
      +-- Web
      +-- Knowledge
```

The entire platform is governed by:

``` text
Evaluation
Observability
Cost Tracking
Security
Guardrails
Auditability
Model Governance
```

The resulting system transforms monthly project information into an
actionable decision chain:

> **Predict → Diagnose → Verify → Prescribe → Monitor.**
