import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest
import torch

from research_copilot.real_multi_paper_evaluation import (
    _CachedEmbeddingModel,
    _choose_calibration_threshold,
    _is_short_term_query,
    _page_level_rrf,
    _score_gate_cases,
    _score_sufficiency_cases,
    _top_distinct_pages,
    check_papers,
    run,
    score_case,
    summarize,
)
from research_copilot.semantic_retriever import E5TokenAlignmentModel


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = (
    PROJECT_ROOT / "docs" / "evaluations" / "m8_4a_real_two_paper_truth.json"
)


def test_check_papers_requires_exact_files_and_hashes(tmp_path: Path) -> None:
    content = b"fixed local research sample"
    truth = {
        "papers": {
            "sample": {
                "filename": "sample.pdf",
                "sha256": hashlib.sha256(content).hexdigest(),
            }
        }
    }

    with pytest.raises(ValueError, match="缺少真实 PDF"):
        check_papers(truth, tmp_path)

    path = tmp_path / "sample.pdf"
    path.write_bytes(b"wrong")
    with pytest.raises(ValueError, match="PDF 版本或内容不符"):
        check_papers(truth, tmp_path)

    path.write_bytes(content)
    assert check_papers(truth, tmp_path) == {"sample": path}


def test_candidate_pages_are_unique_and_keep_rank_order() -> None:
    ranked = [
        {"source_page": 4},
        {"source_page": 4},
        {"source_page": 6},
        {"source_page": 2},
    ]
    assert _top_distinct_pages(ranked, 2) == [4, 6]


def test_page_level_rrf_can_recover_a_page_across_rankers() -> None:
    semantic = [
        {"source_page": 5},
        {"source_page": 6},
        {"source_page": 7},
        {"source_page": 9},
    ]
    hybrid = [
        {"source_page": 5},
        {"source_page": 9},
        {"source_page": 7},
        {"source_page": 6},
    ]

    assert _page_level_rrf(semantic, hybrid, 3) == [5, 6, 9]


def test_evidence_gate_distinguishes_short_terms_from_natural_questions() -> None:
    assert _is_short_term_query("masked language model")
    assert _is_short_term_query("quantum entanglement")
    assert not _is_short_term_query("How do the papers encode token positions?")
    assert not _is_short_term_query("两篇论文如何表示词的位置？")


def test_evidence_gate_uses_phrase_for_terms_and_cosine_for_questions() -> None:
    prepared = [
        {
            "truth": {
                "id": "gate",
                "query": "fixed",
                "relevant_pages": {"term": [], "question": [4]},
                "known_irrelevant_pages": {"term": [], "question": []},
            },
            "papers": {
                "term": {
                    "pages": [1],
                    "gate_kind": "exact_phrase",
                    "exact_phrase_match": False,
                    "max_semantic_similarity": 0.99,
                },
                "question": {
                    "pages": [4],
                    "gate_kind": "cosine",
                    "exact_phrase_match": False,
                    "max_semantic_similarity": 0.82,
                },
            },
        }
    ]

    scored = _score_gate_cases(prepared, threshold=0.81)[0]["papers"]

    assert scored["term"]["status"] == "no_match"
    assert scored["question"]["status"] == "matched"
    assert scored["question"]["anchor_found"] is True


def test_embedding_cache_reuses_identical_passages_and_queries() -> None:
    class FakeModel:
        def __init__(self) -> None:
            self.query_calls = 0
            self.passage_calls = 0

        def embed_query(self, query: str) -> list[float]:
            self.query_calls += 1
            return [float(len(query))]

        def embed_passages(self, passages: list[str]) -> list[list[float]]:
            self.passage_calls += 1
            return [[float(len(passage))] for passage in passages]

    fake = FakeModel()
    cached = _CachedEmbeddingModel(fake)
    assert cached.embed_query("位置") == cached.embed_query("位置")
    assert cached.embed_passages(["text"]) == cached.embed_passages(["text"])
    assert fake.query_calls == 1
    assert fake.passage_calls == 1


def test_token_alignment_scores_content_tokens_and_ignores_special_tokens() -> None:
    class FakeTokenizer:
        def __call__(self, texts: list[str], **_: object) -> dict[str, torch.Tensor]:
            rows = []
            for text in texts:
                content = 2 if "matching" in text or text.startswith("query:") else 3
                rows.append([9, content, 8, 0])
            count = len(rows)
            return {
                "input_ids": torch.tensor(rows),
                "attention_mask": torch.tensor([[1, 1, 1, 0]] * count),
                "special_tokens_mask": torch.tensor([[1, 0, 1, 1]] * count),
            }

    class FakeModel:
        def __call__(self, *, input_ids: torch.Tensor, **_: object) -> object:
            return SimpleNamespace(
                last_hidden_state=torch.nn.functional.one_hot(
                    input_ids, num_classes=10
                ).float()
            )

    scorer = object.__new__(E5TokenAlignmentModel)
    scorer._tokenizer = FakeTokenizer()
    scorer._model = FakeModel()
    scorer._max_length = 8
    scorer._device = torch.device("cpu")

    matching, unrelated = scorer.score_pairs(
        "question", ["matching evidence", "unrelated evidence"]
    )

    assert matching == pytest.approx(1.0)
    assert unrelated == pytest.approx(0.0)


