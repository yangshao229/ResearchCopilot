import { useEffect, useState } from "react";

import {
  answerPaper,
  createConversationSession,
  getPaperLanguagePreferences,
  getPaperReadingGuide,
  getPaperStructure,
  listConversationSessions,
  listReadingHistory,
  previewSelectionContext,
  previewVaultPaperCard,
  searchPaper,
  savePaperLanguagePreferences,
  saveVaultPaperCard,
  type ConversationSession,
  type Paper,
  type PageLayout,
  type PageSourceRegion,
  type LanguagePolicy,
  type PaperAnswer,
  type VaultNotePreview,
  type PaperReadingGuide,
  type PaperStructure,
  type ReadingRecord,
  type ReadingQuestion,
  type SearchMode,
  type SearchResult,
  type ScopePreference,
  type ReadingAnchor,
  type SelectionContextPreview,
} from "../api";
import { useI18n } from "../i18n-context";
import type { MessageKey } from "../i18n";
import { scopeStatus, selectionStatus } from "../ui-status";
import type { PdfSelection } from "./PdfReader";
import GlossaryManager from "./GlossaryManager";
import PageTranslationPanel from "./PageTranslationPanel";
import {
  EvidenceView,
  HistoryCard,
  InfoView,
  OutlineView,
  SummaryView,
  type CompletedSearch,
} from "./assistant/AssistantViews";


type AssistantTab =
  | "ask"
  | "outline"
  | "translation"
  | "evidence"
  | "history"
  | "summary"
  | "info";

const guideRoleKeys: Record<ReadingQuestion["role"], MessageKey> = {
  overview: "assistant.guideRoleOverview",
  method: "assistant.guideRoleMethod",
  experiments: "assistant.guideRoleExperiments",
  critique: "assistant.guideRoleCritique",
};

type AssistantPanelProps = {
  paper: Paper;
  pageNumber: number;
  selection: PdfSelection | null;
  onClearSelection: () => void;
  onNavigateToPage: (pageNumber: number) => void;
  onFocusSourceRegion: (layout: PageLayout, region: PageSourceRegion) => void;
};

