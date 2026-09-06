#!/usr/bin/env python
"""Phase 8 CLI: run the Web Intelligence Agent for each of the 5 validation
cohort projects (run ingest_flash_reports.py first).

Without a real TAVILY_API_KEY configured, this still runs end-to-end - the
trigger gate and query planner execute normally, but every search request
reports itself as unavailable (never fabricated evidence), matching the
graceful-degradation rule (PRD section 65).

Usage (from repo root, with the backend venv active):

    python scripts/ask_web_evidence.py
    python scripts/ask_web_evidence.py --force
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.models.project import Project  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402
from app.services.web.service import get_web_intelligence  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--force", action="store_true", help="Force a search even if risk is not high")
    args = parser.parse_args()

    configure_logging()
    log = get_logger("ask_web_evidence")

    Base.metadata.create_all(bind=engine)

    settings = get_settings()
    if not settings.tavily_api_key:
        print(
            "TAVILY_API_KEY is not set - web search will be reported as unavailable for any "
            "triggered project. Set TAVILY_API_KEY in .env to get live evidence.\n"
        )

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = get_web_intelligence(session, project_id, force=args.force)

            print(f"\n{'=' * 78}")
            print(f"{result.project_name}  ({result.project_id})")
            print(f"Triggered: {result.triggered} - {result.trigger_reason}")
            if not result.triggered:
                continue
            print(f"Topics searched: {', '.join(result.topics_searched) or '(none)'}")
            print(f"{'-' * 78}")
            if result.warnings:
                for w in result.warnings:
                    print(f"  [warning] {w}")
            if not result.evidence:
                print("  No evidence found.")
            for item in result.evidence:
                print(f"  - [{item.source_quality}] {item.source} ({item.publication_date or 'undated'})")
                print(f"    {item.finding}")
                print(f"    relevance={item.project_relevance:.2f}  {item.url}")
    finally:
        session.close()


if __name__ == "__main__":
    main()
