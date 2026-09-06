"""Thin Groq chat-completions call, used by every LLM-touched agent
(Project History narrative, RAG answer composition, Web claim extraction,
Coordinator intent classification, Reporting executive summary).

Groq exposes an OpenAI-compatible REST API, so this is a plain HTTP call via
`httpx` (already a dependency) rather than a new SDK - one shared place for
the request/response shape so switching providers again later only means
editing this one file, not five call sites.

Raises on any failure (no key, network error, non-2xx, malformed response) -
every caller already wraps its own call in `except Exception: <deterministic
fallback>`, matching the guardrail pattern every one of these agents already
uses for Gemini failures (no key, quota exhausted, bad output).
"""

from __future__ import annotations

import httpx

GROQ_CHAT_COMPLETIONS_URL = "https://api.groq.com/openai/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 30.0


def generate_text(
    *,
    api_key: str,
    model: str,
    system_instruction: str,
    contents: str,
    temperature: float = 0.2,
) -> str:
    response = httpx.post(
        GROQ_CHAT_COMPLETIONS_URL,
        headers={"Authorization": f"Bearer {api_key}"},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": contents},
            ],
            "temperature": temperature,
        },
        timeout=REQUEST_TIMEOUT_SECONDS,
    )
    response.raise_for_status()
    data = response.json()
    return (data["choices"][0]["message"]["content"] or "").strip()
