"""Run a bounded, resumable local audit of real paper answers.

The output stays in the Git-ignored artifacts directory. It never writes a
reading record or Obsidian note. An in-progress entry is not retried on resume:
the remote call might have been billed before an interruption.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from research_copilot.domain import Evidence, LanguagePolicy
from research_copilot.paper_answer_service import DeepSeekAnswerModel, ModelAnswerDraft, PaperAnswerService
from research_copilot.paper_identity import PaperIdentityStore, hash_pdf
from research_copilot.paper_library import PaperLibrary
from research_copilot.paper_search_service import PaperSearchService


ROOT = Path(__file__).resolve().parents[1]
SELECTION_PATH = ROOT / "docs/evaluations/m8_4r_answer_audit_selection.json"
DEFAULT_OUTPUT = ROOT / "artifacts/m8_4r_answer_audit.json"


class CapturingModel:
    provider_name = "deepseek"

    def __init__(self) -> None:
        self.delegate = DeepSeekAnswerModel(post=self._post)
        self.model_name = self.delegate.model_name
        self.draft: ModelAnswerDraft | None = None
        self.usage: dict[str, Any] | None = None
        self.called = False

    def _post(self, *args: Any, **kwargs: Any) -> Any:
        self.called = True
        response = DeepSeekAnswerModel._default_post(*args, **kwargs)
        usage = response.json().get("usage")
        self.usage = usage if isinstance(usage, dict) else None
        return response

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
        language: LanguagePolicy | None = None,
        task: str = "question",
        task_context: str = "",
        glossary_terms: list[Any] | None = None,
    ) -> ModelAnswerDraft:
        self.draft = self.delegate.generate(
            question, evidence, language, task, task_context, glossary_terms
        )
        return self.draft


def load_selection() -> tuple[dict[str, Any], list[tuple[dict[str, Any], dict[str, Any]]]]:
    selection = json.loads(SELECTION_PATH.read_text(encoding="utf-8"))
    cases: list[tuple[dict[str, Any], dict[str, Any]]] = []
    seen: set[str] = set()
    for item in selection["datasets"]:
        dataset_path = (ROOT / item["path"]).resolve()
        if not dataset_path.is_relative_to(ROOT / "docs/evaluations"):
            raise ValueError("Selection references a file outside the frozen evaluation ledger.")
        dataset = json.loads(dataset_path.read_text(encoding="utf-8"))
        indexed = {case["id"]: case for case in dataset["cases"]}
        for case_id in item["case_ids"]:
            if case_id in seen or case_id not in indexed:
                raise ValueError(f"Duplicate or unknown case ID: {case_id}")
            seen.add(case_id)
            cases.append((indexed[case_id], dataset["papers"][indexed[case_id]["paper"]]))
    return selection, cases


def save_audit(path: Path, audit: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    if temporary.exists():
        raise FileExistsError(f"Unresolved temporary audit file: {temporary}")
    with temporary.open("x", encoding="utf-8") as stream:
        temporary.chmod(0o600)
        json.dump(audit, stream, ensure_ascii=False, indent=2)
        stream.write("\n")
    temporary.replace(path)


def run(max_new_calls: int, output: Path) -> None:
    if max_new_calls < 1 or max_new_calls > 8:
        raise ValueError("--max-new-calls must be between 1 and 8.")
    if output.exists() and output.is_symlink():
        raise ValueError("Refusing a symlink output path.")

    selection, cases = load_selection()
    selection_sha256 = hashlib.sha256(SELECTION_PATH.read_bytes()).hexdigest()
    paper_directory = ROOT / "data/raw"
    library = PaperLibrary(
        paper_directory,
        PaperIdentityStore(ROOT / "data/.research_copilot/paper_identities"),
    )
    papers_by_name = {paper.name: paper for paper in library.list_papers()}
    for _, paper_truth in cases:
        paper = papers_by_name.get(paper_truth["filename"])
        if paper is None or hash_pdf(library.get_paper_path(paper.id)) != paper_truth["sha256"]:
            raise ValueError(f"PDF missing or changed: {paper_truth['filename']}")

    if output.exists():
        audit = json.loads(output.read_text(encoding="utf-8"))
        if audit.get("selection_sha256") != selection_sha256:
            raise ValueError("Frozen case selection changed; refusing to append to the old audit.")
    else:
        audit = {
            "selection_id": selection["selection_id"],
            "selection_sha256": selection_sha256,
            "search_mode": selection["search_mode"],
            "evidence_limit": selection["evidence_limit"],
            "cases": {},
        }

    load_dotenv(ROOT / ".env")
    search = PaperSearchService(ROOT / "data/processed")
    new_calls = 0
    for case, paper_truth in cases:
        if case["id"] in audit["cases"]:
            continue
        if new_calls >= max_new_calls:
            break
        paper = papers_by_name[paper_truth["filename"]]
        pdf_path = library.get_paper_path(paper.id)
        source_document = library.source_document(paper.id)
        model = CapturingModel()
        service = PaperAnswerService(search, model)
        evidence_set = service.collect_evidence(
            pdf_path, paper.id, case["query"], selection["search_mode"],
            limit=selection["evidence_limit"], source_document=source_document,
        )
        record: dict[str, Any] = {
            "status": "in_progress",
            "paper": paper_truth["filename"],
            "pdf_sha256": paper_truth["sha256"],
            "question": case["query"],
            "answerable_in_pdf": bool(case["anchor_pages"]),
            "anchor_pages": case["anchor_pages"],
            "model": model.model_name,
            "evidence_set": evidence_set.model_dump(mode="json"),
        }
        audit["cases"][case["id"]] = record
        save_audit(output, audit)
        print(f"{case['id']}: evidence={len(evidence_set.candidates)}, request starting", flush=True)
        try:
            answer = service.answer(
                pdf_path, paper.id, case["query"], selection["search_mode"],
                limit=selection["evidence_limit"],
                language=LanguagePolicy(), source_document=source_document,
                evidence_set=evidence_set,
            )
        except Exception as error:
            record.update(status="error", error_type=type(error).__name__, error=str(error))
        else:
            record.update(
                status="completed",
                model_draft=model.draft.model_dump(mode="json") if model.draft else None,
                answer=answer.model_dump(mode="json"),
                usage=model.usage,
                api_called=model.called,
            )
        save_audit(output, audit)
        new_calls += int(model.called)
        print(f"{case['id']}: {record['status']}, api_called={model.called}", flush=True)
        if record["status"] != "completed":
            break
    print(f"New API calls: {new_calls}; audit: {output}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--max-new-calls", type=int, required=True)
    arguments = parser.parse_args()
    run(arguments.max_new_calls, DEFAULT_OUTPUT)
