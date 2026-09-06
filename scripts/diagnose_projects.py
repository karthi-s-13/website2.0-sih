#!/usr/bin/env python
"""Phase 9 CLI: run the Risk Diagnosis Agent (Evidence Fusion + Risk Fusion
+ driver identification) for each of the 5 validation cohort projects.

Usage (from repo root, with the backend venv active):

    python scripts/diagnose_projects.py
    python scripts/diagnose_projects.py --no-web
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
from app.services.diagnosis.service import diagnose_project  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--no-web", action="store_true", help="Skip Phase 8 web evidence gathering")
    args = parser.parse_args()

    configure_logging()
    log = get_logger("diagnose_projects")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = diagnose_project(session, project_id, include_web=not args.no_web)

            print(f"\n{'=' * 78}")
            print(f"{result.project_name}  ({result.project_id})")
            print(
                f"overall_risk={result.overall_risk}  risk_score={result.risk_score}  "
                f"confidence={result.confidence}  fusion_version={result.fusion_version}"
            )
            print(f"{'-' * 78}")
            if not result.drivers:
                print("  No risk drivers identified.")
            for d in result.drivers:
                print(f"  {d.rank}. [{d.severity}] {d.driver}")
                for eid in d.evidence_ids:
                    item = next((e for e in result.evidence if e.evidence_id == eid), None)
                    if item:
                        print(f"       - ({item.category}) {item.description[:120]}")
            print(f"  Evidence pool: {len(result.evidence)} items")
    finally:
        session.close()


if __name__ == "__main__":
    main()
