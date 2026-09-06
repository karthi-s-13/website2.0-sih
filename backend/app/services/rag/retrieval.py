"""Hybrid retrieval + reranking (Phase 7 pipeline stages 7-8).

Hybrid retrieval combines two independent signals via Reciprocal Rank Fusion
(RRF) - semantic similarity (vector_search) and lexical overlap
(keyword_search) - rather than relying on embeddings alone. This matters for
this corpus specifically: a query like "POWERGRID" or a project code is
exactly the kind of short, specific token that keyword search nails and
embedding similarity can dilute.

Reranking is a deterministic keyword-boost pass over the fused results, not
a second LLM call - it is fast, free, and reproducible, consistent with
keeping every non-synthesis stage of this pipeline deterministic (LLM only
ever touches final answer composition, in service.py).
"""

from __future__ import annotations

from dataclasses import dataclass

from sqlalchemy.orm import Session

from app.models.document import DocumentChunk
from app.services.rag.vector_store import keyword_search, vector_search

RRF_K = 60  # standard Reciprocal Rank Fusion constant


@dataclass(frozen=True)
class RankedChunk:
    chunk: DocumentChunk
    score: float
    matched_vector: bool
    matched_keyword: bool


def reciprocal_rank_fusion(
    vector_results: list[tuple[DocumentChunk, float]],
    keyword_results: list[tuple[DocumentChunk, int]],
    k: int = RRF_K,
) -> list[RankedChunk]:
    scores: dict[int, float] = {}
    chunks: dict[int, DocumentChunk] = {}
    matched_vector: set[int] = set()
    matched_keyword: set[int] = set()

    for rank, (chunk, _distance) in enumerate(vector_results, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunks[chunk.id] = chunk
        matched_vector.add(chunk.id)

    for rank, (chunk, _count) in enumerate(keyword_results, start=1):
        scores[chunk.id] = scores.get(chunk.id, 0.0) + 1.0 / (k + rank)
        chunks[chunk.id] = chunk
        matched_keyword.add(chunk.id)

    ranked = [
        RankedChunk(
            chunk=chunks[cid],
            score=score,
            matched_vector=cid in matched_vector,
            matched_keyword=cid in matched_keyword,
        )
        for cid, score in scores.items()
    ]
    ranked.sort(key=lambda r: r.score, reverse=True)
    return ranked


def rerank_with_keyword_boost(
    ranked: list[RankedChunk], boost_terms: list[str], boost_weight: float = 0.02
) -> list[RankedChunk]:
    """Deterministic rerank: chunks containing an exact boost term (e.g. the
    project's agency code or state) move up, proportional to how many
    distinct boost terms they contain."""
    lowered_terms = [t.lower() for t in boost_terms if t and len(t) > 2]
    if not lowered_terms:
        return ranked

    boosted = []
    for item in ranked:
        text_lower = item.chunk.text.lower()
        hits = sum(1 for term in lowered_terms if term in text_lower)
        boosted.append(
            RankedChunk(
                chunk=item.chunk,
                score=item.score + hits * boost_weight,
                matched_vector=item.matched_vector,
                matched_keyword=item.matched_keyword,
            )
        )
    boosted.sort(key=lambda r: r.score, reverse=True)
    return boosted


def hybrid_search(
    session: Session,
    query_text: str,
    query_embedding: list[float],
    top_k: int,
    boost_terms: list[str] | None = None,
    project_id: str | None = None,
    fetch_k: int = 20,
) -> list[RankedChunk]:
    vector_results = vector_search(session, query_embedding, fetch_k, project_id=project_id)
    keyword_results = keyword_search(session, query_text, fetch_k, project_id=project_id)

    fused = reciprocal_rank_fusion(vector_results, keyword_results)
    reranked = rerank_with_keyword_boost(fused, boost_terms or [])
    return reranked[:top_k]
