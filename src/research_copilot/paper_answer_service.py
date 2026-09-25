from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Mapping, Protocol

from pydantic import BaseModel, ConfigDict, ValidationError

from research_copilot.domain import (
    AnswerCitation,
    Evidence,
    LanguagePolicy,
    PaperAnswer,
    ReadingTask,
    ReadingScope,
    SearchHit,
    SearchMode,
)

DEFAULT_DEEPSEEK_BASE_URL = "https://api.deepseek.com"
DEFAULT_DEEPSEEK_MODEL = "deepseek-flash"


class ModelNotConfiguredError(RuntimeError):
    pass


class AnswerGenerationError(RuntimeError):
    pass


class ModelAnswerDraft(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    explanation: str
    cited_evidence_ids: list[int]
    insufficient_evidence: bool
    uncertainty: str


class AnswerModel(Protocol):
    provider_name: str
    model_name: str

    def generate(
        self,
        question: str,
        evidence: list[Evidence],
        language: LanguagePolicy | None = None,
        task: ReadingTask = "question",
        task_context: str = "",
    ) -> ModelAnswerDraft: ...


class SearchService(Protocol):
    def search(
        self,
        pdf_path: Path,
        paper_id: str,
        query: str,
        mode: SearchMode,
        limit: int = 5,
        scope: ReadingScope | None = None,
    ) -> list[SearchHit | Mapping[str, object]]: ...

    def page_text(self, pdf_path: Path, paper_id: str, source_page: int) -> str: ...


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
        language: LanguagePolicy | None = None,
        task: ReadingTask = "question",
        task_context: str = "",
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
                    "input": self._build_input(
                        question,
                        evidence,
                        language or LanguagePolicy(),
                        task,
                        task_context,
                    ),
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
    def _build_input(
        question: str,
        evidence: list[Evidence],
        language: LanguagePolicy | None = None,
        task: ReadingTask = "question",
        task_context: str = "",
    ) -> str:
        policy = language or LanguagePolicy()
        evidence_text = "\n\n".join(
            (
                f"[E{item.evidence_id} | PDF 第 {item.source_page} 页]\n"
                f"{item.text}"
            )
            for item in evidence
        )
        output_language = {
            "follow_question": "跟随用户问题的主要语言",
            "zh-CN": "简体中文",
            "en": "English",
        }[policy.explanation_language]
        terminology_instruction = {
            "bilingual_first_use": "专业术语首次出现时保留英文并给出中文对应，后续用词保持一致。",
            "preserve_english": "专业术语、缩写和变量保持英文，不擅自翻译。",
            "translate_all": "在不改变含义的前提下翻译术语；关键英文术语可在首次出现时括注。",
        }[policy.terminology_policy]
        if task == "translate":
            target_language = {
                "zh-CN": "简体中文",
                "en": "English",
            }[policy.translation_target]
            return (
                f"任务：把论文证据中标记为精确选区的原文翻译成{target_language}。\n"
                "周边上下文仅用于理解术语、指代和句法；不得翻译选区之外的内容，"
                "不得补充论文没有表达的意思。\n"
                f"术语策略：{terminology_instruction}\n"
                f"用户要求：{question}\n\n"
                f"仅供理解、不应额外翻译的同页上下文：\n{task_context}\n\n"
                "以下是唯一需要翻译的原文证据：\n\n"
                f"{evidence_text}\n\n"
                f"请用{target_language}填写 answer；explanation 简短说明术语处理。"
                "在 cited_evidence_ids 中列出支持译文的证据编号。"
            )
        return (
            f"问题：{question}\n\n"
            "以下是从当前论文中检索到的全部可用证据：\n\n"
            f"{evidence_text}\n\n"
            f"请用{output_language}填写 answer 和 explanation。"
            f"{terminology_instruction} "
            "在 cited_evidence_ids 中列出实际支持回答的证据编号。"
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
        scope: ReadingScope | None = None,
        language: LanguagePolicy | None = None,
        task: ReadingTask = "question",
        direct_evidence: list[SearchHit | Mapping[str, object]] | None = None,
        task_context: str = "",
    ) -> PaperAnswer:
        policy = language or LanguagePolicy()
        if direct_evidence is not None:
            raw_evidence = direct_evidence
        elif scope is None:
            raw_evidence = self.search_service.search(
                pdf_path,
                paper_id,
                question,
                mode,
                limit=limit,
            )
        else:
            raw_evidence = self.search_service.search(
                pdf_path,
                paper_id,
                question,
                mode,
                limit=limit,
                scope=scope,
            )
        evidence: list[Evidence] = []
        for index, item in enumerate(raw_evidence, start=1):
            hit = (
                item
                if isinstance(item, SearchHit)
                else SearchHit.model_validate(item)
            )
            evidence.append(
                Evidence(
                    evidence_id=index,
                    **hit.model_dump(),
                )
            )

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
                scope=scope or ReadingScope(),
                language=policy,
            )

        draft = self.answer_model.generate(
            question,
            evidence,
            policy,
            task,
            task_context,
        )
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
                scope=scope or ReadingScope(),
                language=policy,
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
            scope=scope or ReadingScope(),
            language=policy,
        )
