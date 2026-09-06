"""Review-report evidence retrieval service (Phase 7): the query-time half
of the pipeline (Vector DB -> Hybrid Retrieval -> Reranking -> Evidence),
plus LLM answer composition (app/services/rag/answer.py).

Serves: "What does the latest review report say about Project X?" - the
corpus is searched in full (older editions can be more specifically
relevant than the newest one), with a small deterministic recency tiebreak
so that, all else being close to equal, the latest edition's matching
content is preferred - never a hard filter that could discard better
evidence just because it is not the newest document.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, date, datetime

from sqlalchemy.orm import Session

from app.core.config import get_settings
from app.core.errors import NotFoundError
from app.models.project import Project
from app.services.rag.answer import AnswerResult, Citation, compose_answer
from app.services.rag.embeddings import EmbeddingUnavailableError, embed_query
from app.services.rag.retrieval import RankedChunk, hybrid_search

DEFAULT_QUESTION = "What does the latest review report say about this project?"
DEFAULT_TOP_K = 5
RECENCY_BOOST_WEIGHT = 0.005


@dataclass(frozen=True)
class EvidenceResult:
    project_id: str
    project_name: str
    question: str
    answer: str
    citations: list[Citation]
    summary_source: str
    summary_model: str | None
    evidence_found: bool
    searched_at: str


def _recency_boost(ranked: list[RankedChunk]) -> list[RankedChunk]:
    dated = [(item, item.chunk.document.edition_date) for item in ranked]
    known_dates = sorted({d for _, d in dated if d is not None}, reverse=True)
    rank_of: dict[date, int] = {d: i for i, d in enumerate(known_dates)}

    boosted = []
    for item, edition_date in dated:
        bonus = 0.0
        if edition_date is not None and known_dates:
            bonus = RECENCY_BOOST_WEIGHT * (len(known_dates) - rank_of[edition_date]) / len(known_dates)
        boosted.append(
            RankedChunk(
                chunk=item.chunk,
                score=item.score + bonus,
                matched_vector=item.matched_vector,
                matched_keyword=item.matched_keyword,
            )
        )
    boosted.sort(key=lambda r: r.score, reverse=True)
    return boosted


def search_review_evidence(
    session: Session,
    project_id: str,
    question: str = DEFAULT_QUESTION,
    top_k: int = DEFAULT_TOP_K,
) -> EvidenceResult:
    project = session.get(Project, project_id)
    if project is None:
        raise NotFoundError(f"project {project_id} not found")

    settings = get_settings()
    query_text = " ".join(
        filter(None, [question, project.project_name, project.agency, project.state])
    )

    try:
        query_embedding = embed_query(query_text, api_key=settings.gemini_api_key)
    except EmbeddingUnavailableError:
        query_embedding = None

    boost_terms = [t for t in [project.agency_code, project.state] if t]

    if query_embedding is not None:
        ranked = hybrid_search(
            session, query_text, query_embedding, fetch_k=20, top_k=top_k * 2, boost_terms=boost_terms
        )
    else:
        # No embedding available (no API key / call failed) - fall back to
        # keyword-only retrieval rather than returning nothing.
        from app.services.rag.retrieval import reciprocal_rank_fusion, rerank_with_keyword_boost
        from app.services.rag.vector_store import keyword_search

        keyword_results = keyword_search(session, query_text, 20)
        fused = reciprocal_rank_fusion([], keyword_results)
        ranked = rerank_with_keyword_boost(fused, boost_terms)[: top_k * 2]

    ranked = _recency_boost(ranked)[:top_k]

    answer: AnswerResult = compose_answer(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        question=question,
        project_name=project.project_name,
        ranked_chunks=ranked,
    )

    return EvidenceResult(
        project_id=project_id,
        project_name=project.project_name,
        question=question,
        answer=answer.text,
        citations=answer.citations,
        summary_source=answer.source,
        summary_model=answer.model,
        evidence_found=len(ranked) > 0,
        searched_at=datetime.now(UTC).isoformat(),
    )
