import json
from pathlib import Path

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

import app.models  # noqa: F401  (registers models on Base.metadata)
from app.core.db import Base
from app.core.errors import DataQualityFailureError, NotFoundError
from app.models.prediction import Prediction
from app.models.project import Project
from app.services.ingestion.pipeline import ingest_directory
from app.services.prediction.model_loader import FEATURE_ENGINEERING_VERSION
from app.services.prediction.service import predict_cost_overrun

RAW_DIR = Path(__file__).resolve().parents[3] / "data" / "raw" / "flash_reports"
VALID_PROJECT_IDS = ["617069", "619054", "616672", "617184", "617279"]
VALID_RISK_LEVELS = {"LOW", "MODERATE", "ELEVATED", "HIGH", "CRITICAL"}


@pytest.fixture
def session() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(bind=engine)
    with Session(engine) as s:
        yield s


@pytest.fixture
def ingested_session(session: Session) -> Session:
    ingest_directory(session, RAW_DIR)
    return session


def test_all_five_validation_projects_receive_valid_predictions(ingested_session: Session) -> None:
    """Exit criterion: all five projects receive valid model predictions for
    their selected as-of dates (each project's own latest observation month)."""
    for project_id in VALID_PROJECT_IDS:
        project = ingested_session.get(Project, project_id)
        as_of_date = project.latest_observation_month

        result = predict_cost_overrun(ingested_session, project_id, as_of_date)

        assert result.project_id == project_id
        assert result.risk_type == "cost_overrun"
        assert 0.0 <= result.probability <= 1.0
        assert result.risk_level in VALID_RISK_LEVELS
        assert result.model_version.startswith("cost-overrun-lightgbm-")
        assert result.feature_version == FEATURE_ENGINEERING_VERSION
        assert result.leakage_check == "PASSED"


def test_prediction_is_persisted(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "617069")
    result = predict_cost_overrun(ingested_session, "617069", project.latest_observation_month)

    rows = ingested_session.query(Prediction).filter_by(project_id="617069").all()
    assert len(rows) == 1
    assert rows[0].probability == pytest.approx(result.probability)
    assert rows[0].risk_level == result.risk_level
    assert rows[0].model_version == result.model_version


def test_prediction_does_not_use_revised_cost(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "617069")
    predict_cost_overrun(ingested_session, "617069", project.latest_observation_month)

    row = ingested_session.query(Prediction).filter_by(project_id="617069").first()
    raw_features = json.loads(row.raw_features_json)
    assert "revised_cost" not in raw_features
    assert set(raw_features.keys()) == {
        "edition",
        "project_name",
        "agency",
        "state",
        "doa",
        "original_target_doa",
        "original_cost",
        "cumulative_expenditure",
        "physical_progress",
    }


def test_prediction_is_deterministic(ingested_session: Session) -> None:
    project = ingested_session.get(Project, "616672")
    first = predict_cost_overrun(ingested_session, "616672", project.latest_observation_month)
    second = predict_cost_overrun(ingested_session, "616672", project.latest_observation_month)
    assert first.probability == second.probability
    assert first.risk_level == second.risk_level


def test_unknown_project_raises_not_found(ingested_session: Session) -> None:
    with pytest.raises(NotFoundError):
        predict_cost_overrun(ingested_session, "does-not-exist", __import__("datetime").date(2025, 1, 1))


def test_prediction_before_any_observation_raises_data_quality_failure(ingested_session: Session) -> None:
    from datetime import date

    project = ingested_session.get(Project, "617069")
    before_first = date(project.first_observation_month.year - 1, 1, 1)
    with pytest.raises(DataQualityFailureError):
        predict_cost_overrun(ingested_session, "617069", before_first)


def test_prediction_uses_latest_observation_at_or_before_snapshot(ingested_session: Session) -> None:
    """A prediction date between two observed months must use the earlier one,
    never a later (future-relative-to-snapshot) observation."""
    project = ingested_session.get(Project, "617069")
    first_month = project.first_observation_month  # 2025-07-01
    mid_month_date = first_month.replace(day=1)

    result = predict_cost_overrun(ingested_session, "617069", mid_month_date)
    row = ingested_session.query(Prediction).filter_by(project_id="617069").first()
    assert row.input_observation_month == first_month
    assert result.leakage_check == "PASSED"
