#!/usr/bin/env python
"""Phase 2 CLI: build the point-in-time feature store for all ingested
projects (run scripts/ingest_flash_reports.py first).

Usage (from repo root, with the backend venv active):

    python scripts/build_features.py
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.features.pipeline import FEATURE_VERSION, build_features  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    configure_logging()
    log = get_logger("build_features")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summary = build_features(session)
    finally:
        session.close()

    log.info(
        "feature_build_complete",
        feature_version=FEATURE_VERSION,
        projects_processed=summary.projects_processed,
        feature_rows_upserted=summary.feature_rows_upserted,
    )


if __name__ == "__main__":
    main()
