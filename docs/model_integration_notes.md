# Model Integration Notes (Phase 3)

`model/lightgbm_cost_overrun_model.pkl` is a `joblib`-dumped Python **dict**:

```python
{
  "pipeline": sklearn.pipeline.Pipeline(steps=[
      ("fe", pipeline.feature_engineering.FeatureEngineer(...)),   # custom, see below
      ("impute", sklearn.impute.SimpleImputer(strategy="median", add_indicator=True)),
      ("clf", lightgbm.LGBMClassifier(...)),
  ]),
  "model_type": "lightgbm",
  "raw_feature_cols": ["edition", "project_name", "agency", "state", "doa",
                        "original_target_doa", "original_cost",
                        "cumulative_expenditure", "physical_progress"],
  "best_params": {...},                # LightGBM hyperparameters used
  "optimal_threshold": 0.3865956421699089,   # F1-optimal binary decision threshold from training
  "oof_metrics": {"roc_auc": 0.797, "pr_auc": 0.435, "brier_score": 0.0975,
                   "f1": 0.447, "precision": 0.426, "recall": 0.470},
  "trained_at": "2026-08-30T16:59:28",
  "n_training_rows": 48894,
  "random_state": 42,
}
```

All of the above is **read directly from the artifact** - not invented.

## The missing piece: `pipeline.feature_engineering.FeatureEngineer`

Unpickling a custom class instance requires the class to be importable at the
exact dotted path used when it was pickled (`pipeline.feature_engineering.FeatureEngineer`).
That module does not ship with the artifact. Pickle only restores an
instance's **fitted state** (`__dict__`); it never stores method code. So:

- The instance's fitted attributes are recovered **exactly**, byte-for-byte,
  by pickle itself: `rare_threshold=0.01`, `schedule_ratio_clip=(-1.0, 3.0)`,
  `agency_keep_` (18 codes), `agency_freq_map_` (19 entries incl. `OTHER`),
  `state_keep_` (30 states incl. `MISSING`), `state_freq_map_` (31 entries
  incl. `OTHER`). These are ground truth from training, not reconstructed.
- The `transform()` **logic** that combines those fitted values with raw
  inputs is *not* recoverable from the pickle. `ml/pipeline/feature_engineering.py`
  is a reconstruction, built from evidence rather than from source code that
  no longer exists. This document records that evidence so the reconstruction
  can be audited and revised if better evidence turns up.

## Evidence used, and what it established

1. **`raw_feature_cols`** (from the artifact dict) gives the exact 9 raw
   inputs and their names - notably `doa` (date of approval) and
   `original_target_doa` (original target completion date), **not**
   `start_date`. The model was trained against approval date, not start date.
   No `revised_cost` column exists anywhere in the raw inputs - confirming the
   model was never trained on it, so integration cannot leak it either.

2. **`SimpleImputer.feature_names_in_`** (recovered from the fitted imputer
   object, not guessed) gives the exact 23 engineered feature names, in
   order: `planned_duration_months, snapshot_elapsed_months,
   schedule_progress_ratio, original_cost, cumulative_expenditure,
   cost_burn_ratio, physical_progress, progress_spend_discrepancy,
   progress_time_discrepancy, edition_year, edition_month,
   project_name_length, project_name_word_count, kw_road, kw_bridge,
   kw_power_solar, kw_pipeline_oil_gas, kw_rail_metro, kw_port,
   kw_irrigation, kw_building, agency_freq, state_freq`.
   `ml/pipeline/feature_engineering.py::FEATURE_COLUMNS` reproduces this list
   verbatim and a runtime assertion (`app/services/prediction/model_loader.py`)
   checks the reconstruction's output against it on every load.

3. **`SimpleImputer.statistics_`** (training medians per feature) resolved
   two scale ambiguities that formulas alone could not:
   - `physical_progress` median = 50.0 → confirms this column is on the
     **0-100 percent scale**, a direct passthrough of the raw value (not
     divided by 100), unlike features with an explicit `_ratio` suffix.
   - `schedule_progress_ratio` median = 1.42, within the `(-1, 3)` clip range
     → confirms a ratio scale (`elapsed / planned`, clipped), consistent with
     `schedule_ratio_clip`.
   - `cost_burn_ratio` median = 0.54 → consistent with a simple
     `cumulative_expenditure / original_cost` ratio.

