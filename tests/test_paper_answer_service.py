from pathlib import Path

import pytest

from research_copilot.paper_answer_service import (
    AnswerGenerationError,
    DeepSeekAnswerModel,
    Evidence,
    ModelAnswerDraft,
    ModelNotConfiguredError,
    PaperAnswerService,
)
from research_copilot.domain import LanguagePolicy


class FakeSearchService:
    def __init__(self, results: list[dict[str, int | float | str]]) -> None:
        self.results = results

    def search(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        mode: str,
        limit: int = 5,
    ) -> list[dict[str, int | float | str]]:
        return self.results[:limit]


class FakeAnswerModel:
    provider_name = "fake"
    model_name = "fake-paper-model"

    def __init__(self, draft: ModelAnswerDraft) -> None:
        self.draft = draft
        self.received_evidence: list[Evidence] = []
        self.received_language: LanguagePolicy | None = None
        self.received_task = "question"
        self.received_task_context = ""

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
        language: LanguagePolicy | None = None,
        task="question",
        task_context="",
    ) -> ModelAnswerDraft:
        self.received_evidence = evidence
        self.received_language = language
        self.received_task = task
        self.received_task_context = task_context
        return self.draft


def test_answer_maps_model_evidence_ids_to_real_pdf_pages() -> None:
    search_service = FakeSearchService(
        [
            {
                "source_page": 4,
                "chunk_index": 1,
                "text": "Multi-head attention runs attention heads in parallel.",
                "score": 0.92,
            },
            {
                "source_page": 5,
                "chunk_index": 2,
                "text": "The outputs are concatenated and projected.",
                "score": 0.88,
            },
        ]
    )
    model = FakeAnswerModel(
        ModelAnswerDraft(
            answer="多头注意力会并行运行多个注意力头。",
            explanation="不同注意力头的结果会拼接并再次投影。",
            cited_evidence_ids=[1, 2, 1],
            insufficient_evidence=False,
            uncertainty="证据只覆盖论文中的简要定义。",
        )
    )
    service = PaperAnswerService(search_service, model)

    answer = service.answer(
        Path("paper.pdf"),
        "paper-id",
        "什么是多头注意力？",
        "semantic",
    )

    assert [citation.source_page for citation in answer.citations] == [4, 5]
    assert [citation.evidence_id for citation in answer.citations] == [1, 2]
    assert model.received_evidence[0].evidence_id == 1
    assert answer.insufficient_evidence is False


def test_answer_passes_language_policy_to_model() -> None:
    model = FakeAnswerModel(
        ModelAnswerDraft(
            answer="Answer",
            explanation="Explanation",
            cited_evidence_ids=[1],
            insufficient_evidence=False,
            uncertainty="",
        )
    )
    service = PaperAnswerService(
        FakeSearchService(
            [{"source_page": 1, "chunk_index": 0, "text": "evidence", "score": 1.0}]
        ),
        model,
    )
    policy = LanguagePolicy(explanation_language="en")

    answer = service.answer(
        Path("paper.pdf"), "paper-id", "Question", "keyword", language=policy
    )

    assert answer.language == policy
    assert model.received_language == policy


def test_translation_uses_only_direct_selection_evidence_and_context() -> None:
    model = FakeAnswerModel(
        ModelAnswerDraft(
            answer="翻译结果",
            explanation="术语按偏好保留。",
            cited_evidence_ids=[1],
            insufficient_evidence=False,
            uncertainty="",
        )
    )
    search_service = FakeSearchService(
        [{"source_page": 9, "chunk_index": 3, "text": "RAG hit", "score": 0.9}]
    )
    service = PaperAnswerService(search_service, model)
    selected = {
        "source_page": 2,
        "chunk_index": 0,
        "text": "The selected sentence.",
        "score": 1.0,
    }

    answer = service.answer(
        Path("paper.pdf"),
        "paper-id",
        "Translate selected text",
        "hybrid",
        task="translate",
        direct_evidence=[selected],
        task_context="A sentence before. The selected sentence. A sentence after.",
        language=LanguagePolicy(translation_target="en"),
    )

    assert [item.text for item in model.received_evidence] == [
        "The selected sentence."
    ]
    assert model.received_task == "translate"
    assert "A sentence before." in model.received_task_context
    assert answer.citations[0].source_page == 2


