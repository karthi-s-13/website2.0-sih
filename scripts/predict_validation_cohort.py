#!/usr/bin/env python
"""Phase 3 CLI: run a cost-overrun prediction for each of the 5 validation
cohort projects, at their own latest observed month (run ingestion first).

Usage (from repo root, with the backend venv active):

    python scripts/predict_validation_cohort.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.prediction.service import predict_cost_overrun  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    configure_logging()
    log = get_logger("predict_validation_cohort")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None or project.latest_observation_month is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = predict_cost_overrun(session, project_id, project.latest_observation_month)
            log.info(
                "prediction",
                project_id=result.project_id,
                project_name=project.project_name,
                prediction_date=result.prediction_date,
                probability=round(result.probability, 4),
                risk_level=result.risk_level,
                model_version=result.model_version,
                feature_version=result.feature_version,
                leakage_check=result.leakage_check,
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
