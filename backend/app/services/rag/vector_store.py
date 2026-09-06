"""pgvector-backed storage and similarity search (Phase 7 pipeline stage 6:
"Vector DB"). Reuses the existing project Postgres database (pgvector
extension) rather than standing up a separate vector database service - the
corpus here (a handful of PDFs, low hundreds of pages) has no need for a
dedicated ANN index; exact cosine-distance search via pgvector's `<=>`
operator is fast enough and simpler to reason about.
"""

from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.document import Document, DocumentChunk
from app.services.rag.chunking import Chunk


def upsert_document(
    session: Session,
    *,
    document_id: str,
    document_name: str,
    source_file: str,
    edition_date,
    page_count: int,
) -> Document:
    doc = session.get(Document, document_id)
    if doc is None:
        doc = Document(
            document_id=document_id,
            document_name=document_name,
            source_file=source_file,
            page_count=page_count,
        )
        session.add(doc)
    doc.document_name = document_name
    doc.source_file = source_file
    doc.edition_date = edition_date
    doc.page_count = page_count
    return doc


def replace_chunks(
    session: Session,
    document_id: str,
    chunks: list[Chunk],
    embeddings: list[list[float]],
    extraction_methods: dict[int, str],
    sectors: list[str | None],
    project_ids: list[str | None],
) -> int:
    """Deletes any existing chunks for this document and inserts the given
    set fresh - simpler and safer than trying to diff/upsert page-aware
    chunks whose boundaries can change if chunking parameters change."""
    session.query(DocumentChunk).filter_by(document_id=document_id).delete()

    for chunk, embedding, sector, project_id in zip(chunks, embeddings, sectors, project_ids, strict=True):
        session.add(
            DocumentChunk(
                document_id=document_id,
                chunk_index=chunk.chunk_index,
                page=chunk.page,
                text=chunk.text,
                char_count=chunk.char_count,
                extraction_method=extraction_methods.get(chunk.page, "TEXT"),
                sector=sector,
                project_id=project_id,
                embedding=embedding,
            )
        )

    return len(chunks)


def vector_search(
    session: Session, query_embedding: list[float], top_k: int, project_id: str | None = None
) -> list[tuple[DocumentChunk, float]]:
    """Returns [(chunk, cosine_distance), ...] ascending by distance (closer
    = more similar). `project_id`, when given, restricts to chunks that were
    matched to that specific project (see metadata.detect_project_id) -
    callers should fall back to an unrestricted search if this returns
    nothing, since most chunks in these national reports have no project
    match at all.
    """
    distance = DocumentChunk.embedding.cosine_distance(query_embedding)
    stmt = select(DocumentChunk, distance.label("distance")).where(DocumentChunk.embedding.is_not(None))
    if project_id is not None:
        stmt = stmt.where(DocumentChunk.project_id == project_id)
    stmt = stmt.order_by(distance).limit(top_k)
    return [(row[0], row[1]) for row in session.execute(stmt).all()]


def keyword_search(
    session: Session, query_text: str, top_k: int, project_id: str | None = None
) -> list[tuple[DocumentChunk, int]]:
    """Simple term-overlap keyword search (ILIKE-based) as the second leg of
    hybrid retrieval - deliberately not full pg full-text search, so it
    behaves predictably on short/ad-hoc queries (project names, agency
    codes) without needing tsvector/tsquery configuration."""
    terms = [t for t in query_text.lower().split() if len(t) > 2]
    if not terms:
        return []

    chunks_query = session.query(DocumentChunk)
    if project_id is not None:
        chunks_query = chunks_query.filter(DocumentChunk.project_id == project_id)
    candidates = chunks_query.all()

    scored = []
    for chunk in candidates:
        lowered = chunk.text.lower()
        score = sum(1 for term in terms if term in lowered)
        if score > 0:
            scored.append((chunk, score))

    scored.sort(key=lambda pair: pair[1], reverse=True)
    return scored[:top_k]
