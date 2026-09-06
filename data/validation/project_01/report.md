# Validation Report — Project 01

**Report Generated:** 2026-09-04T09:03:41.551335+00:00  
**Report Version:** phase-5-v1

## 1. Project Profile

| Field | Value |
|---|---|
| Project ID | `617069` |
| Project Name | Augmentation of Transformation Capacity at KPS1 [GIS] and KPS2 [GIS] [Phase-V Part B1 and Part B2 Scheme] [SPV Name- POWERGRID KPS1 and 2 Augmentation Transmission Limited] |
| Agency | Power Grid Corporation of India Limited [POWERGRID] |
| State | Gujarat |
| Original Cost | ₹466.00 Cr |
| Revised Cost | ₹466.00 Cr |
| Cumulative Expenditure (as of 2026-07-01) | ₹154.90 Cr |
| As-of Date | 2026-07-01 |

## 2. Current Health

| Metric | Value |
|---|---|
| **Overall Health** | **ELEVATED** |
| Cost Utilisation | 33.2% |
| Schedule Utilisation | 70.8% |
| Physical Progress | 37.0% |
| Expected Progress | 70.8% |
| Progress Gap | -33.8 pts |
| Expenditure–Progress Divergence | -3.8 pts |

## 3. ML Cost-Overrun Risk

| Metric | Value |
|---|---|
| **Risk Level** | **LOW** |
| Probability | 13.0% |
| Model Version | `cost-overrun-lightgbm-2026-08-30T16:59:28` |
| Feature Version | `ml-fe-v1-reconstructed` |
| Leakage Check | PASSED |
| Prediction Timestamp | 2026-09-04T09:03:41.551335+00:00 |

## 4. Revised Cost Interpretation

> No revised cost is currently recorded as of the selected observation date. The ML probability is a forward-looking risk estimate, not a confirmed outcome.

## 5. Historical Trend

| Metric | Value |
|---|---|
| Observations | 13 |
| First Observation | 2025-07-01 |
| Latest Observation | 2026-07-01 |
| Recent Trend | IMPROVING |
| Monthly Progress Change | 0.00 pts |
| Progress Slope (3-mo avg) | 4.83 pts/mo |
| Consecutive Stagnant Months | 1 |

### Observation Timeline

| Month | Cumulative Expenditure (₹ Cr) | Physical Progress (%) |
|---|---|---|
| 2025-07-01 | 6.99 | 0.0 |
| 2025-08-01 | 13.99 | 1.0 |
| 2025-09-01 | 23.30 | 1.0 |
| 2025-10-01 | 24.30 | 2.0 |
| 2025-11-01 | 23.99 | 1.0 |
| 2025-12-01 | 23.99 | 1.0 |
| 2026-01-01 | 27.96 | 2.0 |
| 2026-02-01 | 41.94 | 10.0 |
| 2026-03-01 | 69.90 | 18.0 |
| 2026-04-01 | 93.20 | 22.5 |
| 2026-05-01 | 111.84 | 30.0 |
| 2026-06-01 | 143.48 | 37.0 |
| 2026-07-01 | 154.90 | 37.0 |

### Derived Events

| Month | Type | Description |
|---|---|---|
| 2025-07-01 | PROJECT_FIRST_OBSERVED | Project first appears in Flash Report data (2025-07). |

## 6. Data Quality

**Total Issues:** 2

| Severity | Count |
|---|---|
| WARNING | 2 |

| Type | Severity | Field | Original Value | Action |
|---|---|---|---|---|
| NON_MONOTONIC_CUMULATIVE_EXPENDITURE | WARNING | cumulative_expenditure_crore | 23.99 | FLAGGED_NOT_CORRECTED |
| NON_MONOTONIC_PHYSICAL_PROGRESS | WARNING | physical_progress_percent | 1.0 | FLAGGED_NOT_CORRECTED |


---

*This report was generated deterministically from the ingested data using the Phase 1–4 
pipeline. It is reproducible by re-running `python scripts/validate_cohort.py`.*