4. **`MissingIndicator.features_`** (which of the 23 columns had *any*
   missing values during training: indices `[0,1,2,4,5,6,7,8]`) confirms
   which derived features are legitimately nullable
   (`planned_duration_months`, `snapshot_elapsed_months`,
   `schedule_progress_ratio`, `cumulative_expenditure`, `cost_burn_ratio`,
   `physical_progress`, `progress_spend_discrepancy`,
   `progress_time_discrepancy`) and, importantly, that **`original_cost`
   (index 3) was never missing** in training - matching real Flash Report
   data, where original cost is essentially always known.

5. **Naming conventions** (`_ratio` suffix vs. bare names; `kw_*` prefix;
   `*_freq` suffix) informed the remaining formulas:
   - `cost_burn_ratio = cumulative_expenditure / original_cost`
   - `progress_spend_discrepancy = cost_burn_ratio - (physical_progress / 100)`
   - `progress_time_discrepancy = (physical_progress / 100) - schedule_progress_ratio`
   - `agency_freq` / `state_freq`: frequency-encode the raw category, using
     the fitted keep-set to decide whether the category gets its own
     frequency or falls back to the `OTHER` bucket (both fitted maps contain
     an explicit `OTHER` entry - verified directly on the object, not assumed).

## Remaining genuine uncertainty (flagged, not hidden)

- **`kw_road`, `kw_bridge`, `kw_power_solar`, `kw_pipeline_oil_gas`,
  `kw_rail_metro`, `kw_port`, `kw_irrigation`, `kw_building`**: only the
  *names* survive; no keyword list does. `_KEYWORDS` in
  `feature_engineering.py` is a best-effort reconstruction from the category
  names themselves. These are weak binary signals feeding a 23+8-feature
  gradient-boosted ensemble, so imperfect recall here has bounded impact -
  but it is real, acknowledged uncertainty, not verified fact.
- **Agency/state input format**: the raw `agency` value is passed as the
  short code (e.g. `"POWERGRID"`, `"AAI"`), matching the vocabulary of
  `agency_keep_`/`agency_freq_map_` (all short codes) rather than the
  descriptive `"Power Grid Corporation of India Limited [POWERGRID]"` string
  our Flash Report CSVs also carry. This is inferred from vocabulary
  consistency, not confirmed against training code.
- **Missing-category encoding**: an absent agency/state is encoded as the
  literal string `"MISSING"` before the keep-set lookup, based on `"MISSING"`
  being present as its own category in both `agency_keep_` and `state_keep_`
  (strongly suggesting nulls were filled with that literal at training time).
- **Prediction horizon**: no explicit horizon (e.g. "12 months") is stored in
  the artifact. Rather than inventing one, the API omits a fabricated
  `prediction_horizon_months` value.

## Validation performed

- `ml/pipeline/feature_engineering.py`'s output columns are asserted equal
  (name-for-name, in order) to `SimpleImputer.feature_names_in_` at model
  load time.
- End-to-end smoke test: a real KPS1 (project 617069) observation run through
  the reconstructed `FeatureEngineer` produced `cost_burn_ratio` and
  `schedule_progress_ratio` values that match this project's independently
  computed Phase 2 `cost_utilisation`/`schedule_utilisation` features exactly
  for the same month (0.030021... and 0.25 respectively) - a meaningful
  cross-check between two independently-derived formulas.
- `pipe.predict_proba(...)` runs without error and returns a valid
  two-class probability distribution.

## What this means for "do not retrain"

Per the Phase 3 instructions, this integration does not retrain or alter the
model's learned parameters (the `LGBMClassifier`'s boosted trees, the
imputer's medians, or the `FeatureEngineer`'s fitted frequency maps/keep-sets
are all used exactly as recovered from the artifact). Only the
*preprocessing code path* needed reconstruction, because it is code, not
data, and code is not part of a pickle. If the original `pipeline` package
source is ever located, it should replace this reconstruction directly - the
column contract (`FEATURE_COLUMNS`, `RAW_FEATURE_COLUMNS`) would not need to
change for that swap to be safe.
