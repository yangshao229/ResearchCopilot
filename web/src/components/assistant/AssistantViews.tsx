import { useState } from "react";

import {
  exportReadingRecordUrl,
  type Paper,
  type PaperCardPreview,
  type PaperStructure,
  type ReadingScope,
  type ReadingCategory,
  type ReadingRecord,
  type SearchMode,
  type SearchResult,
  updateReadingRecord,
} from "../../api";
import { useI18n } from "../../i18n-context";
import { scopeStatus } from "../../ui-status";
import type { MessageKey, MessageParams } from "../../i18n";

type Translator = (key: MessageKey, params?: MessageParams) => string;

function categoryOptions(t: Translator): Array<{ value: ReadingCategory; label: string }> {
  return [
    { value: "unclassified", label: t("history.categoryUnclassified") },
    { value: "summary", label: t("history.categorySummary") },
    { value: "research_problem", label: t("history.categoryResearchProblem") },
    { value: "method", label: t("history.categoryMethod") },
    { value: "experiments", label: t("history.categoryExperiments") },
    { value: "contributions", label: t("history.categoryContributions") },
    { value: "limitations", label: t("history.categoryLimitations") },
    { value: "open_questions", label: t("history.categoryOpenQuestions") },
  ];
}

export type CompletedSearch = {
  query: string;
  mode: SearchMode;
  scope: ReadingScope;
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
  const { t, locale, errorMessage } = useI18n();
  const [note, setNote] = useState(record.personal_note);
  const [category, setCategory] = useState<ReadingCategory>(record.category);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  const save = async (confirmed: boolean) => {
    if (confirmed && !note.trim()) {
      setSaveError(t("history.noteRequired"));
      return;
    }
    if (confirmed && category === "unclassified") {
      setSaveError(t("history.categoryRequired"));
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
      setSaveError(errorMessage(reason, "history.errorSave"));
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <article className={record.confirmed ? "history-card confirmed" : "history-card"}>
      <div className="history-heading">
        <span>
          {record.confirmed ? t("history.confirmed") : t("history.draft")}
        </span>
        <time dateTime={record.created_at}>
          {new Date(record.created_at).toLocaleString(locale)}
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
              {t("history.page", { page: citation.source_page })}
            </button>
          ))}
        </div>
      )}
      <label htmlFor={`note-${record.id}`}>{t("history.myUnderstanding")}</label>
      <textarea
        id={`note-${record.id}`}
        value={note}
        onChange={(event) => setNote(event.target.value)}
        placeholder={t("history.notePlaceholder")}
        rows={3}
      />
      <label htmlFor={`category-${record.id}`}>{t("history.categoryLabel")}</label>
      <select
        id={`category-${record.id}`}
        value={category}
        onChange={(event) => setCategory(event.target.value as ReadingCategory)}
      >
        {categoryOptions(t).map((option) => (
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
          {isSaving ? t("history.saving") : t("history.saveDraft")}
        </button>
        {record.confirmed ? (
          <a href={exportReadingRecordUrl(paperId, record.id)} download>
            {t("history.exportMarkdown")}
          </a>
        ) : (
          <button
            type="button"
            className="confirm-record"
            disabled={isSaving}
            onClick={() => void save(true)}
          >
            {t("history.confirm")}
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
  const { t, language } = useI18n();
  return (
    <div className="assistant-content outline-content">
      <p className="eyebrow">{t("outline.eyebrow")}</p>
      <h2>{t("outline.title")}</h2>
      {isLoading ? (
        <div className="empty-conversation"><span>{t("outline.loading")}</span></div>
      ) : error ? (
        <p className="search-error">{error}</p>
      ) : structure && structure.sections.length > 0 ? (
        <>
          <div className="outline-status">
            <strong>
              {structure.method === "bookmarks"
                ? t("outline.bookmarks")
                : t("outline.heuristic")}
            </strong>
            <span>{t("outline.headingCount", { count: structure.sections.length })}</span>
          </div>
          {structure.warnings.map((warning) => (
            <p className="outline-warning" key={warning}>{warning}</p>
          ))}
          <nav className="paper-outline" aria-label={t("outline.aria")}>
            {structure.sections.map((section, index) => (
              <button
                type="button"
                key={`${section.source_page}-${section.title}-${index}`}
                style={{ paddingLeft: `${12 + (section.level - 1) * 16}px` }}
                onClick={() => onNavigateToPage(section.source_page)}
              >
                <span>{section.title}</span>
                <small>{t("outline.page", { page: section.source_page })}</small>
              </button>
            ))}
          </nav>
        </>
      ) : (
        <div className="empty-conversation">
          <span>{t("outline.unavailableTitle")}</span>
          <p>{structure?.warnings[0] && language === "zh-CN"
            ? structure.warnings[0]
            : t("outline.unavailableBody")}</p>
        </div>
      )}
    </div>
  );
}

function scoreLabel(t: Translator, result: SearchResult, mode: SearchMode): string {
  if (mode === "keyword") return t("evidence.keywordScore", { score: result.score });
  if (mode === "hybrid") {
    return t("evidence.hybridScore", { score: result.rerank_score.toFixed(4) });
  }
  return t("evidence.semanticScore", { score: result.score.toFixed(4) });
}

function rankExplanation(t: Translator, result: SearchResult): string {
  const ranks = [];
  if (result.keyword_rank > 0) {
    ranks.push(t("evidence.keywordRank", { rank: result.keyword_rank }));
  }
  if (result.semantic_rank > 0) {
    ranks.push(t("evidence.semanticRank", { rank: result.semantic_rank }));
  }
  if (result.reference_penalty > 0) ranks.push(t("evidence.referencePenalty"));
  return ranks.join(" · ");
}

type EvidenceViewProps = {
  completedSearch: CompletedSearch | null;
  results: SearchResult[];
  onUseFullPaper: () => void;
  onNavigateToPage: (pageNumber: number) => void;
};

export function EvidenceView({
  completedSearch,
  results,
  onUseFullPaper,
  onNavigateToPage,
}: EvidenceViewProps) {
  const { t, language } = useI18n();
  return (
    <div className="assistant-content evidence-content">
      <p className="eyebrow">{t("evidence.eyebrow")}</p>
      {completedSearch ? (
        <>
          <h2>{completedSearch.query}</h2>
          <p className="assistant-intro">
            {completedSearch.mode === "hybrid"
              ? t("evidence.hybridHelp")
              : completedSearch.mode === "semantic"
                ? t("evidence.semanticHelp")
                : t("evidence.keywordHelp")}
          </p>
          <p className="outline-warning" role="status">
            {scopeStatus(completedSearch.scope, language, t)}
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
                      <strong>{t("evidence.page", { page: result.source_page })}</strong>
                      <span>{scoreLabel(t, result, completedSearch.mode)}</span>
                    </span>
                    <span className="evidence-text">{result.text}</span>
                    {completedSearch.mode === "hybrid" && (
                      <span className="rank-explanation">{rankExplanation(t, result)}</span>
                    )}
                    <span className="jump-label">{t("evidence.viewInPdf")}</span>
                  </button>
                </li>
              ))}
            </ol>
          ) : (
            <div className="empty-conversation">
              <span>{t("evidence.emptyTitle")}</span>
              <p>
                {completedSearch.scope.kind === "section"
                  ? t("evidence.emptySection")
                  : t("evidence.emptyFull")}
              </p>
              {completedSearch.scope.kind === "section" && (
                <button type="button" onClick={onUseFullPaper}>
                  {t("evidence.useFullPaper")}
                </button>
              )}
            </div>
          )}
        </>
      ) : (
        <div className="empty-conversation">
          <span>{t("evidence.noSearchTitle")}</span>
          <p>{t("evidence.noSearchBody")}</p>
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
  const { t } = useI18n();
  return (
    <div className="assistant-content summary-content">
      <p className="eyebrow">{t("summary.eyebrow")}</p>
      <h2>{t("summary.title")}</h2>
      <p className="assistant-intro">
        {t("summary.intro", { count: confirmedRecordCount })}
      </p>
      <button
        type="button"
        className="prepare-card-button"
        disabled={confirmedRecordCount < 2 || isPreparingCard}
        onClick={onPrepare}
      >
        {isPreparingCard ? t("summary.preparing") : t("summary.prepare")}
      </button>
      {cardError && <p className="search-error">{cardError}</p>}
      {cardPreview ? (
        <section className="paper-card-preview">
          <div className="card-preview-heading">
            <strong>{t("summary.markdownPreview")}</strong>
            <span>{t("summary.confirmedCount", { count: cardPreview.confirmed_record_count })}</span>
          </div>
          <pre>{cardPreview.markdown}</pre>
          {cardPreview.existing_card && (
            <div className="card-diff">
              <strong>{t("summary.diff")}</strong>
              <pre>{cardPreview.diff || t("summary.noChanges")}</pre>
            </div>
          )}
          <button
            type="button"
            className="export-card-button"
            disabled={isExportingCard}
            onClick={onExport}
          >
            {isExportingCard
              ? t("summary.exporting")
              : cardPreview.existing_card
                ? t("summary.exportVersion")
                : t("summary.exportCard")}
          </button>
          <p className="card-safety-note">
            {cardPreview.existing_card
              ? t("summary.versionSafety")
              : t("summary.firstExportSafety")}
          </p>
        </section>
      ) : (
        <div className="empty-conversation">
          <span>{t("summary.emptyTitle")}</span>
          <p>{t("summary.emptyBody")}</p>
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
  const { t } = useI18n();
  return (
    <div className="assistant-content info-content">
      <p className="eyebrow">{t("info.eyebrow")}</p>
      <h2>{paper.name}</h2>
      <dl>
        <div><dt>{t("info.pdfPages")}</dt><dd>{paper.page_count ?? t("info.readFailed")}</dd></div>
        <div><dt>{t("info.localPath")}</dt><dd>data/raw/{paper.relative_path}</dd></div>
        <div><dt>{t("info.aiScope")}</dt><dd>{t("info.aiScopeValue")}</dd></div>
        <div><dt>{t("info.noteStatus")}</dt><dd>{t("info.confirmedRecords", { count: confirmedRecordCount })}</dd></div>
      </dl>
    </div>
  );
}
