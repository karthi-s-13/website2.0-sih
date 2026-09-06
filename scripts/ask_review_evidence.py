#!/usr/bin/env python
"""Phase 7 CLI: ask "What does the latest review report say about Project X?"
for each of the 5 validation cohort projects (run ingest_review_reports.py first).

Usage (from repo root, with the backend venv active):

    python scripts/ask_review_evidence.py
    python scripts/ask_review_evidence.py --question "Any mention of land acquisition delays?"
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
from app.services.rag.service import DEFAULT_QUESTION, search_review_evidence  # noqa: E402
from app.services.validation_cohort import INITIAL_VALIDATION_COHORT  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--question", default=DEFAULT_QUESTION)
    args = parser.parse_args()

    configure_logging()
    log = get_logger("ask_review_evidence")

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        for project_id in INITIAL_VALIDATION_COHORT:
            project = session.get(Project, project_id)
            if project is None:
                log.warning("project_not_ingested", project_id=project_id)
                continue

            result = search_review_evidence(session, project_id, question=args.question)

            print(f"\n{'=' * 78}")
            print(f"{result.project_name}  ({result.project_id})")
            print(f"Q: {result.question}")
            print(f"{'-' * 78}")
            print(result.answer)
            print()
            if result.citations:
                print("Citations:")
                for c in result.citations:
                    print(f"  - {c.document_name}, p.{c.page} (score {c.score:.4f})")
            else:
                print("Citations: none")
            print(f"[evidence_found={result.evidence_found} | summary: {result.summary_source}" + (f" ({result.summary_model})" if result.summary_model else "") + "]")
    finally:
        session.close()


if __name__ == "__main__":
    main()
