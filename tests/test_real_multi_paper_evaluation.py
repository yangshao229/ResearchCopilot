import hashlib
import json
from pathlib import Path

import pytest

from research_copilot.real_multi_paper_evaluation import (
    check_papers,
    run,
    score_case,
    summarize,
)


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
