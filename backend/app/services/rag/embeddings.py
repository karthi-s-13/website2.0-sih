"""Embedding generation (Phase 7 pipeline stage 5), via the Gemini embeddings
API (the same provider/key as Phase 6 - no separate credential needed).

Uses asymmetric retrieval task types (RETRIEVAL_DOCUMENT at ingestion time,
RETRIEVAL_QUERY at search time), which meaningfully improves retrieval
quality over embedding both sides the same way.

Rate-limit handling: the free-tier embeddings quota is easy to exceed with a
multi-document ingestion batch. 429/RESOURCE_EXHAUSTED responses are retried
with exponential backoff (this is a batch job run by an operator, not a
live request path, so waiting is the right tradeoff); every other error
propagates immediately. Query-time embedding (embed_query, on the live
search path) still fails fast overall since the retry ceiling is bounded -
callers there already fall back to keyword-only search on failure (see
app/services/rag/service.py).
"""

from __future__ import annotations

import time

from app.models.document import EMBEDDING_DIM

EMBEDDING_MODEL = "gemini-embedding-001"
BATCH_SIZE = 16
INTER_BATCH_DELAY_SECONDS = 2.0
MAX_RETRIES = 5
INITIAL_BACKOFF_SECONDS = 20.0
MAX_BACKOFF_SECONDS = 120.0


class EmbeddingUnavailableError(RuntimeError):
    pass


def _client(api_key: str | None):
    if not api_key:
        raise EmbeddingUnavailableError(
            "GEMINI_API_KEY is not configured - embeddings require the Gemini API "
            "(no local embedding model is bundled)."
        )
    from google import genai

    return genai.Client(api_key=api_key)


def _is_rate_limit_error(exc: Exception) -> bool:
    text = str(exc)
    return "429" in text or "RESOURCE_EXHAUSTED" in text


def _embed_batch_with_retry(client, batch: list[str], task_type: str):
    backoff = INITIAL_BACKOFF_SECONDS
    last_exc: Exception | None = None

    for attempt in range(1, MAX_RETRIES + 1):
        try:
            return client.models.embed_content(
                model=EMBEDDING_MODEL,
                contents=batch,
                config={"task_type": task_type, "output_dimensionality": EMBEDDING_DIM},
            )
        except Exception as exc:  # noqa: BLE001
            last_exc = exc
            if not _is_rate_limit_error(exc) or attempt == MAX_RETRIES:
                raise EmbeddingUnavailableError(f"embedding request failed: {exc}") from exc
            time.sleep(min(backoff, MAX_BACKOFF_SECONDS))
            backoff *= 2

    raise EmbeddingUnavailableError(f"embedding request failed: {last_exc}")


def embed_texts(texts: list[str], *, api_key: str | None, task_type: str) -> list[list[float]]:
    """task_type: "RETRIEVAL_DOCUMENT" for chunks being indexed, "RETRIEVAL_QUERY"
    for a search query."""
    if not texts:
        return []

    client = _client(api_key)
    vectors: list[list[float]] = []

    for start in range(0, len(texts), BATCH_SIZE):
        batch = texts[start : start + BATCH_SIZE]
        response = _embed_batch_with_retry(client, batch, task_type)
        vectors.extend(list(e.values) for e in response.embeddings)
        if start + BATCH_SIZE < len(texts):
            time.sleep(INTER_BATCH_DELAY_SECONDS)

    return vectors


def embed_query(text: str, *, api_key: str | None) -> list[float]:
    return embed_texts([text], api_key=api_key, task_type="RETRIEVAL_QUERY")[0]
