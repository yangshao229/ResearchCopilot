import { useEffect, useRef, useState } from "react";

import {
  exportReadingRecordUrl,
  getVaultDocument,
  getVaultStatus,
  previewVaultReadingNote,
  saveVaultReadingNote,
  type Paper,
  type PaperStructure,
  type ReadingScope,
  type ReadingCategory,
  type ReadingRecord,
  type VaultNotePreview,
  type VaultDocument,
  type VaultNote,
  type SearchMode,
  type ScopePreference,
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
  scopePreference: ScopePreference;
  snapshotToken: string | null;
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
  const [vaultPreview, setVaultPreview] = useState<VaultNotePreview | null>(null);
  const [vaultError, setVaultError] = useState<string | null>(null);
  const [vaultSavedPath, setVaultSavedPath] = useState<string | null>(null);
  const [vaultBusy, setVaultBusy] = useState(false);
  const hasUnsavedChanges = note !== record.personal_note || category !== record.category;

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
    setVaultPreview(null);
    setVaultSavedPath(null);
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

  const prepareVaultNote = async () => {
    setVaultBusy(true);
    setVaultError(null);
    setVaultPreview(null);
    try {
      setVaultPreview(await previewVaultReadingNote(paperId, record.id));
    } catch (reason: unknown) {
      setVaultError(errorMessage(reason, "history.vaultPreviewError"));
    } finally {
      setVaultBusy(false);
    }
  };

  const saveVaultNote = async () => {
    if (!vaultPreview || hasUnsavedChanges) return;
    setVaultBusy(true);
    setVaultError(null);
    try {
      const saved = await saveVaultReadingNote(paperId, record.id, vaultPreview.sha256);
      setVaultSavedPath(saved.path);
      setVaultPreview(null);
      window.dispatchEvent(new Event("research-copilot:vault-changed"));
    } catch (reason: unknown) {
      setVaultError(errorMessage(reason, "history.vaultSaveError"));
      setVaultPreview(null);
    } finally {
      setVaultBusy(false);
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
      {record.confirmed && (
        <section className="paper-card-preview">
          <strong>{t("history.vaultTitle")}</strong>
          <p className="muted">{t("history.vaultHelp")}</p>
          {hasUnsavedChanges && <p className="muted">{t("history.vaultSaveDraftFirst")}</p>}
          <button
            type="button"
            disabled={vaultBusy || isSaving || hasUnsavedChanges}
            onClick={() => void prepareVaultNote()}
          >
            {vaultBusy ? t("history.vaultWorking") : t("history.vaultPreview")}
          </button>
          {vaultError && <p className="search-error">{vaultError}</p>}
          {vaultSavedPath && <p>{t("history.vaultSaved", { path: vaultSavedPath })}</p>}
          {vaultPreview && (
            <div className="card-diff">
              <p>{t("history.vaultTarget", { path: vaultPreview.relative_path })}</p>
              <pre>{vaultPreview.markdown}</pre>
              {vaultPreview.already_exists ? (
                <p>{t("history.vaultAlreadyExists")}</p>
              ) : (
                <button
                  type="button"
                  disabled={vaultBusy || hasUnsavedChanges}
                  onClick={() => void saveVaultNote()}
                >
                  {t("history.vaultConfirmSave")}
                </button>
              )}
            </div>
          )}
        </section>
      )}
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
          {!completedSearch.snapshotToken && (
            <p className="outline-warning" role="status">
              {t("evidence.unverifiedSnapshot")}
            </p>
          )}
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
  paper: Paper;
  confirmedRecordCount: number;
  cardPreview: VaultNotePreview | null;
  cardError: string | null;
  cardSavedPath: string | null;
  isPreparingCard: boolean;
  isSavingCard: boolean;
  onPrepare: () => void;
  onSave: () => void;
};

export function SummaryView({
  paper,
  confirmedRecordCount,
  cardPreview,
  cardError,
  cardSavedPath,
  isPreparingCard,
  isSavingCard,
  onPrepare,
  onSave,
}: SummaryViewProps) {
  const { t, errorMessage } = useI18n();
  const [savedNotes, setSavedNotes] = useState<VaultNote[]>([]);
  const [vaultConnected, setVaultConnected] = useState(false);
  const [selectedDocument, setSelectedDocument] = useState<VaultDocument | null>(null);
  const [readError, setReadError] = useState<string | null>(null);
  const [isReading, setIsReading] = useState(false);
  const requestId = useRef(0);

  useEffect(() => {
    const refresh = () => {
      const currentRequest = ++requestId.current;
      setSelectedDocument(null);
      setReadError(null);
      setIsReading(false);
      void getVaultStatus().then((status) => {
        if (currentRequest !== requestId.current) return;
        setVaultConnected(status.connected);
        setSavedNotes(status.notes.filter((note) => note.paper_uid === paper.paper_uid));
      }).catch((reason: unknown) => {
        if (currentRequest === requestId.current) setReadError(errorMessage(reason, "vault.loadError"));
      });
    };
    refresh();
    window.addEventListener("research-copilot:vault-changed", refresh);
    return () => {
      requestId.current += 1;
      window.removeEventListener("research-copilot:vault-changed", refresh);
    };
  }, [paper.id, paper.paper_uid]);

  const readSavedNote = async (uid: string) => {
    const currentRequest = ++requestId.current;
    setSelectedDocument(null);
    setReadError(null);
    setIsReading(true);
    try {
      const document = await getVaultDocument(paper.id, uid);
      if (currentRequest === requestId.current) setSelectedDocument(document);
    } catch (reason: unknown) {
      if (currentRequest === requestId.current) setReadError(errorMessage(reason, "summary.readError"));
    } finally {
      if (currentRequest === requestId.current) setIsReading(false);
    }
  };

  const refreshSavedNotes = async () => {
    const currentRequest = ++requestId.current;
    setSelectedDocument(null);
    setReadError(null);
    setIsReading(false);
    try {
      const status = await getVaultStatus();
      if (currentRequest !== requestId.current) return;
      setVaultConnected(status.connected);
      setSavedNotes(status.notes.filter((note) => note.paper_uid === paper.paper_uid));
    } catch (reason: unknown) {
      if (currentRequest === requestId.current) setReadError(errorMessage(reason, "vault.loadError"));
    }
  };
  return (
    <div className="assistant-content summary-content">
      <p className="eyebrow">{t("summary.eyebrow")}</p>
      <h2>{t("summary.title")}</h2>
      <p className="assistant-intro">
        {t("summary.intro", { count: confirmedRecordCount })}
      </p>
      {paper.pdf_version_status === "changed" && (
        <p className="search-error">{t("summary.changedPdf")}</p>
      )}
      <button
        type="button"
        className="prepare-card-button"
        disabled={isPreparingCard || isSavingCard}
        onClick={onPrepare}
      >
        {isPreparingCard ? t("summary.preparing") : t("summary.prepare")}
      </button>
      {cardError && <p className="search-error">{cardError}</p>}
      {cardSavedPath && <p>{t("summary.saved", { path: cardSavedPath })}</p>}
      {cardPreview ? (
        <section className="paper-card-preview">
          <div className="card-preview-heading">
            <strong>{t("summary.markdownPreview")}</strong>
            <span>{t("summary.target", { path: cardPreview.relative_path })}</span>
          </div>
          <pre>{cardPreview.markdown}</pre>
          {cardPreview.already_exists ? (
            <p className="card-safety-note">{t("summary.alreadyExists")}</p>
          ) : (
            <button
              type="button"
              className="export-card-button"
              disabled={isSavingCard}
              onClick={onSave}
            >
              {isSavingCard ? t("summary.saving") : t("summary.save")}
            </button>
          )}
          <p className="card-safety-note">{t("summary.safety")}</p>
        </section>
      ) : (
        <div className="empty-conversation">
          <span>{t("summary.emptyTitle")}</span>
          <p>{t("summary.emptyBody")}</p>
        </div>
      )}
      <section className="vault-readback">
        <div className="card-preview-heading">
          <strong>{t("summary.savedKnowledge")}</strong>
          <button type="button" onClick={() => void refreshSavedNotes()}>
            {t("summary.reload")}
          </button>
        </div>
        {!vaultConnected ? (
          <p className="muted">{t("summary.notConnected")}</p>
        ) : savedNotes.length === 0 ? (
          <p className="muted">{t("summary.noSavedNotes")}</p>
        ) : (
          <ul className="vault-notes">
            {savedNotes.map((note) => (
              <li key={note.uid}>
                <button
                  type="button"
                  disabled={isReading}
                  onClick={() => void readSavedNote(note.uid)}
                >
                  {note.kind === "paper" ? t("summary.paperCard") : t("summary.readingNote")}: {note.title}
                </button>
              </li>
            ))}
          </ul>
        )}
        {isReading && <p className="muted">{t("summary.loadingNote")}</p>}
        {readError && <p className="search-error">{readError}</p>}
        {selectedDocument && (
          <div className="paper-card-preview">
            <p className="muted">{t("summary.readOnly", {
              path: selectedDocument.note.path,
              digest: selectedDocument.sha256.slice(0, 12),
            })}</p>
            <pre>{selectedDocument.markdown}</pre>
          </div>
        )}
      </section>
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
