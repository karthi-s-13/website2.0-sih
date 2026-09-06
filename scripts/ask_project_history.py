#!/usr/bin/env python
"""Phase 6 CLI: ask the Project History Agent "What happened to this
project?" for each of the 5 validation cohort projects (run ingestion first).

Usage (from repo root, with the backend venv active):

    python scripts/ask_project_history.py
    python scripts/ask_project_history.py --question "Why is this project risky?"
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
from app.services.history.service import DEFAULT_QUESTION, get_project_history  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    # Rupee/other non-ASCII characters in descriptions must not crash the
    # script on a non-UTF-8 console (e.g. Windows cp1252).
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args()

    configure_logging()
    log = get_logger("ask_project_history")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None or project.latest_observation_month is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = get_project_history(session, project_id, question=args.question)

            print(f"\n{'=' * 78}")
            print(f"{result.project_name}  ({result.project_id})")
            print(f"Q: {result.question}")
            print(f"{'-' * 78}")
            print(result.current_state)
            print(
                f"\n[timeline: {len(result.timeline)} entries | "
                f"major changes: {len(result.major_changes)} | "
                f"risk signals: {len(result.historical_risk_signals)} | "
                f"summary: {result.summary_source}"
                + (f" ({result.summary_model})" if result.summary_model else "")
                + "]"
            )
    finally:
        session.close()


if __name__ == "__main__":
    main()