def test_answer_fails_closed_when_model_cites_unknown_evidence() -> None:
    search_service = FakeSearchService(
        [
            {
                "source_page": 2,
                "chunk_index": 0,
                "text": "Transformer removes recurrence.",
                "score": 0.9,
            }
        ]
    )
    model = FakeAnswerModel(
        ModelAnswerDraft(
            answer="一个未经证据支持的结论。",
            explanation="无。",
            cited_evidence_ids=[99],
            insufficient_evidence=False,
            uncertainty="无。",
        )
    )
    service = PaperAnswerService(search_service, model)

    answer = service.answer(
        Path("paper.pdf"),
        "paper-id",
        "问题",
        "semantic",
    )

    assert answer.insufficient_evidence is True
    assert answer.citations == []
    assert "引用校验" in answer.uncertainty


def test_answer_skips_model_when_retrieval_finds_no_evidence() -> None:
    model = FakeAnswerModel(
        ModelAnswerDraft(
            answer="不应调用",
            explanation="不应调用",
            cited_evidence_ids=[],
            insufficient_evidence=False,
            uncertainty="",
        )
    )
    service = PaperAnswerService(FakeSearchService([]), model)

    answer = service.answer(
        Path("paper.pdf"),
        "paper-id",
        "不存在的问题",
        "keyword",
    )

    assert answer.insufficient_evidence is True
    assert model.received_evidence == []


class FakeHttpResponse:
    def __init__(self, output_text: str) -> None:
        self.status_code = 200
        self.output_text = output_text

    def json(self) -> dict[str, object]:
        return {
            "output": [
                {
                    "type": "message",
                    "content": [
                        {"type": "output_text", "text": self.output_text}
                    ],
                }
            ]
        }


class FakePost:
    def __init__(self, output_text: str) -> None:
        self.output_text = output_text
        self.url = ""
        self.request: dict[str, object] | None = None

    def __call__(self, url: str, **kwargs: object) -> FakeHttpResponse:
        self.url = url
        self.request = kwargs
        return FakeHttpResponse(self.output_text)


def test_deepseek_model_requests_structured_json() -> None:
    post = FakePost(
        ModelAnswerDraft(
            answer="回答",
            explanation="解释",
            cited_evidence_ids=[1],
            insufficient_evidence=False,
            uncertainty="无",
        ).model_dump_json()
    )
    model = DeepSeekAnswerModel(
        api_key="test-key",
        model_name="deepseek-flash",
        post=post,
    )

    result = model.generate(
        "问题",
        [
            Evidence(
                evidence_id=1,
                source_page=3,
                chunk_index=0,
                text="论文证据",
                score=0.8,
            )
        ],
        LanguagePolicy(explanation_language="en"),
    )

    assert result.cited_evidence_ids == [1]
    assert post.request is not None
    request_body = post.request["json"]
    assert isinstance(request_body, dict)
    text_config = request_body["text"]
    assert isinstance(text_config, dict)
    assert text_config["format"]["type"] == "json_schema"  # type: ignore[index]
    assert "PDF 第 3 页" in str(request_body["input"])
    assert "English" in str(request_body["input"])
    assert post.url == "https://api.deepseek.com/responses"


def test_deepseek_model_requires_api_key(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("DEEPSEEK_API_KEY", raising=False)
    model = DeepSeekAnswerModel(api_key=None, post=None)

    with pytest.raises(ModelNotConfiguredError):
        model.generate("问题", [])


def test_deepseek_model_rejects_invalid_json() -> None:
    model = DeepSeekAnswerModel(
        api_key="test-key",
        post=FakePost("not-json"),
    )

    with pytest.raises(AnswerGenerationError):
        model.generate("问题", [])
