import { useEffect, useState } from "react";

import {
  answerPaper,
  downloadPaperCard,
  exportReadingRecordUrl,
  listReadingHistory,
  previewPaperCard,
  searchPaper,
  type Paper,
  type PaperAnswer,
  type PaperCardPreview,
  type ReadingCategory,
  type ReadingRecord,
  type SearchMode,
  type SearchResult,
  updateReadingRecord,
} from "../api";
import type { PdfSelection } from "./PdfReader";


type AssistantTab = "ask" | "evidence" | "history" | "summary";

const CATEGORY_OPTIONS: Array<{ value: ReadingCategory; label: string }> = [
  { value: "unclassified", label: "待分类" },
  { value: "summary", label: "一句话结论" },
  { value: "research_problem", label: "研究问题" },
  { value: "method", label: "方法" },
  { value: "experiments", label: "实验" },
  { value: "contributions", label: "贡献" },
  { value: "limitations", label: "局限" },
  { value: "open_questions", label: "未解决问题" },
];

type CompletedSearch = {
  query: string;
  mode: SearchMode;
};

type AssistantPanelProps = {
  paper: Paper;
  selection: PdfSelection | null;
  onClearSelection: () => void;
  onNavigateToPage: (pageNumber: number) => void;
};

function scoreLabel(result: SearchResult, mode: SearchMode): string {
  if (mode === "keyword") {
    return `命中 ${result.score} 次`;
  }
  if (mode === "hybrid") {
    return `重排分 ${result.rerank_score.toFixed(4)}`;
  }
  return `相似度 ${result.score.toFixed(4)}`;
}

function rankExplanation(result: SearchResult): string {
  const ranks = [];
  if (result.keyword_rank > 0) {
    ranks.push(`关键词 #${result.keyword_rank}`);
  }
  if (result.semantic_rank > 0) {
    ranks.push(`语义 #${result.semantic_rank}`);
  }
  if (result.reference_penalty > 0) {
    ranks.push("已降低参考文献权重");
  }
  return ranks.join(" · ");
}

type HistoryCardProps = {
  paperId: string;
  record: ReadingRecord;
  onNavigateToPage: (pageNumber: number) => void;
  onSaved: (record: ReadingRecord) => void;
};

