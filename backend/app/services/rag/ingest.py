"""Ingestion orchestration: PDF -> ... -> Vector DB (Phase 7, the full left
half of the pipeline diagram, stages 1-6)."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from sqlalchemy.orm import Session

from app.models.project import Project
from app.services.rag.chunking import chunk_pages
from app.services.rag.embeddings import embed_texts
from app.services.rag.extraction import extract_pdf_pages
from app.services.rag.metadata import detect_project_id, detect_sector, parse_edition_date
from app.services.rag.vector_store import replace_chunks, upsert_document


@dataclass(frozen=True)
class IngestSummary:
    document_id: str
    document_name: str
    page_count: int
    chunk_count: int
    ocr_pages: int
    empty_pages: int


def _document_id_for(filename: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", filename.lower()).strip("-")
    return f"review-{slug}"[:64]


def build_project_lookup(session: Session) -> dict[str, str]:
    """Maps lowercased project name / agency code / state to project_id, for
    the (rare, honestly-reported-when-absent) case a chunk does name one."""
    lookup: dict[str, str] = {}
    for project in session.query(Project).all():
        if project.project_name:
            lookup[project.project_name.lower()] = project.project_id
        if project.agency_code:
            lookup[project.agency_code.lower()] = project.project_id
    return lookup


def ingest_pdf(session: Session, path: Path, *, api_key: str | None) -> IngestSummary:
    pages = extract_pdf_pages(path)
    chunks = chunk_pages(pages)

    if not chunks:
        document_id = _document_id_for(path.name)
        upsert_document(
            session,
            document_id=document_id,
            document_name=path.stem,
            source_file=path.name,
            edition_date=parse_edition_date(path.name),
            page_count=len(pages),
        )
        replace_chunks(session, document_id, [], [], {}, [], [])
        return IngestSummary(document_id, path.stem, len(pages), 0, 0, len(pages))

    document_id = _document_id_for(path.name)
    document_name = path.stem
    edition_date = parse_edition_date(path.name)

    project_lookup = build_project_lookup(session)
    sectors = [detect_sector(c.text) for c in chunks]
    project_ids = [detect_project_id(c.text, project_lookup) for c in chunks]

    embeddings = embed_texts([c.text for c in chunks], api_key=api_key, task_type="RETRIEVAL_DOCUMENT")

    extraction_methods = {p.page: p.method for p in pages}
    ocr_pages = sum(1 for p in pages if p.method == "OCR")
    empty_pages = sum(1 for p in pages if p.method == "EMPTY")

    upsert_document(
        session,
        document_id=document_id,
        document_name=document_name,
        source_file=path.name,
        edition_date=edition_date,
        page_count=len(pages),
    )
    chunk_count = replace_chunks(session, document_id, chunks, embeddings, extraction_methods, sectors, project_ids)

    return IngestSummary(document_id, document_name, len(pages), chunk_count, ocr_pages, empty_pages)


def ingest_directory(
    session: Session, directory: Path, *, api_key: str | None, pattern: str = "*.pdf"
) -> list[IngestSummary]:
    """Commits after each document, so a later document's failure (e.g. a
    rate limit that outlasts the retry budget) does not discard already-
    ingested documents - safe to simply re-run to pick up where it left off."""
    summaries = []
    for path in sorted(directory.glob(pattern)):
        summary = ingest_pdf(session, path, api_key=api_key)
        session.commit()
        summaries.append(summary)
    return summaries
