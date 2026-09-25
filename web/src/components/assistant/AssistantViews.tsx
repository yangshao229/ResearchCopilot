import { useState } from "react";

import {
  exportReadingRecordUrl,
  type Paper,
  type PaperCardPreview,
  type PaperStructure,
  type ReadingCategory,
  type ReadingRecord,
  type SearchMode,
  type SearchResult,
  updateReadingRecord,
} from "../../api";

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

export type CompletedSearch = {
  query: string;
  mode: SearchMode;
};

type HistoryCardProps = {
  paperId: string;
  record: ReadingRecord;
  onNavigateToPage: (pageNumber: number) => void;
  onSaved: (record: ReadingRecord) => void;
};

export function HistoryCard({
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
    if (confirmed && !note.trim()) {
      setSaveError("请先写下你核对原文后的个人理解。");
      return;
    }
    if (confirmed && category === "unclassified") {
      setSaveError("请选择这条记录进入论文卡片的栏目。");
      return;
    }

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
        <span>{record.confirmed ? "已加入论文卡片" : "AI 草稿 · 待核对"}</span>
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
        placeholder="必填：用自己的话写下理解、疑问或反例……"
        rows={3}
      />
      <label htmlFor={`category-${record.id}`}>进入论文卡片的栏目</label>
      <select
        id={`category-${record.id}`}
        value={category}
        onChange={(event) => setCategory(event.target.value as ReadingCategory)}
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
          {isSaving ? "保存中…" : "保存草稿"}
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
            核对完成，加入论文卡片
          </button>
        )}
      </div>
    </article>
  );
}

type OutlineViewProps = {
  structure: PaperStructure | null;
  error: string | null;
  isLoading: boolean;
  onNavigateToPage: (pageNumber: number) => void;
};

export function OutlineView({
  structure,
  error,
  isLoading,
  onNavigateToPage,
}: OutlineViewProps) {
  return (
    <div className="assistant-content outline-content">
      <p className="eyebrow">当前论文目录</p>
      <h2>点击标题跳到 PDF 原文</h2>
      {isLoading ? (
        <div className="empty-conversation"><span>正在读取目录…</span></div>
      ) : error ? (
        <p className="search-error">{error}</p>
      ) : structure && structure.sections.length > 0 ? (
        <>
          <div className="outline-status">
            <strong>
              {structure.method === "bookmarks" ? "PDF 自带目录" : "规则推断目录"}
            </strong>
            <span>{structure.sections.length} 个标题</span>
          </div>
          {structure.warnings.map((warning) => (
            <p className="outline-warning" key={warning}>{warning}</p>
          ))}
          <nav className="paper-outline" aria-label="论文目录">
            {structure.sections.map((section, index) => (
              <button
                type="button"
                key={`${section.source_page}-${section.title}-${index}`}
                style={{ paddingLeft: `${12 + (section.level - 1) * 16}px` }}
                onClick={() => onNavigateToPage(section.source_page)}
              >
                <span>{section.title}</span>
                <small>第 {section.source_page} 页</small>
              </button>
            ))}
          </nav>
        </>
      ) : (
        <div className="empty-conversation">
          <span>无法可靠识别目录</span>
          <p>{structure?.warnings[0] ?? "这篇 PDF 没有可用书签，也没有清晰的编号标题。"}</p>
        </div>
      )}
    </div>
  );
}

function scoreLabel(result: SearchResult, mode: SearchMode): string {
  if (mode === "keyword") return `命中 ${result.score} 次`;
  if (mode === "hybrid") return `重排分 ${result.rerank_score.toFixed(4)}`;
  return `相似度 ${result.score.toFixed(4)}`;
}

function rankExplanation(result: SearchResult): string {
  const ranks = [];
  if (result.keyword_rank > 0) ranks.push(`关键词 #${result.keyword_rank}`);
  if (result.semantic_rank > 0) ranks.push(`语义 #${result.semantic_rank}`);
  if (result.reference_penalty > 0) ranks.push("已降低参考文献权重");
  return ranks.join(" · ");
}

type EvidenceViewProps = {
  completedSearch: CompletedSearch | null;
  results: SearchResult[];
  onNavigateToPage: (pageNumber: number) => void;
};

export function EvidenceView({
  completedSearch,
  results,
  onNavigateToPage,
}: EvidenceViewProps) {
  return (
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
                      <span>{scoreLabel(result, completedSearch.mode)}</span>
                    </span>
                    <span className="evidence-text">{result.text}</span>
                    {completedSearch.mode === "hybrid" && (
                      <span className="rank-explanation">{rankExplanation(result)}</span>
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
  );
}

type SummaryViewProps = {
  confirmedRecordCount: number;
  cardPreview: PaperCardPreview | null;
  cardError: string | null;
  isPreparingCard: boolean;
  isExportingCard: boolean;
  onPrepare: () => void;
  onExport: () => void;
};

export function SummaryView({
  confirmedRecordCount,
  cardPreview,
  cardError,
  isPreparingCard,
  isExportingCard,
  onPrepare,
  onExport,
}: SummaryViewProps) {
  return (
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
        onClick={onPrepare}
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
            onClick={onExport}
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
  );
}

export function InfoView({
  paper,
  confirmedRecordCount,
}: {
  paper: Paper;
  confirmedRecordCount: number;
}) {
  return (
    <div className="assistant-content info-content">
      <p className="eyebrow">当前论文信息</p>
      <h2>{paper.name}</h2>
      <dl>
        <div><dt>PDF 页数</dt><dd>{paper.page_count ?? "读取失败"}</dd></div>
        <div><dt>本地位置</dt><dd>data/raw/{paper.relative_path}</dd></div>
        <div><dt>AI 数据范围</dt><dd>仅发送问题和最多 5 段检索证据，不上传整篇 PDF。</dd></div>
        <div><dt>笔记状态</dt><dd>{confirmedRecordCount} 条记录已加入论文卡片</dd></div>
      </dl>
    </div>
  );
}
