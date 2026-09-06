"""Page-aware chunking (Phase 7 pipeline stage 3).

Chunks never cross a page boundary - every chunk carries exactly one page
number, which is what lets retrieved evidence cite a specific page (the
exit criterion). Long pages are split on paragraph boundaries with a small
character overlap so a sentence isn't severed mid-thought at a chunk edge;
short pages become a single chunk.
"""

from __future__ import annotations

from dataclasses import dataclass

from app.services.rag.extraction import PageText

DEFAULT_MAX_CHARS = 1200
DEFAULT_OVERLAP_CHARS = 150
MIN_CHUNK_CHARS = 10


@dataclass(frozen=True)
class Chunk:
    page: int
    chunk_index: int  # 0-based, unique within the document
    text: str
    char_count: int


def _split_paragraphs(text: str) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n\n")]
    return [p for p in paragraphs if p]


def _pack_paragraphs(paragraphs: list[str], max_chars: int, overlap_chars: int) -> list[str]:
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        candidate = f"{current}\n\n{para}" if current else para
        if len(candidate) <= max_chars or not current:
            current = candidate
        else:
            chunks.append(current)
            tail = current[-overlap_chars:] if overlap_chars else ""
            current = f"{tail}\n\n{para}" if tail else para

        # A single paragraph longer than max_chars must still be split.
        while len(current) > max_chars * 1.5:
            chunks.append(current[:max_chars])
            current = current[max_chars - overlap_chars :]

    if current.strip():
        chunks.append(current)

    return chunks


def chunk_pages(
    pages: list[PageText],
    max_chars: int = DEFAULT_MAX_CHARS,
    overlap_chars: int = DEFAULT_OVERLAP_CHARS,
) -> list[Chunk]:
    chunks: list[Chunk] = []
    index = 0

    for page in pages:
        if page.method == "EMPTY" or len(page.text.strip()) < MIN_CHUNK_CHARS:
            continue

        paragraphs = _split_paragraphs(page.text) or [page.text.strip()]
        for piece in _pack_paragraphs(paragraphs, max_chars, overlap_chars):
            piece = piece.strip()
            if len(piece) < MIN_CHUNK_CHARS:
                continue
            chunks.append(Chunk(page=page.page, chunk_index=index, text=piece, char_count=len(piece)))
            index += 1

    return chunks
