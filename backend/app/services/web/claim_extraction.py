"""Claim extraction + project-relevance scoring (spec section 20's "Claim
Extraction" and "Project Relevance" stages), mirroring the guardrail shape
of `history/llm.py` and `rag/answer.py`: one bounded LLM call per
topic-query batch, grounded only in the search results actually returned -
never inventing a finding, a date, or a relevance score not backed by the
fetched content.

Graceful degradation: no API key, a failed call, or an output that isn't
valid JSON grounded in the given URLs falls back to a deterministic
extraction (truncated snippet + keyword-overlap relevance).
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass

from app.services.web.search_client import SearchResult

SYSTEM_INSTRUCTION = """You extract a single factual finding from each web search result about an \
infrastructure project, for an infrastructure project monitoring platform. Use ONLY the title and \
content given for each result - never invent facts, numbers, or dates not present in it.

For every result, in the same order given, output one JSON object with:
  - "finding": one plain sentence stating what the source says (or "No specific project-relevant \
claim found in this source." if the content does not actually concern the project).
  - "project_relevance": a number from 0.0 to 1.0 for how clearly this source concerns the named \
project specifically (not just its sector or region in general).

Return ONLY a JSON array of these objects, one per result, same order, no other text.
"""

_WORD_RE = re.compile(r"[a-z0-9]+")


@dataclass(frozen=True)
class ExtractedClaim:
    result: SearchResult
    finding: str
    project_relevance: float


def _tokens(text: str) -> set[str]:
    return set(_WORD_RE.findall(text.lower()))


def _keyword_relevance(result: SearchResult, project_name: str, agency: str | None, state: str | None) -> float:
    haystack = _tokens(f"{result.title} {result.content}")
    keywords = _tokens(project_name) | _tokens(agency or "") | _tokens(state or "")
    keywords = {k for k in keywords if len(k) > 3}  # drop short/common tokens
    if not keywords:
        return 0.0
    matched = keywords & haystack
    return round(min(len(matched) / len(keywords), 1.0), 4)


def _deterministic_claims(
    results: list[SearchResult], project_name: str, agency: str | None, state: str | None
) -> list[ExtractedClaim]:
    claims = []
    for result in results:
        snippet = result.content.strip()[:280] or result.title
        claims.append(
            ExtractedClaim(
                result=result,
                finding=snippet,
                project_relevance=_keyword_relevance(result, project_name, agency, state),
            )
        )
    return claims


def _format_results(results: list[SearchResult]) -> str:
    lines = []
    for i, r in enumerate(results):
        lines.append(f"[{i}] URL: {r.url}\nTitle: {r.title}\nContent: {r.content[:1500]}\n")
    return "\n".join(lines)


def extract_claims(
    *,
    api_key: str | None,
    model: str,
    project_name: str,
    agency: str | None,
    state: str | None,
    topic: str,
    results: list[SearchResult],
) -> list[ExtractedClaim]:
    fallback = _deterministic_claims(results, project_name, agency, state)
    if not api_key or not results:
        return fallback

    try:
        from app.services.llm.groq_client import generate_text

        prompt = (
            f"Project: {project_name}\nSearch topic: {topic}\n\nResults:\n{_format_results(results)}"
        )
        text = generate_text(
            api_key=api_key, model=model, system_instruction=SYSTEM_INSTRUCTION, contents=prompt, temperature=0.1
        )
        text = re.sub(r"^```(json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
        parsed = json.loads(text)
    except Exception:  # noqa: BLE001 - any failure must degrade gracefully, never raise
        return fallback

    if not isinstance(parsed, list) or len(parsed) != len(results):
        return fallback

    claims = []
    for result, item in zip(results, parsed, strict=True):
        if not isinstance(item, dict):
            return fallback
        finding = str(item.get("finding") or "").strip()
        try:
            relevance = float(item.get("project_relevance"))
        except (TypeError, ValueError):
            return fallback
        if not finding or not 0.0 <= relevance <= 1.0:
            return fallback
        claims.append(ExtractedClaim(result=result, finding=finding, project_relevance=relevance))

    return claims
