"""Read-side repository for review-report documents/chunks (Phase 7's
`rag/vector_store.py` only ever wrote these; Phase 12's Document MCP needs
page/metadata lookups that never existed before)."""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk


def get_document(session: Session, document_id: str) -> Document | None:
    return session.get(Document, document_id)


def list_chunks(session: Session, document_id: str) -> list[DocumentChunk]:
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(session.execute(stmt).scalars().all())


def get_chunks_by_page(session: Session, document_id: str, page: int) -> list[DocumentChunk]:
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id, DocumentChunk.page == page)
        .order_by(DocumentChunk.chunk_index)
    )
    return list(session.execute(stmt).scalars().all())


def get_chunks_by_indexes(session: Session, document_id: str, chunk_indexes: list[int]) -> list[DocumentChunk]:
    stmt = (
        select(DocumentChunk)
        .where(DocumentChunk.document_id == document_id, DocumentChunk.chunk_index.in_(chunk_indexes))
        .order_by(DocumentChunk.chunk_index)
    )
    return list(session.execute(stmt).scalars().all())


def count_chunks(session: Session, document_id: str) -> int:
    return len(list_chunks(session, document_id))
