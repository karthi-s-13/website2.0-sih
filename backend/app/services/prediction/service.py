"""Cost-overrun prediction service (Phase 3).

Orchestrates: point-in-time lookup -> leakage validation -> raw feature row
-> pretrained pipeline -> risk classification -> logging.

The pretrained model has its OWN internal preprocessing (ml/pipeline/
feature_engineering.py), entirely separate from Phase 2's `project_monthly_features`
feature store. Phase 2's engineered features are not inputs to this model -
the model was trained against its own 9 raw columns (see
docs/model_integration_notes.md). Both point-in-time disciplines are enforced
independently.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import date

import pandas as pd
from sqlalchemy.orm import Session

from app.core.errors import DataLeakageError, DataQualityFailureError, NotFoundError
from app.models.prediction import Prediction
from app.models.project import Project, ProjectMonthlyObservation
from app.services.features.pipeline import filter_point_in_time, validate_point_in_time
from app.services.prediction.model_loader import (
    FEATURE_ENGINEERING_VERSION,
    RISK_TYPE,
    load_model_bundle,
)
from app.services.prediction.risk import risk_level_for_probability


@dataclass(frozen=True)
class PredictionResult:
    project_id: str
    prediction_date: str
    risk_type: str
    probability: float
    risk_level: str
    model_version: str
    feature_version: str
    leakage_check: str


def _month_start(d: date) -> date:
    return date(d.year, d.month, 1)


def _format_edition(d: date) -> str:
    return d.strftime("%B %Y")


def predict_cost_overrun(session: Session, project_id: str, prediction_date: date) -> PredictionResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")

    snapshot_month = _month_start(prediction_date)

    all_observations = (
        session.query(ProjectMonthlyObservation)
        .filter_by(project_id=project_id)
        .order_by(ProjectMonthlyObservation.observation_month)
        .all()
    )
    window = filter_point_in_time(all_observations, snapshot_month)
    if not window:
        raise DataQualityFailureError(
            f"no observation available for project {project_id} at or before {snapshot_month.isoformat()}"
        )
    validate_point_in_time(window, snapshot_month)  # raises DataLeakageError if ever violated

    current = window[-1]

    raw_row = {
        "edition": _format_edition(current.observation_month),
        "project_name": project.project_name,
        "agency": project.agency_code,
        "state": project.state,
        "doa": current.date_of_approval,
        "original_target_doa": current.target_completion_date,
        "original_cost": current.original_cost_crore,
        "cumulative_expenditure": current.cumulative_expenditure_crore,
        "physical_progress": current.physical_progress_percent,
    }

    bundle = load_model_bundle()
    raw_df = pd.DataFrame([raw_row], columns=bundle.raw_feature_cols)

    try:
        probability = float(bundle.pipeline.predict_proba(raw_df)[0][1])
    except DataLeakageError:
        raise
    except Exception as exc:  # noqa: BLE001
        raise DataQualityFailureError(f"model inference failed: {exc}") from exc

    risk_level = risk_level_for_probability(probability)

    result = PredictionResult(
        project_id=project_id,
        prediction_date=prediction_date.isoformat(),
        risk_type=RISK_TYPE,
        probability=probability,
        risk_level=risk_level,
        model_version=bundle.model_version,
        feature_version=FEATURE_ENGINEERING_VERSION,
        leakage_check="PASSED",
    )

    session.add(
        Prediction(
            project_id=project_id,
            prediction_date=prediction_date,
            snapshot_month=snapshot_month,
            input_observation_month=current.observation_month,
            risk_type=result.risk_type,
            probability=result.probability,
            risk_level=result.risk_level,
            model_version=result.model_version,
            feature_version=result.feature_version,
            leakage_check=result.leakage_check,
            raw_features_json=json.dumps(
                {k: (v.isoformat() if isinstance(v, date) else v) for k, v in raw_row.items()}
            ),
        )
    )
    session.commit()

    return result
