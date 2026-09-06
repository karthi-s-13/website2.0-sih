#!/usr/bin/env python
"""Phase 7 CLI: ingest the review-report PDFs into the RAG pipeline
(extraction -> chunking -> metadata -> embeddings -> pgvector).

Usage (from repo root, with the backend venv active):

    python scripts/ingest_review_reports.py

Requires GEMINI_API_KEY (embeddings have no local fallback) and a reachable
Postgres with the pgvector extension (Phase 7 migration applied).
"""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BACKEND_DIR = REPO_ROOT / "backend"
sys.path.insert(0, str(BACKEND_DIR))

from app.core.config import get_settings  # noqa: E402
from app.core.db import Base, SessionLocal, engine  # noqa: E402
from app.core.logging import configure_logging, get_logger  # noqa: E402
from app.services.rag.ingest import ingest_directory  # noqa: E402

import app.models  # noqa: E402, F401  (registers models on Base.metadata)

RAW_DIR = REPO_ROOT / "data" / "raw" / "review_reports"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    configure_logging()
    log = get_logger("ingest_review_reports")

    settings = get_settings()
    if not settings.gemini_api_key:
        log.error("gemini_api_key_missing", message="Embeddings require GEMINI_API_KEY in .env")
        sys.exit(1)

    Base.metadata.create_all(bind=engine)

    session = SessionLocal()
    try:
        summaries = ingest_directory(session, RAW_DIR, api_key=settings.gemini_api_key)
    finally:
        session.close()

    total_chunks = 0
    for s in summaries:
        total_chunks += s.chunk_count
        log.info(
            "document_ingested",
            document_id=s.document_id,
            document_name=s.document_name,
            page_count=s.page_count,
            chunk_count=s.chunk_count,
            ocr_pages=s.ocr_pages,
            empty_pages=s.empty_pages,
        )

    log.info("ingestion_complete", documents=len(summaries), total_chunks=total_chunks)


if __name__ == "__main__":
    main()
