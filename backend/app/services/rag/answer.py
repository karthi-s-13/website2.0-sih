"""LLM answer composition for review-report evidence (Phase 7, mirrors the
Phase 6 pattern exactly): the LLM's only job is to write a short answer
grounded in the chunks retrieval already found - it never sees the whole
report, never invents a citation, and must say so plainly when the evidence
is only general/sector-level rather than naming the project directly - these
are national sector bulletins, not project-level write-ups, so that case is
the common one, not the exception.

Graceful degradation matches Phase 6: no API key, a failed call, or an
output that cites nothing at all falls back to a deterministic, still
citation-bearing answer built directly from the retrieved chunks - this
alone satisfies the exit criterion (document + page references present)
even with the LLM unavailable.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.retrieval import RankedChunk

SYSTEM_INSTRUCTION = """You answer questions about official Review Reports for an infrastructure \
project monitoring platform, using ONLY the excerpts provided below - never invent facts, page \
numbers, or document names not present in them.

The review reports are NATIONAL sector-aggregate bulletins (Power, Coal, Steel, Cement, \
Fertilizers, Petroleum, Roads, Railways, Shipping & Ports, Civil Aviation, Telecommunications) - \
they rarely name an individual project directly. Rules:
  - Cite every claim with its document name and page number, e.g. (CompleteReviewReportAugust2025.pdf, p.6).
  - If none of the excerpts mention the project by name, say so explicitly and describe only what \
general sector-level context is present - never imply a direct connection that isn't there.
  - If the excerpts are irrelevant to the question, say clearly that no relevant evidence was found.
  - 2-4 sentences, neutral factual tone.
"""


@dataclass(frozen=True)
class Citation:
    document_name: str
    page: int
    excerpt: str
    score: float


@dataclass(frozen=True)
class AnswerResult:
    text: str
    source: str  # "LLM" | "DETERMINISTIC_FALLBACK"
    model: str | None
    citations: list[Citation]


def _citations_from(ranked: list[RankedChunk]) -> list[Citation]:
    return [
        Citation(
            document_name=item.chunk.document.document_name,
            page=item.chunk.page,
            excerpt=item.chunk.text[:400],
            score=round(item.score, 4),
        )
        for item in ranked
    ]


def _deterministic_answer(question: str, citations: list[Citation]) -> str:
    if not citations:
        return (
            f'No retrieved evidence was found for "{question}" in the indexed review reports.'
        )
    lines = [f'No LLM synthesis available. Most relevant excerpts for "{question}":']
    for c in citations:
        lines.append(f"- ({c.document_name}, p.{c.page}): {c.excerpt.strip()[:200]}")
    return "\n".join(lines)


def _format_context(question: str, project_name: str | None, ranked: list[RankedChunk]) -> str:
    lines = [f"Question: {question}"]
    if project_name:
        lines.append(f"Project: {project_name}")
    lines.append("")
    lines.append("Retrieved excerpts:")
    for item in ranked:
        lines.append(
            f"[{item.chunk.document.document_name}, p.{item.chunk.page}] {item.chunk.text}"
        )
        lines.append("")
    return "\n".join(lines)


def _has_any_citation(text: str, citations: list[Citation]) -> bool:
    lowered = text.lower()
    if "no relevant evidence" in lowered or "does not mention" in lowered or "not mentioned" in lowered:
        return True
    return any(f"p.{c.page}" in text or c.document_name.lower() in lowered for c in citations)


def compose_answer(
    *,
    api_key: str | None,
    model: str,
    question: str,
    project_name: str | None,
    ranked_chunks: list[RankedChunk],
) -> AnswerResult:
    citations = _citations_from(ranked_chunks)
    fallback_text = _deterministic_answer(question, citations)

    if not api_key or not ranked_chunks:
        return AnswerResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None, citations=citations)

    try:
        from app.services.llm.groq_client import generate_text

        context = _format_context(question, project_name, ranked_chunks)
        text = generate_text(
            api_key=api_key, model=model, system_instruction=SYSTEM_INSTRUCTION, contents=context, temperature=0.1
        )
    except Exception:  # noqa: BLE001 - must degrade gracefully, never raise
        return AnswerResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None, citations=citations)

    if not text or not _has_any_citation(text, citations):
        return AnswerResult(text=fallback_text, source="DETERMINISTIC_FALLBACK", model=None, citations=citations)

    return AnswerResult(text=text, source="LLM", model=model, citations=citations)