def test_fine_grained_threshold_uses_only_calibration_split() -> None:
    prepared = [
        {
            "truth": {
                "id": "positive",
                "split": "calibration",
                "query": "q",
                "relevant_pages": {"paper": [2]},
                "known_irrelevant_pages": {"paper": []},
            },
            "papers": {
                "paper": {"pages": [2], "evidence_sufficiency_score": 0.8}
            },
        },
        {
            "truth": {
                "id": "negative",
                "split": "calibration",
                "query": "q",
                "relevant_pages": {"paper": []},
                "known_irrelevant_pages": {"paper": []},
            },
            "papers": {
                "paper": {"pages": [1], "evidence_sufficiency_score": 0.7}
            },
        },
        {
            "truth": {
                "id": "held-out",
                "split": "held_out",
                "query": "q",
                "relevant_pages": {"paper": []},
                "known_irrelevant_pages": {"paper": []},
            },
            "papers": {
                "paper": {"pages": [3], "evidence_sufficiency_score": 0.99}
            },
        },
    ]

    selected = _choose_calibration_threshold(prepared)
    scored = _score_sufficiency_cases(prepared, float(selected["threshold"]))

    assert selected == {
        "threshold": 0.8,
        "positive_floor": 0.8,
        "negative_ceiling": 0.7,
        "separable": True,
    }
    assert scored[0]["papers"]["paper"]["status"] == "matched"
    assert scored[1]["papers"]["paper"]["status"] == "no_match"
    assert scored[2]["papers"]["paper"]["status"] == "matched"


def test_scores_relevance_noise_no_match_and_scope_leakage() -> None:
    relevant = score_case(
        {
            "id": "relevant",
            "query": "learning rate",
            "relevant_pages": {"alpha": [7]},
            "known_irrelevant_pages": {"alpha": [2]},
        },
        {
            "alpha": {
                "paper_id": "alpha-id",
                "status": "matched",
                "hits": [
                    {"paper_id": "alpha-id", "source_page": 7},
                    {"paper_id": "other-id", "source_page": 2},
                ],
            }
        },
    )
    negative = score_case(
        {
            "id": "negative",
            "query": "missing topic",
            "relevant_pages": {"alpha": []},
            "known_irrelevant_pages": {"alpha": []},
        },
        {
            "alpha": {
                "paper_id": "alpha-id",
                "status": "no_match",
                "hits": [],
            }
        },
    )

    metrics = summarize([relevant, negative])

    assert metrics == {
        "expected_source_count": 1,
        "sources_found": 1,
        "source_coverage": 1.0,
        "anchor_pages_found": 1,
        "anchor_coverage": 1.0,
        "expected_no_match_count": 1,
        "correct_no_match_count": 1,
        "no_match_accuracy": 1.0,
        "known_irrelevant_hits": 1,
        "returned_hit_count": 2,
        "known_irrelevant_hit_rate": 0.5,
        "scope_leakage_hits": 1,
    }


def test_real_two_paper_baseline_when_local_samples_are_available() -> None:
    truth = json.loads(DEFAULT_TRUTH.read_text(encoding="utf-8"))
    paper_directory = PROJECT_ROOT / "data" / "raw"
    missing = [
        paper["filename"]
        for paper in truth["papers"].values()
        if not (paper_directory / paper["filename"]).is_file()
    ]
    if missing:
        pytest.skip(
            "Local real-paper benchmark files are not synchronized with Git: "
            + ", ".join(missing)
        )

    report = run(truth, paper_directory)

    assert report["metrics"] == {
        "expected_source_count": 9,
        "sources_found": 5,
        "source_coverage": pytest.approx(5 / 9),
        "anchor_pages_found": 5,
        "anchor_coverage": pytest.approx(5 / 9),
        "expected_no_match_count": 3,
        "correct_no_match_count": 3,
        "no_match_accuracy": 1.0,
        "known_irrelevant_hits": 3,
        "returned_hit_count": 15,
        "known_irrelevant_hit_rate": 0.2,
        "scope_leakage_hits": 0,
    }