function HistoryCard({
  paperId,
  record,
  onNavigateToPage,
  onSaved,
}: HistoryCardProps) {
  const [note, setNote] = useState(record.personal_note);
  const [category, setCategory] = useState<ReadingCategory>(record.category);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const save = async (confirmed: boolean) => {
    setIsSaving(true);
    setSaveError(null);
    try {
      onSaved(
        await updateReadingRecord(
          paperId,
          record.id,
          confirmed,
          note,
          category,
        ),
      );
    } catch (reason: unknown) {
      setSaveError(reason instanceof Error ? reason.message : "保存失败。");
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <article className={record.confirmed ? "history-card confirmed" : "history-card"}>
      <div className="history-heading">
        <span>{record.confirmed ? "已人工确认" : "待人工确认"}</span>
        <time dateTime={record.created_at}>
          {new Date(record.created_at).toLocaleString("zh-CN")}
        </time>
      </div>
      <h3>{record.question}</h3>
      <p className="history-answer">{record.answer}</p>
      {record.citations.length > 0 && (
        <div className="citation-list">
          {record.citations.map((citation) => (
            <button
              type="button"
              key={citation.evidence_id}
              onClick={() => onNavigateToPage(citation.source_page)}
            >
              第 {citation.source_page} 页
            </button>
          ))}
        </div>
      )}
      <label htmlFor={`note-${record.id}`}>我的理解</label>
      <textarea
        id={`note-${record.id}`}
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder="写下你核对原文后的理解、疑问或反例……"
        rows={3}
      />
      <label htmlFor={`category-${record.id}`}>进入论文卡片的栏目</label>
      <select
        id={`category-${record.id}`}
        value={category}
        onChange={(event) =>
          setCategory(event.target.value as ReadingCategory)
        }
      >
        {CATEGORY_OPTIONS.map((option) => (
          <option key={option.value} value={option.value}>
            {option.label}
          </option>
        ))}
      </select>
      {saveError && <p className="search-error">{saveError}</p>}
      <div className="history-actions">
        <button
          type="button"
          disabled={isSaving}
          onClick={() => void save(record.confirmed)}
        >
          {isSaving ? "保存中…" : "保存备注"}
        </button>
        {record.confirmed ? (
          <a href={exportReadingRecordUrl(paperId, record.id)} download>
            导出 Markdown
          </a>
        ) : (
          <button
            type="button"
            className="confirm-record"
            disabled={isSaving}
            onClick={() => void save(true)}
          >
            核对完成并确认
          </button>
        )}
      </div>
    </article>
  );
}

export default function AssistantPanel({
  paper,
  selection,
  onClearSelection,
  onNavigateToPage,
}: AssistantPanelProps) {
  const [activeTab, setActiveTab] = useState<AssistantTab>("ask");
  const [question, setQuestion] = useState("");
  const [searchMode, setSearchMode] = useState<SearchMode>("hybrid");
  const [completedSearch, setCompletedSearch] =
    useState<CompletedSearch | null>(null);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [answer, setAnswer] = useState<PaperAnswer | null>(null);
  const [isSearching, setIsSearching] = useState(false);
  const [isAnswering, setIsAnswering] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [history, setHistory] = useState<ReadingRecord[]>([]);
  const [historyError, setHistoryError] = useState<string | null>(null);
  const [cardPreview, setCardPreview] = useState<PaperCardPreview | null>(null);
  const [cardError, setCardError] = useState<string | null>(null);
  const [isPreparingCard, setIsPreparingCard] = useState(false);
  const [isExportingCard, setIsExportingCard] = useState(false);

  useEffect(() => {
    listReadingHistory(paper.id)
      .then(setHistory)
      .catch((reason: unknown) => {
        setHistoryError(
          reason instanceof Error ? reason.message : "阅读记录加载失败。",
        );
      });
  }, [paper.id]);

  const isBusy = isSearching || isAnswering;
  const confirmedRecordCount = history.filter(
    (record) => record.confirmed,
  ).length;

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

  const runSearch = async () => {
    const query = question.trim();
    if (!query || isBusy) {
      return;
    }

    setError(null);
    setIsSearching(true);

    try {
      const searchResults = await searchPaper(
        paper.id,
        query,
        searchMode,
      );
      setResults(searchResults);
      setCompletedSearch({ query, mode: searchMode });
      setActiveTab("evidence");
    } catch (reason: unknown) {
      setError(reason instanceof Error ? reason.message : "证据检索失败。");
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
      );
      setAnswer(paperAnswer);
      setResults(paperAnswer.evidence);
      setCompletedSearch({ query, mode: searchMode });
      setActiveTab("ask");
      setHistory(await listReadingHistory(paper.id));
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
          记录{history.length > 0 ? ` ${history.length}` : ""}
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
      </div>

      {activeTab === "ask" ? (
        <div className="assistant-content">
          <p className="eyebrow">当前论文</p>
          <h2>{paper.name}</h2>
          <p className="assistant-intro">
            系统先在本地检索论文证据，再让 DeepSeek 只根据这些证据回答并标注页码。
          </p>

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
                  {answer.insufficient_evidence ? "证据不足" : "论文回答"}
                </strong>
                <span>{answer.model}</span>
              </div>
              <p className="answer-direct">{answer.answer}</p>
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
                className="use-selection-button"
                onClick={() => setQuestion(selection.text)}
              >
                用这段原文检索
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
      ) : activeTab === "evidence" ? (
        <div className="assistant-content evidence-content">
          <p className="eyebrow">当前论文证据</p>
          {completedSearch ? (
            <>
              <h2>{completedSearch.query}</h2>
              <p className="assistant-intro">
                {completedSearch.mode === "hybrid"
                  ? "混合检索分别排列关键词与语义结果，再融合名次并降低参考文献列表的权重。"
                  : completedSearch.mode === "semantic"
                    ? "语义检索按意思寻找相关段落，分数用于比较本次结果的相对顺序。"
                    : "关键词检索按问题中的词语统计命中次数。"}
              </p>

              {results.length > 0 ? (
                <ol className="evidence-list">
                  {results.map((result, index) => (
                    <li key={`${result.source_page}-${result.chunk_index}-${index}`}>
                      <button
                        type="button"
                        className="evidence-card"
                        onClick={() => onNavigateToPage(result.source_page)}
                      >
                        <span className="evidence-meta">
                          <strong>第 {result.source_page} 页</strong>
                          <span>
                            {scoreLabel(result, completedSearch.mode)}
                          </span>
                        </span>
                        <span className="evidence-text">{result.text}</span>
                        {completedSearch.mode === "hybrid" && (
                          <span className="rank-explanation">
                            {rankExplanation(result)}
                          </span>
                        )}
                        <span className="jump-label">在 PDF 中查看 →</span>
                      </button>
                    </li>
                  ))}
                </ol>
              ) : (
                <div className="empty-conversation">
                  <span>没有找到可用证据</span>
                  <p>换一种问法，或切换关键词与语义检索再试一次。</p>
                </div>
              )}
            </>
          ) : (
            <div className="empty-conversation">
              <span>还没有检索记录</span>
              <p>返回“提问”输入问题，系统会在当前论文内查找证据。</p>
            </div>
          )}
        </div>
      ) : activeTab === "history" ? (
        <div className="assistant-content history-content">
          <p className="eyebrow">本地阅读记录</p>
          <h2>人工确认后再进入正式笔记</h2>
          <p className="assistant-intro">
            AI 回答会自动保存在本机。核对引用、写下自己的理解并确认后，才能导出 Markdown。
          </p>
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
      ) : (
        <div className="assistant-content summary-content">
          <p className="eyebrow">结构化论文卡片</p>
          <h2>只汇总你已确认的理解</h2>
          <p className="assistant-intro">
            当前有 {confirmedRecordCount} 条已确认记录。至少需要 2 条，并先在“记录”中选择它们所属的栏目。
          </p>
          <button
            type="button"
            className="prepare-card-button"
            disabled={confirmedRecordCount < 2 || isPreparingCard}
            onClick={() => void prepareCard()}
          >
            {isPreparingCard ? "正在生成预览…" : "生成卡片预览"}
          </button>
          {cardError && <p className="search-error">{cardError}</p>}
          {cardPreview ? (
            <section className="paper-card-preview">
              <div className="card-preview-heading">
                <strong>Markdown 预览</strong>
                <span>{cardPreview.confirmed_record_count} 条确认记录</span>
              </div>
              <pre>{cardPreview.markdown}</pre>
              {cardPreview.existing_card && (
                <div className="card-diff">
                  <strong>与已有正式卡片的差异</strong>
                  <pre>{cardPreview.diff || "内容没有变化。"}</pre>
                </div>
              )}
              <button
                type="button"
                className="export-card-button"
                disabled={isExportingCard}
                onClick={() => void exportCard()}
              >
                {isExportingCard
                  ? "正在导出…"
                  : cardPreview.existing_card
                    ? "确认差异并导出为新版本"
                    : "确认内容并导出正式卡片"}
              </button>
              <p className="card-safety-note">
                {cardPreview.existing_card
                  ? "原卡片不会被修改；新内容将保存为带时间戳的版本。"
                  : "以后再次导出时会先显示差异，不会覆盖本文件。"}
              </p>
            </section>
          ) : (
            <div className="empty-conversation">
              <span>尚未生成卡片预览</span>
              <p>先确认并分类至少两条阅读记录。</p>
            </div>
          )}
        </div>
      )}

      {activeTab !== "summary" && <form
        className="question-box"
        onSubmit={(event) => {
          event.preventDefault();
          void runAnswer();
        }}
      >
        <label htmlFor="question">向当前论文提问</label>
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
