from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol

from pydantic import BaseModel, ConfigDict, Field, ValidationError

from research_copilot.paper_search_service import (
    SearchMode,
    SearchResult,
)

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"


class ModelNotConfiguredError(RuntimeError):
    pass


class AnswerGenerationError(RuntimeError):
    pass


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    source_page: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    text: str
    score: float
    keyword_rank: int = 0
    keyword_score: float = 0.0
    semantic_rank: int = 0
    semantic_score: float = 0.0
    fusion_score: float = 0.0
    reference_penalty: float = 0.0
    rerank_score: float = 0.0


class ModelAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    explanation: str
    cited_evidence_ids: list[int]
    insufficient_evidence: bool
    uncertainty: str


class AnswerCitation(BaseModel):
    evidence_id: int
    source_page: int
    quote: str


class PaperAnswer(BaseModel):
    answer: str
    explanation: str
    citations: list[AnswerCitation]
    insufficient_evidence: bool
    uncertainty: str
    evidence: list[Evidence]
    provider: str
    model: str


class AnswerModel(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> ModelAnswerDraft: ...


class SearchService(Protocol):
    def search(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        mode: SearchMode,
        limit: int = 5,
    ) -> list[SearchResult]: ...


class DeepSeekAnswerModel:
    provider_name = "deepseek"

    def __init__(
        self,
        api_key: str | None = None,
        model_name: str | None = None,
        base_url: str | None = None,
        post: Any | None = None,
    ) -> None:
        self._api_key = api_key
        self.model_name = (
            model_name
            or os.getenv("DEEPSEEK_MODEL")
            or DEFAULT_DEEPSEEK_MODEL
        )
        self._base_url = (
            base_url
            or os.getenv("DEEPSEEK_BASE_URL")
            or DEFAULT_DEEPSEEK_BASE_URL
        )
        self._post = post

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
    ) -> ModelAnswerDraft:
        api_key = self._get_api_key()

        try:
            post = self._post or self._default_post
            response = post(
                f"{self._base_url.rstrip('/')}/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model_name,
                    "instructions": self._instructions(),
                    "input": self._build_input(question, evidence),
                    "max_output_tokens": 1600,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "paper_answer",
                            "schema": ModelAnswerDraft.model_json_schema(),
                        }
                    },
                },
                timeout=120,
            )
            response_body = response.json()
            if response.status_code >= 400:
                error_data = response_body.get("error", {})
                error_message = (
                    error_data.get("message")
                    if isinstance(error_data, dict)
                    else None
                )
                raise AnswerGenerationError(
                    f"DeepSeek API returned {response.status_code}: "
                    f"{error_message or 'unknown error'}"
                )

            output_text = self._extract_output_text(response_body)
            if not output_text:
                raise AnswerGenerationError("DeepSeek returned an empty answer.")
            return ModelAnswerDraft.model_validate_json(output_text)
        except ModelNotConfiguredError:
            raise
        except AnswerGenerationError:
            raise
        except ValidationError as error:
            raise AnswerGenerationError(
                "DeepSeek returned an invalid structured answer."
            ) from error
        except Exception as error:
            raise AnswerGenerationError(
                "DeepSeek request failed. Check the API key, balance, and network."
            ) from error

    def _get_api_key(self) -> str:
        api_key = self._api_key or os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ModelNotConfiguredError(
                "DEEPSEEK_API_KEY is not configured."
            )

        return api_key

    @staticmethod
    def _default_post(*args: Any, **kwargs: Any) -> Any:
        from curl_cffi import requests

        return requests.post(*args, **kwargs)

    @staticmethod
    def _extract_output_text(response_body: dict[str, Any]) -> str:
        direct_text = response_body.get("output_text")
        if isinstance(direct_text, str):
            return direct_text

        for item in response_body.get("output", []):
            if not isinstance(item, dict) or item.get("type") != "message":
                continue
            for content in item.get("content", []):
                if (
                    isinstance(content, dict)
                    and content.get("type") == "output_text"
                    and isinstance(content.get("text"), str)
                ):
                    return content["text"]
        return ""

    @staticmethod
    def _instructions() -> str:
        return (
            "你是科研论文阅读助手。只能根据用户提供的论文证据回答，"
            "不得使用证据之外的论文细节。区分直接结论、解释和不确定性。"
            "引用只能填写证据中存在的 evidence_id。证据不足时必须将 "
            "insufficient_evidence 设为 true，并明确说明缺少什么。"
            "输出必须是符合给定 JSON Schema 的 JSON。"
        )

    @staticmethod
    def _build_input(question: str, evidence: list[Evidence]) -> str:
        evidence_text = "\n\n".join(
            (
                f"[E{item.evidence_id} | PDF 第 {item.source_page} 页]\n"
                f"{item.text}"
            )
            for item in evidence
        )
        return (
            f"问题：{question}\n\n"
            "以下是从当前论文中检索到的全部可用证据：\n\n"
            f"{evidence_text}\n\n"
            "请用中文回答，并在 cited_evidence_ids 中列出实际支持回答的证据编号。"
        )


