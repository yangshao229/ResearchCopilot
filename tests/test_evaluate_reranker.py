import pytest

from research_copilot.reranker_evaluation import (
    evidence_requirement_coverage,
    evaluate_case,
    rerank_candidates,
    summarize,
)


class FakePairScorer:
    def __init__(self, scores):
        self.scores = scores

    def predict(self, pairs, *, batch_size, show_progress_bar):
        assert pairs == [("question", "first"), ("question", "second")]
        assert batch_size == 8
        assert show_progress_bar is False
        return self.scores


def test_rerank_candidates_preserves_original_hits_and_uses_pair_scores():
    candidates = [
        {"source_page": 1, "chunk_index": 0, "text": "first", "score": 0.2},
        {"source_page": 4, "chunk_index": 0, "text": "second", "score": 0.1},
    ]

    ranked = rerank_candidates("question", candidates, FakePairScorer([1.0, 3.0]))

    assert [hit["source_page"] for hit in ranked] == [4, 1]
    assert ranked[0]["cross_encoder_score"] == 3.0
    assert "cross_encoder_score" not in candidates[0]


@pytest.mark.parametrize("scores", [[1.0], [1.0, float("nan")]])
def test_rerank_candidates_rejects_invalid_scores(scores):
    candidates = [
        {"source_page": 1, "chunk_index": 0, "text": "first", "score": 0.2},
        {"source_page": 4, "chunk_index": 0, "text": "second", "score": 0.1},
    ]

    with pytest.raises(ValueError):
        rerank_candidates("question", candidates, FakePairScorer(scores))


def test_summary_counts_gain_and_regression_separately():
    cases = [
        {
            "id": "gain", "kind": "answerable", "language": "zh",
            "anchor_in_candidates": True,
            "baseline_anchor_at_5": False, "reranked_anchor_at_5": True,
            "baseline_known_irrelevant_at_5": 1,
            "reranked_known_irrelevant_at_5": 0,
        },
        {
            "id": "regression", "kind": "answerable", "language": "en",
            "anchor_in_candidates": True,
            "baseline_anchor_at_5": True, "reranked_anchor_at_5": False,
            "baseline_known_irrelevant_at_5": 0,
            "reranked_known_irrelevant_at_5": 1,
        },
        {
            "id": "negative", "kind": "no_answer", "top_cross_encoder_score": -3.0,
            "baseline_known_irrelevant_at_5": 0,
            "reranked_known_irrelevant_at_5": 0,
        },
    ]

    report = summarize(cases)

    assert report["gains"] == 1
    assert report["regressions"] == 1
    assert report["baseline_anchor_at_5"] == report["reranked_anchor_at_5"] == 1
    assert report["no_answer_abstention_supported"] is False
    assert report["by_language"]["zh"]["reranked_anchor_at_5"] == 1
    assert report["answer_bearing_evidence"]["cases"] == 0
    assert report["top_score_separation"] == {
        "positive_min": None,
        "negative_max": -3.0,
        "single_threshold_separates": None,
    }


@pytest.mark.parametrize(
    ("positive_scores", "negative_scores", "separates"),
    [([2.0, 4.0], [-1.0, 1.0], True), ([0.5, 4.0], [-1.0, 0.8], False)],
)
def test_summary_reports_top_score_separation_without_claiming_abstention(
    positive_scores, negative_scores, separates
):
    cases = [
        {
            "id": f"positive-{index}", "kind": "answerable", "language": "en",
            "anchor_in_candidates": True,
            "baseline_anchor_at_5": True, "reranked_anchor_at_5": True,
            "baseline_known_irrelevant_at_5": 0,
            "reranked_known_irrelevant_at_5": 0,
            "top_cross_encoder_score": score,
        }
        for index, score in enumerate(positive_scores)
    ] + [
        {
            "id": f"negative-{index}", "kind": "no_answer",
            "baseline_known_irrelevant_at_5": 0,
            "reranked_known_irrelevant_at_5": 0,
            "top_cross_encoder_score": score,
        }
        for index, score in enumerate(negative_scores)
    ]

    report = summarize(cases)

    assert report["top_score_separation"] == {
        "positive_min": min(positive_scores),
        "negative_max": max(negative_scores),
        "single_threshold_separates": separates,
    }
    assert report["no_answer_abstention_supported"] is False


def test_distinct_page_shadow_exposes_duplicate_page_crowding():
    pages = [8, 8, 10, 8, 2, 7, 1]
    candidates = [
        {"source_page": page, "chunk_index": index, "text": f"chunk {index}", "score": 1.0}
        for index, page in enumerate(pages)
    ]
    class DescendingScorer:
        def predict(self, pairs, *, batch_size, show_progress_bar):
            return list(range(len(pairs), 0, -1))

    result = evaluate_case(
        {"id": "hardware", "paper": "transformer", "language": "en",
         "query": "training hardware", "anchor_pages": [7],
         "known_irrelevant_pages": []},
        [],
        object(),
        DescendingScorer(),
        candidate_search=lambda *args, **kwargs: candidates,
    )

    assert result["reranked_pages_at_5"] == [8, 8, 10, 8, 2]
    assert result["distinct_pages_at_5"] == [8, 10, 2, 7, 1]
    assert result["reranked_anchor_at_5"] is False
    assert result["distinct_anchor_at_5"] is True


def test_evidence_coverage_requires_every_group_across_the_evidence_set():
    hits = [
        {"source_page": 2, "text": "A pre-trained seq2seq Transformer."},
        {"source_page": 2, "text": "A dense vector index of Wikipedia."},
    ]
    requirements = [
        ["pre-trained seq2seq transformer"],
        ["dense vector index", "document store"],
    ]

    assert evidence_requirement_coverage(hits, requirements, 1) == {
        "matched_groups": 1, "total_groups": 2, "complete": False,
    }
    assert evidence_requirement_coverage(hits, requirements, 2) == {
        "matched_groups": 2, "total_groups": 2, "complete": True,
    }
    assert evidence_requirement_coverage(hits, None, 2) is None


def test_evidence_coverage_can_require_all_facts_on_one_pdf_page():
    hits = [
        {"source_page": 2, "text": "first required fact"},
        {"source_page": 4, "text": "second required fact"},
    ]
    requirements = [["first required fact"], ["second required fact"]]

    assert evidence_requirement_coverage(hits, requirements, 2)["complete"] is True
    coherent = evidence_requirement_coverage(
        hits, requirements, 2, require_one_page=True
    )
    assert coherent == {
        "matched_groups": 1, "total_groups": 2, "complete": False,
    }


def test_page_hit_does_not_imply_answer_bearing_evidence():
    candidates = [
        {"source_page": 4, "chunk_index": 0, "text": "Experiments begin here.",
         "score": 1.0},
        {"source_page": 4, "chunk_index": 1,
         "text": "Fast decoding avoids additional forward passes.", "score": 0.5},
    ]

    class OrderedScorer:
        def predict(self, pairs, *, batch_size, show_progress_bar):
            return [2.0, 1.0]

    result = evaluate_case(
        {"id": "decoding", "paper": "rag", "language": "en",
         "query": "question", "anchor_pages": [4],
         "known_irrelevant_pages": [],
         "evidence_requirements": [["additional forward pass"],
                                   ["sum probabilities across beams"]]},
        [], object(), OrderedScorer(),
        candidate_search=lambda *args, **kwargs: candidates,
    )

    assert result["baseline_anchor_at_5"] is True
    assert result["baseline_evidence_coverage_at_5"]["complete"] is False
    assert result["baseline_evidence_coverage_at_5"]["matched_groups"] == 1
