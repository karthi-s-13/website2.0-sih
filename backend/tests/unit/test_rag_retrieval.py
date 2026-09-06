from types import SimpleNamespace

from app.services.rag.retrieval import reciprocal_rank_fusion, rerank_with_keyword_boost


def make_chunk(id_, text="some text"):
    return SimpleNamespace(id=id_, text=text)


def test_rrf_ranks_items_in_both_lists_highest() -> None:
    a, b, c = make_chunk(1), make_chunk(2), make_chunk(3)
    # b is #1 in both lists; a is #1 in vector only; c is #1 in keyword only.
    vector_results = [(b, 0.1), (a, 0.2)]
    keyword_results = [(b, 5), (c, 3)]

    ranked = reciprocal_rank_fusion(vector_results, keyword_results)
    ids = [r.chunk.id for r in ranked]

    # b, appearing top-ranked in both lists, must outrank items in only one list.
    assert ids[0] == 2
    assert ranked[0].matched_vector is True
    assert ranked[0].matched_keyword is True


def test_rrf_includes_items_from_only_one_list() -> None:
    a, b = make_chunk(1), make_chunk(2)
    ranked = reciprocal_rank_fusion([(a, 0.1)], [(b, 1)])
    ids = {r.chunk.id for r in ranked}
    assert ids == {1, 2}


def test_rrf_empty_inputs_returns_empty() -> None:
    assert reciprocal_rank_fusion([], []) == []


def test_rrf_scores_are_descending() -> None:
    chunks = [make_chunk(i) for i in range(5)]
    vector_results = [(c, float(i)) for i, c in enumerate(chunks)]
    ranked = reciprocal_rank_fusion(vector_results, [])
    scores = [r.score for r in ranked]
    assert scores == sorted(scores, reverse=True)


def test_rerank_boosts_chunks_with_exact_term_match() -> None:
    a = make_chunk(1, text="This chunk mentions POWERGRID directly in the text.")
    b = make_chunk(2, text="This chunk is unrelated to any agency.")
    # give both chunks explicit equal scores to isolate the boost effect
    from app.services.rag.retrieval import RankedChunk

    equal_ranked = [
        RankedChunk(chunk=a, score=0.5, matched_vector=True, matched_keyword=False),
        RankedChunk(chunk=b, score=0.5, matched_vector=True, matched_keyword=False),
    ]
    boosted = rerank_with_keyword_boost(equal_ranked, ["POWERGRID"])
    assert boosted[0].chunk.id == 1
    assert boosted[0].score > boosted[1].score


def test_rerank_no_boost_terms_is_noop() -> None:
    a = make_chunk(1)
    from app.services.rag.retrieval import RankedChunk

    ranked = [RankedChunk(chunk=a, score=0.5, matched_vector=True, matched_keyword=False)]
    result = rerank_with_keyword_boost(ranked, [])
    assert result == ranked
