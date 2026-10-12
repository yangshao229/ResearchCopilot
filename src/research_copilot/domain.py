from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


SearchMode = Literal["keyword", "semantic", "hybrid"]
EvidenceOrigin = Literal["retrieval", "selection"]
ResearchEvidenceStatus = Literal["matched", "no_match", "unsearchable"]
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
TranslationLanguage = Literal["zh-CN", "en"]
SourceLanguageOverride = Literal["auto", "zh-CN", "en"]
TerminologyPolicy = Literal[
    "bilingual_first_use",
    "preserve_english",
    "translate_all",
]


class LanguagePolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")

    explanation_language: OutputLanguage = "follow_question"
    translation_target: TranslationLanguage = "zh-CN"
    terminology_policy: TerminologyPolicy = "bilingual_first_use"
    source_language_override: SourceLanguageOverride = "auto"


class GlossaryEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    source: str = Field(min_length=1, max_length=100)
    translation: str = Field(min_length=1, max_length=100)
    target_language: TranslationLanguage


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
    refresh_translation: bool = False


class SourceDocumentRef(BaseModel):
    """Stable identity of the exact PDF version used for a reading task."""

    model_config = ConfigDict(extra="forbid")

    paper_uid: str = Field(pattern=r"^paper-[0-9a-f]{32}$")
    pdf_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")

    def at_page(self, source_page: int) -> "SourceAnchor":
        return SourceAnchor(
            paper_uid=self.paper_uid,
            pdf_sha256=self.pdf_sha256,
            source_page=source_page,
        )


class SourceAnchor(SourceDocumentRef):
    source_page: int = Field(ge=1)


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
    source: SourceAnchor | None = None

    @model_validator(mode="after")
    def source_must_match_page(self) -> "SearchHit":
        if self.source is not None and self.source.source_page != self.source_page:
            raise ValueError("Evidence source page does not match the search hit.")
        return self


class LibrarySearchHit(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    paper_name: str
    source_page: int = Field(ge=1)
    text: str
    score: float = Field(gt=0)


class LibrarySearchResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    results: list[LibrarySearchHit]
    requested_paper_count: int = Field(ge=0)
    searched_paper_count: int = Field(ge=0)
    skipped_paper_count: int = Field(ge=0)


class ResearchPaperEvidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    paper_id: str
    paper_name: str
    status: ResearchEvidenceStatus
    hits: list[LibrarySearchHit]


class ResearchEvidenceResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    query: str
    papers: list[ResearchPaperEvidence]


class Evidence(SearchHit):
    evidence_id: int = Field(ge=1)


class AnswerCitation(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: int = Field(ge=1)
    source_page: int = Field(ge=1)
    quote: str
    source: SourceAnchor | None = None

    @model_validator(mode="after")
    def source_must_match_page(self) -> "AnswerCitation":
        if self.source is not None and self.source.source_page != self.source_page:
            raise ValueError("Citation source page does not match the quote page.")
        return self


class EvidenceSet(BaseModel):
    """Original-text candidates supplied to a task, not a sufficiency verdict."""

    model_config = ConfigDict(extra="forbid")

    query: str
    origin: EvidenceOrigin
    scope: ReadingScope = Field(default_factory=ReadingScope)
    candidates: list[Evidence] = Field(default_factory=list)

    @model_validator(mode="after")
    def candidate_ids_must_be_sequential(self) -> "EvidenceSet":
        ids = [candidate.evidence_id for candidate in self.candidates]
        if ids != list(range(1, len(ids) + 1)):
            raise ValueError("Evidence IDs must be unique and sequential.")
        return self

    def citations_for(self, requested_ids: list[int]) -> list[AnswerCitation]:
        by_id = {candidate.evidence_id: candidate for candidate in self.candidates}
        return [
            AnswerCitation(
                evidence_id=evidence_id,
                source_page=by_id[evidence_id].source_page,
                quote=by_id[evidence_id].text,
                source=by_id[evidence_id].source,
            )
            for evidence_id in dict.fromkeys(requested_ids)
            if evidence_id in by_id
        ]


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
    language: LanguagePolicy = Field(default_factory=LanguagePolicy)
    cache_hit: bool = False


class ReadingRecord(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    paper_id: str
    paper_name: str
    created_at: str
    question: str
    task: ReadingTask = "question"
    session_id: str = "default"
    anchor: ReadingAnchor | None = None
    context_text: str = ""
    prompt_version: str = ""
    glossary_signature: str = ""
    search_mode: SearchMode
    answer: str
    explanation: str
    citations: list[AnswerCitation]
    insufficient_evidence: bool
    uncertainty: str
    provider: str
    model: str
    scope: ReadingScope = Field(default_factory=ReadingScope)
    language: LanguagePolicy = Field(default_factory=LanguagePolicy)
    confirmed: bool = False
    personal_note: str = ""
    category: ReadingCategory = "unclassified"
