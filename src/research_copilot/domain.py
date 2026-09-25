from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


SearchMode = Literal["keyword", "semantic", "hybrid"]
ReadingCategory = Literal[
    "unclassified",
    "summary",
    "research_problem",
    "method",
    "experiments",
    "contributions",
    "limitations",
    "open_questions",
]
ReadingTask = Literal[
    "lookup",
    "translate",
    "explain",
    "formula",
    "question",
    "structure",
    "summarize",
]
ScopeKind = Literal["full_paper", "section", "selection"]
ScopeResolution = Literal["full_paper", "matched", "fallback"]
ScopePreference = Literal["auto", "full_paper"]
OutputLanguage = Literal["follow_question", "zh-CN", "en"]


class LanguagePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_language: OutputLanguage = "follow_question"
    translation_target: str = "zh-CN"
    terminology_policy: str = "bilingual_first_use"


class ReadingAnchor(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_page: int | None = Field(default=None, ge=1)
    selected_text: str = ""
    section_title: str = ""


class ReadingScope(BaseModel):
    model_config = ConfigDict(extra="forbid")

    kind: ScopeKind = "full_paper"
    resolution: ScopeResolution = "full_paper"
    section_title: str = ""
    start_page: int | None = Field(default=None, ge=1)
    end_page: int | None = Field(default=None, ge=1)
    note: str = ""


class ReadingContext(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    session_id: str = "default"
    query: str
    task: ReadingTask = "question"
    search_mode: SearchMode = "hybrid"
    scope_preference: ScopePreference = "auto"
    anchor: ReadingAnchor | None = None
    scope: ReadingScope = Field(default_factory=ReadingScope)
    language: LanguagePolicy = Field(default_factory=LanguagePolicy)


class SearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_page: int = Field(ge=1)
    chunk_index: int = Field(ge=0)
    text: str
    score: float
    keyword_rank: int = Field(default=0, ge=0)
    keyword_score: float = 0.0
    semantic_rank: int = Field(default=0, ge=0)
    semantic_score: float = 0.0
    fusion_score: float = 0.0
    reference_penalty: float = 0.0
    rerank_score: float = 0.0


class Evidence(SearchHit):
    evidence_id: int = Field(ge=1)


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    source_page: int = Field(ge=1)
    quote: str


class PaperAnswer(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    explanation: str
    citations: list[AnswerCitation]
    insufficient_evidence: bool
    uncertainty: str
    evidence: list[Evidence]
    provider: str
    model: str
    history_id: str | None = None
    scope: ReadingScope = Field(default_factory=ReadingScope)


class ReadingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    paper_name: str
    created_at: str
    question: str
    session_id: str = "default"
    search_mode: SearchMode
    answer: str
    explanation: str
    citations: list[AnswerCitation]
    insufficient_evidence: bool
    uncertainty: str
    provider: str
    model: str
    scope: ReadingScope = Field(default_factory=ReadingScope)
    confirmed: bool = False
    personal_note: str = ""
    category: ReadingCategory = "unclassified"
