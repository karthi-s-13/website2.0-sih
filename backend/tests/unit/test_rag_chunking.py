from app.services.rag.chunking import chunk_pages
from app.services.rag.extraction import PageText


def test_chunks_never_cross_page_boundaries() -> None:
    pages = [
        PageText(page=1, text="First page content here.", method="TEXT"),
        PageText(page=2, text="Second page content here.", method="TEXT"),
    ]
    chunks = chunk_pages(pages)
    assert len(chunks) == 2
    assert chunks[0].page == 1
    assert chunks[1].page == 2
    assert "First" in chunks[0].text
    assert "Second" in chunks[1].text


def test_empty_pages_produce_no_chunks() -> None:
    pages = [PageText(page=1, text="", method="EMPTY"), PageText(page=2, text="real content here", method="TEXT")]
    chunks = chunk_pages(pages)
    assert len(chunks) == 1
    assert chunks[0].page == 2


def test_short_page_is_a_single_chunk() -> None:
    pages = [PageText(page=1, text="Short paragraph.", method="TEXT")]
    chunks = chunk_pages(pages)
    assert len(chunks) == 1
    assert chunks[0].chunk_index == 0


def test_long_page_is_split_into_multiple_chunks() -> None:
    paragraph = "This is a sentence that repeats. " * 20  # ~680 chars
    long_text = "\n\n".join([paragraph] * 5)  # ~3400 chars
    pages = [PageText(page=1, text=long_text, method="TEXT")]
    chunks = chunk_pages(pages, max_chars=1000, overlap_chars=100)
    assert len(chunks) > 1
    assert all(c.page == 1 for c in chunks)
    # chunk_index must be unique and sequential
    assert [c.chunk_index for c in chunks] == list(range(len(chunks)))


def test_chunk_index_is_unique_across_pages() -> None:
    pages = [
        PageText(page=1, text="Page one content that is reasonably long for a chunk test case.", method="TEXT"),
        PageText(page=2, text="Page two content that is reasonably long for a chunk test case.", method="TEXT"),
        PageText(page=3, text="Page three content that is reasonably long for a chunk test case.", method="TEXT"),
    ]
    chunks = chunk_pages(pages)
    indexes = [c.chunk_index for c in chunks]
    assert indexes == sorted(set(indexes))  # unique and ascending


def test_char_count_matches_text_length() -> None:
    pages = [PageText(page=1, text="Exactly this text.", method="TEXT")]
    chunks = chunk_pages(pages)
    assert chunks[0].char_count == len(chunks[0].text)