class PaperAnswerService:
    def __init__(
        self,
        search_service: SearchService,
        answer_model: AnswerModel | None = None,
    ) -> None:
        self.search_service = search_service
        self.answer_model = answer_model or DeepSeekAnswerModel()

    def answer(
        self,
        pdf_path: Path,
        paper_id: str,
        question: str,
        mode: SearchMode,
        limit: int = 5,
    ) -> PaperAnswer:
        raw_evidence = self.search_service.search(
            pdf_path,
            paper_id,
            question,
            mode,
            limit=limit,
        )
        evidence = [
            Evidence(
                evidence_id=index,
                source_page=int(item["source_page"]),
                chunk_index=int(item["chunk_index"]),
                text=str(item["text"]),
                score=float(item["score"]),
                keyword_rank=int(item.get("keyword_rank", 0)),
                keyword_score=float(item.get("keyword_score", 0.0)),
                semantic_rank=int(item.get("semantic_rank", 0)),
                semantic_score=float(item.get("semantic_score", 0.0)),
                fusion_score=float(item.get("fusion_score", 0.0)),
                reference_penalty=float(item.get("reference_penalty", 0.0)),
                rerank_score=float(item.get("rerank_score", 0.0)),
            )
            for index, item in enumerate(raw_evidence, start=1)
        ]

        if not evidence:
            return PaperAnswer(
                answer="当前论文中没有检索到足以回答该问题的原文证据。",
                explanation="请换一种问法，或切换关键词与语义检索后重试。",
                citations=[],
                insufficient_evidence=True,
                uncertainty="没有可供模型核对的论文片段。",
                evidence=[],
                provider=self.answer_model.provider_name,
                model=self.answer_model.model_name,
            )

        draft = self.answer_model.generate(question, evidence)
        evidence_by_id = {item.evidence_id: item for item in evidence}
        valid_ids = list(
            dict.fromkeys(
                evidence_id
                for evidence_id in draft.cited_evidence_ids
                if evidence_id in evidence_by_id
            )
        )
        citations = [
            AnswerCitation(
                evidence_id=evidence_id,
                source_page=evidence_by_id[evidence_id].source_page,
                quote=evidence_by_id[evidence_id].text,
            )
            for evidence_id in valid_ids
        ]

        missing_valid_citation = not citations and not draft.insufficient_evidence
        if missing_valid_citation:
            return PaperAnswer(
                answer="现有回答没有通过原文引用校验，因此没有展示模型结论。",
                explanation="模型未引用任何真实检索证据。请重新检索或换一种问法。",
                citations=[],
                insufficient_evidence=True,
                uncertainty="引用校验失败。",
                evidence=evidence,
                provider=self.answer_model.provider_name,
                model=self.answer_model.model_name,
            )

        return PaperAnswer(
            answer=draft.answer,
            explanation=draft.explanation,
            citations=citations,
            insufficient_evidence=draft.insufficient_evidence,
            uncertainty=draft.uncertainty,
            evidence=evidence,
            provider=self.answer_model.provider_name,
            model=self.answer_model.model_name,
        )
