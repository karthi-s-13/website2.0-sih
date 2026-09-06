#!/usr/bin/env python
"""Phase 1 CLI: profile + ingest the raw Flash Report CSVs and seed the
validation cohort.

Usage (from repo root, with the backend venv active):

    python scripts/ingest_flash_reports.py

Writes a data profile to data/validation/, ingests data/raw/flash_reports/*.csv
into the configured database (see backend/app/core/config.py / .env), and
seeds the validation_cohort table.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.ingestion.pipeline import ingest_directory  # noqa: E402
from app.services.ingestion.profiling import profile_directory, render_markdown  # noqa: E402
from app.services.validation_cohort import seed_validation_cohort  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)

RAW_DIR = REPO_ROOT / "data" / "raw" / "flash_reports"
VALIDATION_DIR = REPO_ROOT / "data" / "validation"


def main() -> None:
    configure_logging()
    log = get_logger("ingest_flash_reports")

    VALIDATION_DIR.mkdir(parents=True, exist_ok=True)
    report = profile_directory(RAW_DIR)
    (VALIDATION_DIR / "profile_report.json").write_text(json.dumps(report, indent=2))
    (VALIDATION_DIR / "profile_report.md").write_text(render_markdown(report))
    log.info("profiled_raw_data", files=report["file_count"], out=str(VALIDATION_DIR))

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summary = ingest_directory(session, RAW_DIR)
        cohort_inserted = seed_validation_cohort(session)
    finally:
        session.close()

    log.info(
        "ingestion_complete",
        files_processed=summary.files_processed,
        raw_rows_seen=summary.raw_rows_seen,
        raw_rows_newly_stored=summary.raw_rows_newly_stored,
        projects_upserted=summary.projects_upserted,
        observations_upserted=summary.observations_upserted,
        observations_quarantined=summary.observations_quarantined,
        events_created=summary.events_created,
        issues_by_severity=summary.issues_by_severity,
        validation_cohort_seeded=cohort_inserted,
    )


if __name__ == "__main__":
    main()