export default function AssistantPanel({
  paper,
  pageNumber,
  selection,
  onClearSelection,
  onNavigateToPage,
  onFocusSourceRegion,
}: AssistantPanelProps) {
  const { t, language, errorMessage } = useI18n();
  const [activeTab, setActiveTab] = useState<AssistantTab>("outline");
  const [question, setQuestion] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");
  const [scopePreference, setScopePreference] =
    useState<ScopePreference>("auto");
  const [languagePolicy, setLanguagePolicy] = useState<LanguagePolicy>({
    explanation_language: "follow_question",
    translation_target: "zh-CN",
    terminology_policy: "bilingual_first_use",
    source_language_override: "auto",
  });
  const [languagePolicyError, setLanguagePolicyError] = useState<string | null>(
    null,
  );
  const [isLoadingLanguagePolicy, setIsLoadingLanguagePolicy] =
    useState(true);
  const [isSavingLanguagePolicy, setIsSavingLanguagePolicy] = useState(false);
  const [completedSearch, setCompletedSearch] =
    useState<CompletedSearch | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<PaperAnswer | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ReadingRecord[]>([]);
  const [allHistory, setAllHistory] = useState<ReadingRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [sessions, setSessions] = useState<ConversationSession[]>([]);
  const [activeSessionId, setActiveSessionId] = useState("default");
  const [newSessionTitle, setNewSessionTitle] = useState("");
  const [sessionError, setSessionError] = useState<string | null>(null);
  const [isCreatingSession, setIsCreatingSession] = useState(false);
  const [guide, setGuide] = useState<PaperReadingGuide | null>(null);
  const [guideError, setGuideError] = useState<string | null>(null);
  const [cardPreview, setCardPreview] = useState<VaultNotePreview | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);
  const [cardSavedPath, setCardSavedPath] = useState<string | null>(null);
  const [isPreparingCard, setIsPreparingCard] = useState(false);
  const [isSavingCard, setIsSavingCard] = useState(false);
  const [structure, setStructure] = useState<PaperStructure | null>(null);
  const [structureError, setStructureError] = useState<string | null>(null);
  const [isLoadingStructure, setIsLoadingStructure] = useState(true);
  const [selectionPreview, setSelectionPreview] =
    useState<SelectionContextPreview | null>(null);
  const [selectionPreviewError, setSelectionPreviewError] =
    useState<string | null>(null);
  const [isLoadingSelectionPreview, setIsLoadingSelectionPreview] =
    useState(false);
  const [glossaryRevision, setGlossaryRevision] = useState(0);

  useEffect(() => {
    let isCurrent = true;
    setIsLoadingLanguagePolicy(true);
    setLanguagePolicyError(null);
    setLanguagePolicy({
      explanation_language: "follow_question",
      translation_target: "zh-CN",
      terminology_policy: "bilingual_first_use",
      source_language_override: "auto",
    });
    getPaperLanguagePreferences(paper.id)
      .then((preferences) => {
        if (isCurrent) setLanguagePolicy(preferences);
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setLanguagePolicyError(
            errorMessage(reason, "assistant.errorLanguageLoad"),
          );
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoadingLanguagePolicy(false);
      });
    setActiveSessionId("default");
    setHistory([]);
    setAllHistory([]);
    setSessions([]);
    setGuide(null);
    setHistoryError(null);
    setSessionError(null);
    setGuideError(null);
    setCardPreview(null);
    setCardSavedPath(null);
    setCardError(null);

    listReadingHistory(paper.id)
      .then((records) => {
        if (isCurrent) {
          setAllHistory(records);
        }
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setHistoryError(
            errorMessage(reason, "assistant.errorHistoryLoad"),
          );
        }
      });
    listConversationSessions(paper.id)
      .then((paperSessions) => {
        if (isCurrent) {
          setSessions(paperSessions);
        }
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setSessionError(
            errorMessage(reason, "assistant.errorSessionsLoad"),
          );
        }
      });
    getPaperReadingGuide(paper.id)
      .then((paperGuide) => {
        if (isCurrent) {
          setGuide(paperGuide);
        }
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setGuideError(
            errorMessage(reason, "assistant.errorGuideLoad"),
          );
        }
      });

    return () => {
      isCurrent = false;
    };
  }, [paper.id]);

  useEffect(() => {
    let isCurrent = true;
    setHistoryError(null);
    setAnswer(null);
    setResults([]);
    setCompletedSearch(null);
    listReadingHistory(paper.id, activeSessionId)
      .then((records) => {
        if (isCurrent) {
          setHistory(records);
        }
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setHistoryError(
            errorMessage(reason, "assistant.errorHistoryLoad"),
          );
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [paper.id, activeSessionId]);

  useEffect(() => {
    setCompletedSearch(null);
    setResults([]);
  }, [question, searchMode, scopePreference]);

  useEffect(() => {
    let isCurrent = true;
    setSelectionPreview(null);
    setSelectionPreviewError(null);
    if (!selection) {
      setIsLoadingSelectionPreview(false);
      return () => {
        isCurrent = false;
      };
    }

    setIsLoadingSelectionPreview(true);
    previewSelectionContext(
      paper.id,
      selection.sourcePage,
      selection.text,
      languagePolicy.translation_target,
    )
      .then((preview) => {
        if (isCurrent) setSelectionPreview(preview);
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setSelectionPreviewError(
            errorMessage(reason, "assistant.errorSelectionPreview"),
          );
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoadingSelectionPreview(false);
      });
    return () => {
      isCurrent = false;
    };
  }, [
    paper.id,
    selection?.sourcePage,
    selection?.text,
    languagePolicy.translation_target,
    glossaryRevision,
  ]);

  useEffect(() => {
    setIsLoadingStructure(true);
    setStructureError(null);
    getPaperStructure(paper.id)
      .then(setStructure)
      .catch((reason: unknown) => {
        setStructureError(
          errorMessage(reason, "assistant.errorStructureLoad"),
        );
      })
      .finally(() => setIsLoadingStructure(false));
  }, [paper.id]);

  const isBusy = isSearching || isAnswering;
  const confirmedRecordCount = allHistory.filter(
    (record) => record.confirmed,
  ).length;
  const activeSession = sessions.find(
    (session) => session.id === activeSessionId,
  );

  const updateLanguagePolicy = async (nextPolicy: LanguagePolicy) => {
    setLanguagePolicyError(null);
    setIsSavingLanguagePolicy(true);
    try {
      const saved = await savePaperLanguagePreferences(paper.id, nextPolicy);
      setLanguagePolicy(saved);
    } catch (reason: unknown) {
      setLanguagePolicyError(
        errorMessage(reason, "assistant.errorLanguageSave"),
      );
    } finally {
      setIsSavingLanguagePolicy(false);
    }
  };

  const useSelection = (instruction: string) => {
    if (!selection) {
      return;
    }
    const excerpt = selection.text.slice(0, 1400);
    setQuestion(
      `${instruction}\n\nPDF 第 ${selection.sourcePage} 页原文：\n${excerpt}`,
    );
    setActiveTab("ask");
  };

  const prepareCard = async () => {
    setCardError(null);
    setCardPreview(null);
    setCardSavedPath(null);
    setIsPreparingCard(true);
    try {
      setCardPreview(await previewVaultPaperCard(paper.id));
    } catch (reason: unknown) {
      setCardError(
        errorMessage(reason, "assistant.errorCardPreview"),
      );
    } finally {
      setIsPreparingCard(false);
    }
  };

  const saveCard = async () => {
    if (!cardPreview || cardPreview.already_exists) return;
    setCardError(null);
    setIsSavingCard(true);
    try {
      const saved = await saveVaultPaperCard(paper.id, cardPreview.sha256);
      setCardSavedPath(saved.path);
      setCardPreview(null);
      window.dispatchEvent(new Event("research-copilot:vault-changed"));
    } catch (reason: unknown) {
      setCardError(
        errorMessage(reason, "assistant.errorCardExport"),
      );
      setCardPreview(null);
    } finally {
      setIsSavingCard(false);
    }
  };

  const createSession = async () => {
    const title = newSessionTitle.trim();
    if (!title || isCreatingSession) {
      return;
    }
    setSessionError(null);
    setIsCreatingSession(true);
    try {
      const created = await createConversationSession(paper.id, title);
      setSessions((current) => [...current, created]);
      setActiveSessionId(created.id);
      setNewSessionTitle("");
    } catch (reason: unknown) {
      setSessionError(
        errorMessage(reason, "assistant.errorSessionCreate"),
      );
    } finally {
      setIsCreatingSession(false);
    }
  };

  const sessionPanel = (
    <section className="session-panel" aria-label={t("assistant.sessionAria")}>
      <div className="session-heading">
        <div>
          <strong>{t("assistant.currentSession")}</strong>
          <small>{t("assistant.sessionScope", { paper: paper.name })}</small>
        </div>
        <select
          aria-label={t("assistant.selectSessionAria")}
          value={activeSessionId}
          onChange={(event) => setActiveSessionId(event.target.value)}
        >
          {sessions.map((session) => (
            <option key={session.id} value={session.id}>
              {session.title}
            </option>
          ))}
        </select>
      </div>
      <div className="session-create">
        <input
          type="text"
          value={newSessionTitle}
          maxLength={80}
          placeholder={t("assistant.newSessionPlaceholder")}
          onChange={(event) => setNewSessionTitle(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              event.preventDefault();
              void createSession();
            }
          }}
        />
        <button
          type="button"
          disabled={!newSessionTitle.trim() || isCreatingSession}
          onClick={() => void createSession()}
        >
          {isCreatingSession
            ? t("assistant.creatingSession")
            : t("assistant.createSession")}
        </button>
      </div>
      <p>{t("assistant.sessionHelp")}</p>
      {sessionError && <p className="search-error">{sessionError}</p>}
    </section>
  );

  const runSearch = async () => {
    const query = question.trim();
    if (!query || isBusy) {
      return;
    }

    setError(null);
    setIsSearching(true);

    try {
      const searchExecution = await searchPaper(
        paper.id,
        query,
        searchMode,
        5,
        scopePreference,
      );
      setResults(searchExecution.results);
      setCompletedSearch({
        query,
        mode: searchMode,
        scope: searchExecution.scope,
        scopePreference,
        snapshotToken: searchExecution.snapshotToken,
      });
      setActiveTab("evidence");
    } catch (reason: unknown) {
      setError(errorMessage(reason, "assistant.errorSearch"));
    } finally {
      setIsSearching(false);
    }
  };

  const runFullPaperSearch = async () => {
    const query = completedSearch?.query ?? question.trim();
    if (!query || isBusy) return;

    setScopePreference("full_paper");
    setError(null);
    setIsSearching(true);
    try {
      const searchExecution = await searchPaper(
        paper.id,
        query,
        searchMode,
        5,
        "full_paper",
      );
      setResults(searchExecution.results);
      setCompletedSearch({
        query,
        mode: searchMode,
        scope: searchExecution.scope,
        scopePreference: "full_paper",
        snapshotToken: searchExecution.snapshotToken,
      });
    } catch (reason: unknown) {
      setError(errorMessage(reason, "assistant.errorFullSearch"));
    } finally {
      setIsSearching(false);
    }
  };

  const runAnswer = async (
    task: "question" | "translate" = "question",
    anchor?: ReadingAnchor,
    refreshTranslation = false,
  ) => {
    const query = task === "translate" ? "翻译当前选中的论文原文" : question.trim();
    if (!query || isBusy) {
      return;
    }

    setError(null);
    setIsAnswering(true);

    try {
      const evidenceSnapshot = task === "question"
        && completedSearch?.query === query
        && completedSearch.mode === searchMode
        && completedSearch.scopePreference === scopePreference
        ? completedSearch.snapshotToken ?? undefined
        : undefined;
      const paperAnswer = await answerPaper(
        paper.id,
        query,
        searchMode,
        activeSessionId,
        5,
        scopePreference,
        languagePolicy,
        task,
        anchor,
        refreshTranslation,
        evidenceSnapshot,
      );
      setAnswer(paperAnswer);
      setResults(paperAnswer.evidence);
      setCompletedSearch({
        query,
        mode: searchMode,
        scope: paperAnswer.scope,
        scopePreference,
        snapshotToken: null,
      });
      setActiveTab("ask");
      const [sessionHistory, paperHistory] = await Promise.all([
        listReadingHistory(paper.id, activeSessionId),
        listReadingHistory(paper.id),
      ]);
      setHistory(sessionHistory);
      setAllHistory(paperHistory);
    } catch (reason: unknown) {
      setError(errorMessage(reason, "assistant.errorAnswer"));
    } finally {
      setIsAnswering(false);
    }
  };

  const cachedTranslationAnchor = answer?.cache_hit
    ? history.find((item) => item.id === answer.history_id)?.anchor
    : undefined;

  return (
    <aside className="assistant-panel">
      <div className="assistant-tabs" role="tablist" aria-label={t("assistant.tabsAria")}>
        <button
          type="button"
          className={activeTab === "outline" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "outline"}
          onClick={() => setActiveTab("outline")}
        >
          {t("assistant.tabOutline")}
        </button>
        <button
          type="button"
          className={activeTab === "translation" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "translation"}
          onClick={() => setActiveTab("translation")}
        >
          {t("assistant.tabTranslation")}
        </button>
        <button
          type="button"
          className={activeTab === "ask" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "ask"}
          onClick={() => setActiveTab("ask")}
        >
          {t("assistant.tabAsk")}
        </button>
        <button
          type="button"
          className={activeTab === "evidence" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "evidence"}
          onClick={() => setActiveTab("evidence")}
        >
          {t("assistant.tabEvidence")}{results.length > 0 ? ` ${results.length}` : ""}
        </button>
        <button
          type="button"
          className={activeTab === "history" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
        >
          {t("assistant.tabNotes")}{history.length > 0 ? ` ${history.length}` : ""}
        </button>
        <button
          type="button"
          className={activeTab === "summary" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "summary"}
          onClick={() => setActiveTab("summary")}
        >
          {t("assistant.tabSummary")}
        </button>
        <button
          type="button"
          className={activeTab === "info" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "info"}
          onClick={() => setActiveTab("info")}
        >
          {t("assistant.tabInfo")}
        </button>
      </div>

      {activeTab === "ask" ? (
        <div className="assistant-content">
          <p className="eyebrow">{t("assistant.currentPaper")}</p>
          <h2>{paper.name}</h2>
          <p className="assistant-intro">{t("assistant.intro")}</p>

          {sessionPanel}

          <section className="reading-guide" aria-label={t("assistant.readingGuideAria")}>
            <div className="reading-guide-heading">
              <div>
                <strong>{t("assistant.readingGuideTitle")}</strong>
                <small>{t("assistant.readingGuideSubtitle")}</small>
              </div>
            </div>
            {guideError ? (
              <p className="search-error">{guideError}</p>
            ) : guide && guide.questions.length > 0 ? (
              <div className="guide-question-list">
                {guide.questions.map((item) => (
                  <button
                    type="button"
                    key={`${item.role}-${item.source_page}-${item.label}`}
                    onClick={() => setQuestion(item.question)}
                  >
                    <span>{language === "zh-CN"
                      ? item.label
                      : `${t(guideRoleKeys[item.role])} · ${item.section_title}`}</span>
                    <small>{t("assistant.guideQuestionMeta", { page: item.source_page })}</small>
                  </button>
                ))}
              </div>
            ) : (
              <p className="guide-unavailable">
                {guide?.warnings[0]
                  ? language === "zh-CN" ? guide.warnings[0] : t("status.guideUnavailable")
                  : t("assistant.guideLoading")}
              </p>
            )}
          </section>

          {answer && (
            <section
              className={
                answer.insufficient_evidence
                  ? "answer-card insufficient"
                  : "answer-card"
              }
            >
              <div className="answer-heading">
                <strong>
                  {answer.provider === "local"
                    ? t("assistant.localAnalysis")
                    : answer.insufficient_evidence
                      ? t("assistant.insufficientEvidence")
                      : t("assistant.paperAnswer")}
                </strong>
                <span>
                  {answer.cache_hit
                    ? t("assistant.cachedTranslation")
                    : answer.provider === "local"
                      ? t("assistant.noApi")
                      : answer.model}
                </span>
              </div>
              <p className="answer-direct">{answer.answer}</p>
              {answer.cache_hit && cachedTranslationAnchor && (
                <button
                  type="button"
                  className="translation-refresh"
                  disabled={isBusy}
                  onClick={() =>
                    void runAnswer("translate", cachedTranslationAnchor, true)
                  }
                >
                  {t("assistant.retranslate")}
                </button>
              )}
              {answer.scope.note && (
                <p className="outline-warning" role="status">
                  {scopeStatus(answer.scope, language, t)}
                </p>
              )}
              <div className="answer-section">
                <h3>{t("assistant.explanation")}</h3>
                <p>{answer.explanation}</p>
              </div>
              {answer.citations.length > 0 && (
                <div className="answer-section">
                  <h3>{t("assistant.sourceCitations")}</h3>
                  <div className="citation-list">
                    {answer.citations.map((citation) => (
                      <button
                        type="button"
                        key={citation.evidence_id}
                        onClick={() => onNavigateToPage(citation.source_page)}
                      >
                        {t("assistant.pageCitation", {
                          evidence: citation.evidence_id,
                          page: citation.source_page,
                        })}
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="answer-section uncertainty">
                <h3>{t("assistant.uncertainty")}</h3>
                <p>{answer.uncertainty || t("assistant.noExtraUncertainty")}</p>
              </div>
            </section>
          )}

          {selection && (
            <section className="selection-card">
              <div className="selection-card-heading">
                <strong>{t("assistant.selectedSource", { page: selection.sourcePage })}</strong>
                <button type="button" onClick={onClearSelection}>
                  {t("assistant.clear")}
                </button>
              </div>
              <blockquote>{selection.text}</blockquote>
              {isLoadingSelectionPreview && (
                <p className="selection-context-note">{t("assistant.loadingSelectionContext")}</p>
              )}
              {selectionPreviewError && (
                <p className="selection-context-note">{selectionPreviewError}</p>
              )}
              {selectionPreview && (
                <div className="selection-context-preview">
                  <p className="selection-context-note">
                    {t("assistant.selectionSendIntro", {
                      page: selectionPreview.source_page,
                      language:
                        languagePolicy.translation_target === "zh-CN"
                          ? t("assistant.languageChinese")
                          : t("assistant.languageEnglish"),
                      context:
                        selectionPreview.method === "selection_only"
                          ? t("assistant.selectionOnly")
                          : t("assistant.selectionWithContext", {
                              count: selectionPreview.context_text.length,
                            }),
                    })} {selectionStatus(selectionPreview, language, t)}
                  </p>
                  <details>
                    <summary>{t("assistant.showSentContext")}</summary>
                    <strong>{t("assistant.exactSelection")}</strong>
                    <blockquote>{selectionPreview.selected_text}</blockquote>
                    {selectionPreview.method !== "selection_only" && (
                      <>
                        <strong>{t("assistant.disambiguationContext")}</strong>
                        <blockquote>{selectionPreview.context_text}</blockquote>
                      </>
                    )}
                  </details>
                  <p className="selection-context-note">
                    {t("assistant.glossaryHits", {
                      terms:
                        selectionPreview.glossary_terms.length === 0
                          ? t("assistant.none")
                          : selectionPreview.glossary_terms
                              .map((entry) => `${entry.source} → ${entry.translation}`)
                              .join(" · "),
                    })}
                  </p>
                  <button
                    type="button"
                    disabled={isBusy || isLoadingLanguagePolicy}
                    onClick={() =>
                      void runAnswer("translate", {
                        source_page: selectionPreview.source_page,
                        selected_text: selectionPreview.selected_text,
                        section_title: "",
                      })
                    }
                  >
                    {isAnswering
                      ? t("assistant.translating")
                      : t("assistant.translateSelection")}
                  </button>
                </div>
              )}
              <button
                type="button"
                onClick={() => useSelection("请用中文解释下面这段原文，并说明理解它需要的前置知识。")}
              >
                {t("assistant.selectionExplain")}
              </button>
              <button
                type="button"
                onClick={() => useSelection("请拆解下面原文涉及的公式或符号，说明变量、维度、步骤和直觉。")}
              >
                {t("assistant.selectionFormula")}
              </button>
              <button
                type="button"
                onClick={() => useSelection("请基于论文证据回答我对下面原文的疑问：")}
              >
                {t("assistant.selectionAsk")}
              </button>
            </section>
          )}

          <GlossaryManager
            paperId={paper.id}
            targetLanguage={languagePolicy.translation_target}
            selectionText={selection?.text ?? ""}
            onChange={() => setGlossaryRevision((revision) => revision + 1)}
          />

          <div className="mode-picker" aria-label={t("assistant.searchModeAria")}>
            <button
              type="button"
              className={searchMode === "hybrid" ? "selected" : ""}
              onClick={() => setSearchMode("hybrid")}
            >
              {t("assistant.hybridSearch")}
              <small>{t("assistant.hybridSearchHelp")}</small>
            </button>
            <button
              type="button"
              className={searchMode === "semantic" ? "selected" : ""}
              onClick={() => setSearchMode("semantic")}
            >
              {t("assistant.semanticSearch")}
              <small>{t("assistant.semanticSearchHelp")}</small>
            </button>
            <button
              type="button"
              className={searchMode === "keyword" ? "selected" : ""}
              onClick={() => setSearchMode("keyword")}
            >
              {t("assistant.keywordSearch")}
              <small>{t("assistant.keywordSearchHelp")}</small>
            </button>
          </div>

          {error && <p className="search-error">{error}</p>}
        </div>
      ) : activeTab === "translation" ? (
        <PageTranslationPanel
          paperId={paper.id}
          sourcePage={pageNumber}
          targetLanguage={languagePolicy.translation_target}
          onFocusSourceRegion={onFocusSourceRegion}
        />
      ) : activeTab === "outline" ? (
        <OutlineView
          structure={structure}
          error={structureError}
          isLoading={isLoadingStructure}
          onNavigateToPage={onNavigateToPage}
        />
      ) : activeTab === "evidence" ? (
        <EvidenceView
          completedSearch={completedSearch}
          results={results}
          onUseFullPaper={() => void runFullPaperSearch()}
          onNavigateToPage={onNavigateToPage}
        />
      ) : activeTab === "history" ? (
        <div className="assistant-content history-content">
          <p className="eyebrow">{t("assistant.historyEyebrow")}</p>
          <h2>{t("assistant.historyTitle")}</h2>
          <p className="assistant-intro">
            {t("assistant.historyIntro", {
              session: activeSession?.title ?? t("assistant.defaultSession"),
            })}
          </p>
          {sessionPanel}
          {historyError && <p className="search-error">{historyError}</p>}
          {history.length > 0 ? (
            <div className="history-list">
              {history.map((record) => (
                <HistoryCard
                  key={record.id}
                  paperId={paper.id}
                  record={record}
                  onNavigateToPage={onNavigateToPage}
                  onSaved={(updatedRecord) => {
                    setCardPreview(null);
                    setHistory((currentHistory) =>
                      currentHistory.map((item) =>
                        item.id === updatedRecord.id ? updatedRecord : item,
                      ),
                    );
                    setAllHistory((currentHistory) =>
                      currentHistory.map((item) =>
                        item.id === updatedRecord.id ? updatedRecord : item,
                      ),
                    );
                  }}
                />
              ))}
            </div>
          ) : (
            <div className="empty-conversation">
              <span>{t("assistant.emptyHistoryTitle")}</span>
              <p>{t("assistant.emptyHistoryBody")}</p>
            </div>
          )}
        </div>
      ) : activeTab === "summary" ? (
        <SummaryView
          paper={paper}
          confirmedRecordCount={confirmedRecordCount}
          cardPreview={cardPreview}
          cardError={cardError}
          cardSavedPath={cardSavedPath}
          isPreparingCard={isPreparingCard}
          isSavingCard={isSavingCard}
          onPrepare={() => void prepareCard()}
          onSave={() => void saveCard()}
        />
      ) : (
        <InfoView paper={paper} confirmedRecordCount={confirmedRecordCount} />
      )}

      {(activeTab === "ask" || activeTab === "evidence") && <form
        className="question-box"
        onSubmit={(event) => {
          event.preventDefault();
          void runAnswer();
        }}
      >
        {error && activeTab === "evidence" && (
          <p className="search-error" role="alert">{error}</p>
        )}
        <label htmlFor="question">
          {t("assistant.askCurrentPaper", {
            session: activeSession?.title ?? t("assistant.defaultSession"),
          })}
        </label>
        <p className="send-scope">{t("assistant.sendScope")}</p>
        <label className="scope-picker">
          {t("assistant.scopeLabel")}
          <select
            aria-label={t("assistant.scopeAria")}
            value={scopePreference}
            onChange={(event) =>
              setScopePreference(event.target.value as ScopePreference)
            }
          >
            <option value="auto">{t("assistant.scopeAuto")}</option>
            <option value="full_paper">{t("assistant.scopeFullPaper")}</option>
          </select>
        </label>
        <div className="language-preferences" aria-label={t("assistant.languagePreferencesAria")}>
          <div className="source-language-control">
            <label>
              {t("assistant.sourceLanguage")}
              <select
                value={languagePolicy.source_language_override}
                disabled={isLoadingLanguagePolicy || isSavingLanguagePolicy}
                onChange={(event) =>
                  void updateLanguagePolicy({
                    ...languagePolicy,
                    source_language_override: event.target.value as LanguagePolicy["source_language_override"],
                  })
                }
              >
                <option value="auto">{t("assistant.sourceAuto")}</option>
                <option value="en">{t("assistant.sourceManualEnglish")}</option>
                <option value="zh-CN">{t("assistant.sourceManualChinese")}</option>
              </select>
            </label>
            <p className="source-language-hint">
              {languagePolicy.source_language_override === "auto"
                ? t("assistant.detectedSource", {
                    language: {
                      en: t("assistant.sourceEnglish"),
                      "zh-CN": t("assistant.sourceChinese"),
                      mixed: t("assistant.sourceMixed"),
                      unknown: t("assistant.sourceUnknown"),
                    }[paper.detected_source_language],
                  })
                : t("assistant.overriddenSource", {
                    language:
                      languagePolicy.source_language_override === "en"
                        ? t("assistant.sourceEnglish")
                        : t("assistant.sourceChinese"),
                  })}
            </p>
          </div>
          <label>
            {t("assistant.answerLanguage")}
            <select
              value={languagePolicy.explanation_language}
              disabled={isLoadingLanguagePolicy || isSavingLanguagePolicy}
              onChange={(event) =>
                void updateLanguagePolicy({
                  ...languagePolicy,
                  explanation_language: event.target.value as LanguagePolicy["explanation_language"],
                })
              }
            >
              <option value="follow_question">{t("assistant.followQuestion")}</option>
              <option value="zh-CN">{t("assistant.languageChinese")}</option>
              <option value="en">{t("assistant.languageEnglish")}</option>
            </select>
          </label>
          <label>
            {t("assistant.translationTarget")}
            <select
              value={languagePolicy.translation_target}
              disabled={isLoadingLanguagePolicy || isSavingLanguagePolicy}
              onChange={(event) =>
                void updateLanguagePolicy({
                  ...languagePolicy,
                  translation_target: event.target.value as LanguagePolicy["translation_target"],
                })
              }
            >
              <option value="zh-CN">{t("assistant.languageChinese")}</option>
              <option value="en">{t("assistant.languageEnglish")}</option>
            </select>
          </label>
          <label>
            {t("assistant.terminology")}
            <select
              value={languagePolicy.terminology_policy}
              disabled={isLoadingLanguagePolicy || isSavingLanguagePolicy}
              onChange={(event) =>
                void updateLanguagePolicy({
                  ...languagePolicy,
                  terminology_policy: event.target.value as LanguagePolicy["terminology_policy"],
                })
              }
            >
              <option value="bilingual_first_use">{t("assistant.terminologyBilingual")}</option>
              <option value="preserve_english">{t("assistant.terminologyEnglish")}</option>
              <option value="translate_all">{t("assistant.terminologyTranslate")}</option>
            </select>
          </label>
        </div>
        {languagePolicyError && (
          <p className="search-error">{languagePolicyError}</p>
        )}
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder={t("assistant.questionPlaceholder")}
          rows={4}
        />
        <div className="question-actions">
          <button
            type="button"
            className="secondary-action"
            disabled={!question.trim() || isBusy}
            onClick={() => void runSearch()}
          >
            {isSearching
              ? t("assistant.searching")
              : t("assistant.searchEvidenceOnly")}
          </button>
          <button type="submit" disabled={!question.trim() || isBusy}>
            {isAnswering
              ? searchMode === "semantic"
                ? t("assistant.searchingAndAnswering")
                : t("assistant.answering")
              : t("assistant.generateAnswer")}
          </button>
        </div>
      </form>}
    </aside>
  );
}
