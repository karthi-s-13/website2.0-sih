#!/usr/bin/env python
"""Phase 10 CLI: run the Intervention Agent (Diagnosis -> Driver
Classification -> Action Mapping -> Recommendation) for each of the 5
validation cohort projects.

Usage (from repo root, with the backend venv active):

    python scripts/recommend_interventions.py
    python scripts/recommend_interventions.py --no-web
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.intervention.service import recommend_interventions  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-web", action="store_true", help="Skip Phase 8 web evidence gathering")
    args = parser.parse_args()

    configure_logging()
    log = get_logger("recommend_interventions")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = recommend_interventions(session, project_id, include_web=not args.no_web)

            print(f"\n{'=' * 78}")
            print(f"{result.project_name}  ({result.project_id})")
            print(
                f"overall_risk={result.overall_risk}  "
                f"suggested_monitoring_level={result.suggested_monitoring_level}"
            )
            print(f"{'-' * 78}")
            if not result.recommendations:
                print("  No recommendations - no risk drivers identified.")
            for r in result.recommendations:
                print(f"  [{r.priority}] ({r.action_type}) {r.action}")
                print(f"      reason: {r.reason}")
                print(f"      review area: {r.review_area}  |  evidence: {len(r.evidence_ids)} item(s)")
    finally:
        session.close()


if __name__ == "__main__":
    main()
