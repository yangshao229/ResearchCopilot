import { useEffect, useState } from "react";

import {
  answerPaper,
  createConversationSession,
  downloadPaperCard,
  getPaperReadingGuide,
  getPaperStructure,
  listConversationSessions,
  listReadingHistory,
  previewPaperCard,
  searchPaper,
  type ConversationSession,
  type Paper,
  type PaperAnswer,
  type PaperCardPreview,
  type PaperReadingGuide,
  type PaperStructure,
  type ReadingRecord,
  type SearchMode,
  type SearchResult,
  type ScopePreference,
} from "../api";
import type { PdfSelection } from "./PdfReader";
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
  | "evidence"
  | "history"
  | "summary"
  | "info";

type AssistantPanelProps = {
  paper: Paper;
  selection: PdfSelection | null;
  onClearSelection: () => void;
  onNavigateToPage: (pageNumber: number) => void;
};

export default function AssistantPanel({
  paper,
  selection,
  onClearSelection,
  onNavigateToPage,
}: AssistantPanelProps) {
  const [activeTab, setActiveTab] = useState<AssistantTab>("outline");
  const [question, setQuestion] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");
  const [scopePreference, setScopePreference] =
    useState<ScopePreference>("auto");
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
  const [cardPreview, setCardPreview] = useState<PaperCardPreview | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);
  const [isPreparingCard, setIsPreparingCard] = useState(false);
  const [isExportingCard, setIsExportingCard] = useState(false);
  const [structure, setStructure] = useState<PaperStructure | null>(null);
  const [structureError, setStructureError] = useState<string | null>(null);
  const [isLoadingStructure, setIsLoadingStructure] = useState(true);

  useEffect(() => {
    let isCurrent = true;
    setActiveSessionId("default");
    setHistory([]);
    setAllHistory([]);
    setSessions([]);
    setGuide(null);
    setHistoryError(null);
    setSessionError(null);
    setGuideError(null);

    listReadingHistory(paper.id)
      .then((records) => {
        if (isCurrent) {
          setAllHistory(records);
        }
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setHistoryError(
            reason instanceof Error ? reason.message : "阅读记录加载失败。",
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
            reason instanceof Error ? reason.message : "阅读会话加载失败。",
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
            reason instanceof Error ? reason.message : "论文阅读路线加载失败。",
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
            reason instanceof Error ? reason.message : "阅读记录加载失败。",
          );
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [paper.id, activeSessionId]);

  useEffect(() => {
    setIsLoadingStructure(true);
    setStructureError(null);
    getPaperStructure(paper.id)
      .then(setStructure)
      .catch((reason: unknown) => {
        setStructureError(
          reason instanceof Error ? reason.message : "论文目录加载失败。",
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
    setIsPreparingCard(true);
    try {
      setCardPreview(await previewPaperCard(paper.id));
    } catch (reason: unknown) {
      setCardError(
        reason instanceof Error ? reason.message : "论文卡片预览生成失败。",
      );
    } finally {
      setIsPreparingCard(false);
    }
  };

  const exportCard = async () => {
    setCardError(null);
    setIsExportingCard(true);
    try {
      await downloadPaperCard(
        paper.id,
        paper.name,
        cardPreview?.existing_card ?? false,
      );
    } catch (reason: unknown) {
      setCardError(
        reason instanceof Error ? reason.message : "论文卡片导出失败。",
      );
    } finally {
      setIsExportingCard(false);
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
        reason instanceof Error ? reason.message : "阅读会话创建失败。",
      );
    } finally {
      setIsCreatingSession(false);
    }
  };

  const sessionPanel = (
    <section className="session-panel" aria-label="当前阅读会话">
      <div className="session-heading">
        <div>
          <strong>当前会话</strong>
          <small>范围固定为 {paper.name}</small>
        </div>
        <select
          aria-label="选择阅读会话"
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
          placeholder="新会话，例如：方法精读"
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
          {isCreatingSession ? "创建中…" : "新建"}
        </button>
      </div>
      <p>切换会话只切换这篇论文的问答和笔记，不会混入其他论文。</p>
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
      });
      setActiveTab("evidence");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "证据检索失败。");
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
      });
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "全文检索失败。");
    } finally {
      setIsSearching(false);
    }
  };

  const runAnswer = async () => {
    const query = question.trim();
    if (!query || isBusy) {
      return;
    }

    setError(null);
    setIsAnswering(true);

    try {
      const paperAnswer = await answerPaper(
        paper.id,
        query,
        searchMode,
        activeSessionId,
        5,
        scopePreference,
      );
      setAnswer(paperAnswer);
      setResults(paperAnswer.evidence);
      setCompletedSearch({
        query,
        mode: searchMode,
        scope: paperAnswer.scope,
      });
      setActiveTab("ask");
      const [sessionHistory, paperHistory] = await Promise.all([
        listReadingHistory(paper.id, activeSessionId),
        listReadingHistory(paper.id),
      ]);
      setHistory(sessionHistory);
      setAllHistory(paperHistory);
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "论文回答生成失败。");
    } finally {
      setIsAnswering(false);
    }
  };

  return (
    <aside className="assistant-panel">
      <div className="assistant-tabs" role="tablist" aria-label="阅读辅助功能">
        <button
          type="button"
          className={activeTab === "outline" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "outline"}
          onClick={() => setActiveTab("outline")}
        >
          目录
        </button>
        <button
          type="button"
          className={activeTab === "ask" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "ask"}
          onClick={() => setActiveTab("ask")}
        >
          提问
        </button>
        <button
          type="button"
          className={activeTab === "evidence" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "evidence"}
          onClick={() => setActiveTab("evidence")}
        >
          证据{results.length > 0 ? ` ${results.length}` : ""}
        </button>
        <button
          type="button"
          className={activeTab === "history" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "history"}
          onClick={() => setActiveTab("history")}
        >
          笔记{history.length > 0 ? ` ${history.length}` : ""}
        </button>
        <button
          type="button"
          className={activeTab === "summary" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "summary"}
          onClick={() => setActiveTab("summary")}
        >
          总结
        </button>
        <button
          type="button"
          className={activeTab === "info" ? "active" : ""}
          role="tab"
          aria-selected={activeTab === "info"}
          onClick={() => setActiveTab("info")}
        >
          信息
        </button>
      </div>

      {activeTab === "ask" ? (
        <div className="assistant-content">
          <p className="eyebrow">当前论文</p>
          <h2>{paper.name}</h2>
          <p className="assistant-intro">
            页数、目录和标题等结构问题在本地直接回答；内容问题先检索论文证据，再让 DeepSeek 只根据证据回答并标注页码。
          </p>

          {sessionPanel}

          <section className="reading-guide" aria-label="这篇论文的阅读路线">
            <div className="reading-guide-heading">
              <div>
                <strong>这篇论文的阅读路线</strong>
                <small>根据真实目录生成，不套用固定问题</small>
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
                    <span>{item.label}</span>
                    <small>第 {item.source_page} 页起 · 点击填入问题</small>
                  </button>
                ))}
              </div>
            ) : (
              <p className="guide-unavailable">
                {guide?.warnings[0] ?? "正在根据论文目录准备建议…"}
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
                    ? "本地结构分析"
                    : answer.insufficient_evidence
                      ? "证据不足"
                      : "论文回答"}
                </strong>
                <span>
                  {answer.provider === "local" ? "未调用 API" : answer.model}
                </span>
              </div>
              <p className="answer-direct">{answer.answer}</p>
              {answer.scope.note && (
                <p className="outline-warning" role="status">
                  {answer.scope.note}
                </p>
              )}
              <div className="answer-section">
                <h3>解释</h3>
                <p>{answer.explanation}</p>
              </div>
              {answer.citations.length > 0 && (
                <div className="answer-section">
                  <h3>原文引用</h3>
                  <div className="citation-list">
                    {answer.citations.map((citation) => (
                      <button
                        type="button"
                        key={citation.evidence_id}
                        onClick={() => onNavigateToPage(citation.source_page)}
                      >
                        [E{citation.evidence_id}] 第 {citation.source_page} 页
                      </button>
                    ))}
                  </div>
                </div>
              )}
              <div className="answer-section uncertainty">
                <h3>不确定性</h3>
                <p>{answer.uncertainty || "当前回答未标记额外不确定性。"}</p>
              </div>
            </section>
          )}

          {selection && (
            <section className="selection-card">
              <div className="selection-card-heading">
                <strong>已选择第 {selection.sourcePage} 页原文</strong>
                <button type="button" onClick={onClearSelection}>
                  清除
                </button>
              </div>
              <blockquote>{selection.text}</blockquote>
              <button
                type="button"
                onClick={() => useSelection("请准确翻译下面的英文原文，并保留专业术语。")}
              >
                翻译
              </button>
              <button
                type="button"
                onClick={() => useSelection("请用中文解释下面这段原文，并说明理解它需要的前置知识。")}
              >
                解释
              </button>
              <button
                type="button"
                onClick={() => useSelection("请拆解下面原文涉及的公式或符号，说明变量、维度、步骤和直觉。")}
              >
                公式
              </button>
              <button
                type="button"
                onClick={() => useSelection("请基于论文证据回答我对下面原文的疑问：")}
              >
                提问
              </button>
            </section>
          )}

          <div className="mode-picker" aria-label="检索方式">
            <button
              type="button"
              className={searchMode === "hybrid" ? "selected" : ""}
              onClick={() => setSearchMode("hybrid")}
            >
              混合检索
              <small>综合术语与语义，默认推荐</small>
            </button>
            <button
              type="button"
              className={searchMode === "semantic" ? "selected" : ""}
              onClick={() => setSearchMode("semantic")}
            >
              语义检索
              <small>中文问题 → 英文原文</small>
            </button>
            <button
              type="button"
              className={searchMode === "keyword" ? "selected" : ""}
              onClick={() => setSearchMode("keyword")}
            >
              关键词检索
              <small>精确术语与缩写</small>
            </button>
          </div>

          {error && <p className="search-error">{error}</p>}
        </div>
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
          <p className="eyebrow">本地阅读记录</p>
          <h2>人工确认后再进入正式笔记</h2>
          <p className="assistant-intro">
            当前显示“{activeSession?.title ?? "默认阅读"}”的记录。核对引用、写下自己的理解并确认后，才能进入整篇论文的正式卡片。
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
              <span>还没有问答记录</span>
              <p>生成第一条带引用回答后，它会自动保存在这里。</p>
            </div>
          )}
        </div>
      ) : activeTab === "summary" ? (
        <SummaryView
          confirmedRecordCount={confirmedRecordCount}
          cardPreview={cardPreview}
          cardError={cardError}
          isPreparingCard={isPreparingCard}
          isExportingCard={isExportingCard}
          onPrepare={() => void prepareCard()}
          onExport={() => void exportCard()}
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
        <label htmlFor="question">
          向当前论文提问 · {activeSession?.title ?? "默认阅读"}
        </label>
        <p className="send-scope">
          结构问题只在本地处理；内容问题发送给 DeepSeek 的只有你的问题和最多 5 段本地证据，不会发送整篇论文。
        </p>
        <label className="scope-picker">
          检索范围
          <select
            aria-label="检索范围"
            value={scopePreference}
            onChange={(event) =>
              setScopePreference(event.target.value as ScopePreference)
            }
          >
            <option value="auto">自动识别问题中的章节</option>
            <option value="full_paper">全文</option>
          </select>
        </label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：为什么 Transformer 可以并行处理序列？"
          rows={4}
        />
        <div className="question-actions">
          <button
            type="button"
            className="secondary-action"
            disabled={!question.trim() || isBusy}
            onClick={() => void runSearch()}
          >
            {isSearching ? "正在检索…" : "只查原文证据"}
          </button>
          <button type="submit" disabled={!question.trim() || isBusy}>
            {isAnswering
              ? searchMode === "semantic"
                ? "检索证据并生成回答…"
                : "生成引用回答…"
              : "生成带引用回答"}
          </button>
        </div>
      </form>}
    </aside>
  );
}
