import json
from pathlib import Path

from fastapi.testclient import TestClient
from pypdf import PdfWriter

from research_copilot.page_store import save_page_data
from research_copilot.reading_history import ReadingHistoryStore
from research_copilot.web_app import create_app


PROJECT_ROOT = Path(__file__).resolve().parents[1]
TRUTH_PATH = (
    PROJECT_ROOT
    / "docs"
    / "evaluations"
    / "m8_3_multi_paper_evidence_truth.json"
)


def _blank_pdf(path: Path) -> None:
    writer = PdfWriter()
    writer.add_blank_page(width=300, height=400)
    with path.open("wb") as output:
        writer.write(output)


def _build_client(tmp_path: Path) -> tuple[TestClient, dict[str, str], dict[str, object]]:
    truth = json.loads(TRUTH_PATH.read_text(encoding="utf-8"))
    papers = tmp_path / "papers"
    papers.mkdir()
    processed = tmp_path / "processed"

    for fixture in truth["papers"].values():
        path = papers / fixture["filename"]
        if fixture["pages"] is None:
            path.write_bytes(b"not a pdf")
        else:
            _blank_pdf(path)

    client = TestClient(
        create_app(
            paper_directory=papers,
            processed_directory=processed,
            frontend_directory=tmp_path / "web",
            history_store=ReadingHistoryStore(tmp_path / "history"),
        )
    )
    ids_by_filename = {
        item["name"]: item["id"] for item in client.get("/api/papers").json()
    }
    aliases = {
        alias: ids_by_filename[fixture["filename"]]
        for alias, fixture in truth["papers"].items()
    }

    processed.mkdir()
    for alias, fixture in truth["papers"].items():
        if fixture["pages"] is None:
            continue
        save_page_data(
            {
                "source_pdf": fixture["filename"],
                "pages": [
                    {"source_page": number, "text": text}
                    for number, text in enumerate(fixture["pages"], start=1)
                ],
            },
            processed / f"{aliases[alias]}.json",
        )
    return client, aliases, truth


def test_fixed_multi_paper_evidence_truth_set(tmp_path: Path) -> None:
    client, aliases, truth = _build_client(tmp_path)
    expected_sources = 0
    found_sources = 0
    expected_pages = 0
    found_pages = 0
    status_total = 0
    status_correct = 0
    leaked_hits = 0

    for case in truth["cases"]:
        selected_ids = [aliases[alias] for alias in case["selected"]]
        response = client.post(
            "/api/research/evidence",
            json={
                "query": case["query"],
                "paper_ids": selected_ids,
                "per_paper_limit": 3,
            },
        )
        assert response.status_code == 200, case["id"]
        papers = response.json()["papers"]
        assert [paper["paper_id"] for paper in papers] == selected_ids

        actual_by_alias = {
            alias: next(paper for paper in papers if paper["paper_id"] == aliases[alias])
            for alias in case["selected"]
        }
        for alias in case["selected"]:
            actual = actual_by_alias[alias]
            expected_status = case["expected_status"][alias]
            status_total += 1
            status_correct += actual["status"] == expected_status
            if expected_status == "matched":
                expected_sources += 1
                found_sources += actual["status"] == "matched"

            actual_pages = {hit["source_page"] for hit in actual["hits"]}
            for expected_page in case["expected_pages"][alias]:
                expected_pages += 1
                found_pages += expected_page in actual_pages
            leaked_hits += sum(
                hit["paper_id"] not in selected_ids for hit in actual["hits"]
            )

    assert found_sources / expected_sources == 1.0
    assert found_pages / expected_pages == 1.0
    assert status_correct / status_total == 1.0
    assert leaked_hits == 0


def test_research_evidence_scope_validation(tmp_path: Path) -> None:
    client, aliases, _ = _build_client(tmp_path)

    one_paper = client.post(
        "/api/research/evidence",
        json={"query": "attention", "paper_ids": [aliases["alpha"]]},
    )
    assert one_paper.status_code == 422

    duplicate = client.post(
        "/api/research/evidence",
        json={
            "query": "attention",
            "paper_ids": [aliases["alpha"], aliases["alpha"]],
        },
    )
    assert duplicate.status_code == 422

    unknown = client.post(
        "/api/research/evidence",
        json={
            "query": "attention",
            "paper_ids": [aliases["alpha"], "missing"],
        },
    )
    assert unknown.status_code == 422


def test_per_paper_limit_preserves_other_sources(tmp_path: Path) -> None:
    client, aliases, _ = _build_client(tmp_path)
    response = client.post(
        "/api/research/evidence",
        json={
            "query": "attention",
            "paper_ids": [aliases["alpha"], aliases["beta"]],
            "per_paper_limit": 1,
        },
    )

    assert response.status_code == 200
    papers = response.json()["papers"]
    assert [paper["status"] for paper in papers] == ["matched", "matched"]
    assert [len(paper["hits"]) for paper in papers] == [1, 1]
