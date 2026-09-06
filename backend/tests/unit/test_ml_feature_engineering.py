import sys
from pathlib import Path

import pandas as pd
import pytest

ML_DIR = Path(__file__).resolve().parents[3] / "ml"
if str(ML_DIR) not in sys.path:
    sys.path.insert(0, str(ML_DIR))

from pipeline.feature_engineering import FEATURE_COLUMNS, RAW_FEATURE_COLUMNS, FeatureEngineer  # noqa: E402


def make_fe() -> FeatureEngineer:
    """A FeatureEngineer with hand-picked fitted state, standing in for what
    pickle would normally restore from the real trained artifact."""
    fe = FeatureEngineer()
    fe.agency_keep_ = {"AAI", "NHAI", "MISSING"}
    fe.agency_freq_map_ = {"AAI": 0.2, "NHAI": 0.5, "MISSING": 0.05, "OTHER": 0.1}
    fe.state_keep_ = {"GUJARAT", "KARNATAKA", "MISSING"}
    fe.state_freq_map_ = {"GUJARAT": 0.3, "KARNATAKA": 0.25, "MISSING": 0.02, "OTHER": 0.05}
    return fe


def make_row(**overrides) -> pd.DataFrame:
    row = {
        "edition": "August 2025",
        "project_name": "Development of Keshod Airport",
        "agency": "AAI",
        "state": "Gujarat",
        "doa": "2025-02-01",
        "original_target_doa": "2027-02-01",
        "original_cost": 466.00,
        "cumulative_expenditure": 13.99,
        "physical_progress": 1.00,
    }
    row.update(overrides)
    return pd.DataFrame([row])


def test_output_columns_match_contract() -> None:
    fe = make_fe()
    out = fe.transform(make_row())
    assert list(out.columns) == FEATURE_COLUMNS


def test_missing_raw_column_raises() -> None:
    fe = make_fe()
    df = make_row().drop(columns=["doa"])
    with pytest.raises(ValueError):
        fe.transform(df)


def test_hand_computed_values() -> None:
    fe = make_fe()
    out = fe.transform(make_row()).iloc[0]

    assert out["planned_duration_months"] == pytest.approx(24)
    assert out["snapshot_elapsed_months"] == pytest.approx(6)
    assert out["schedule_progress_ratio"] == pytest.approx(0.25)
    assert out["original_cost"] == pytest.approx(466.00)
    assert out["cumulative_expenditure"] == pytest.approx(13.99)
    assert out["cost_burn_ratio"] == pytest.approx(13.99 / 466.00)
    assert out["physical_progress"] == pytest.approx(1.00)
    assert out["progress_spend_discrepancy"] == pytest.approx((13.99 / 466.00) - 0.01)
    assert out["progress_time_discrepancy"] == pytest.approx(0.01 - 0.25)
    assert out["edition_year"] == 2025
    assert out["edition_month"] == 8
    assert out["project_name_length"] == len("Development of Keshod Airport")
    assert out["project_name_word_count"] == 4
    assert out["agency_freq"] == pytest.approx(0.2)  # AAI is kept
    assert out["state_freq"] == pytest.approx(0.3)  # Gujarat is kept


def test_unkept_agency_and_state_fall_back_to_other() -> None:
    fe = make_fe()
    out = fe.transform(make_row(agency="POWERGRID", state="Madhya Pradesh")).iloc[0]
    assert out["agency_freq"] == pytest.approx(0.1)  # OTHER
    assert out["state_freq"] == pytest.approx(0.05)  # OTHER


def test_missing_agency_and_state_use_missing_bucket() -> None:
    fe = make_fe()
    out = fe.transform(make_row(agency=None, state=None)).iloc[0]
    assert out["agency_freq"] == pytest.approx(0.05)  # MISSING
    assert out["state_freq"] == pytest.approx(0.02)  # MISSING


def test_missing_doa_yields_null_schedule_features() -> None:
    fe = make_fe()
    out = fe.transform(make_row(doa=None)).iloc[0]
    assert pd.isna(out["planned_duration_months"])
    assert pd.isna(out["snapshot_elapsed_months"])
    assert pd.isna(out["schedule_progress_ratio"])
    # progress_time_discrepancy depends on schedule_progress_ratio too
    assert pd.isna(out["progress_time_discrepancy"])
    # cost-side features are unaffected by a missing doa
    assert out["cost_burn_ratio"] == pytest.approx(13.99 / 466.00)


def test_schedule_ratio_is_clipped() -> None:
    fe = make_fe()
    # elapsed way beyond planned duration -> ratio would be huge without clipping
    out = fe.transform(
        make_row(doa="2020-01-01", original_target_doa="2020-02-01", edition="January 2025")
    ).iloc[0]
    lo, hi = fe.schedule_ratio_clip
    assert out["schedule_progress_ratio"] == pytest.approx(hi)


def test_keyword_flags_case_insensitive() -> None:
    fe = make_fe()
    out = fe.transform(make_row(project_name="NEW ROAD Bridge Construction")).iloc[0]
    assert out["kw_road"] == 1.0
    assert out["kw_bridge"] == 1.0
    assert out["kw_port"] == 0.0


def test_raw_feature_columns_constant_has_no_revised_cost() -> None:
    assert "revised_cost" not in RAW_FEATURE_COLUMNS
