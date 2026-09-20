import { useState } from "react";

import {
  answerPaper,
  searchPaper,
  type Paper,
  type PaperAnswer,
  type SearchMode,
  type SearchResult,
} from "../api";
import type { PdfSelection } from "./PdfReader";


type AssistantTab = "ask" | "evidence";

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

  const isBusy = isSearching || isAnswering;

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
        <button type="button" role="tab" aria-selected="false" disabled>
          笔记
        </button>
        <button type="button" role="tab" aria-selected="false" disabled>
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
      ) : (
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
      )}

      <form
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
      </form>
    </aside>
  );
}
