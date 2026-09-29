import { useEffect, useMemo, useState } from "react";

import { importPaper, listPapers, type PageLayout, type PageSourceRegion, type Paper } from "./api";
import AssistantPanel from "./components/AssistantPanel";
import PdfReader, { type FocusedSourceRegion, type PdfSelection } from "./components/PdfReader";
import { useI18n, type UiLanguage } from "./i18n-context";


const SELECTED_PAPER_KEY = "research-copilot:selected-paper";

function savedPageKey(paperId: string): string {
  return `research-copilot:page:${paperId}`;
}

function loadSavedPage(paperId: string): number {
  const value = Number.parseInt(
    window.localStorage.getItem(savedPageKey(paperId)) ?? "1",
    10,
  );
  return Number.isFinite(value) && value > 0 ? value : 1;
}

export default function App() {
  const { language, setLanguage, t, errorMessage } = useI18n();
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [pagesByPaper, setPagesByPaper] = useState<Record<string, number>>({});
  const [selection, setSelection] = useState<PdfSelection | null>(null);
  const [focusedSourceRegion, setFocusedSourceRegion] = useState<FocusedSourceRegion | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [isImporting, setIsImporting] = useState(false);
  const [importMessage, setImportMessage] = useState<string | null>(null);
  const [libraryOpen, setLibraryOpen] = useState(
    () => window.innerWidth > 1050,
  );
  const [assistantOpen, setAssistantOpen] = useState(
    () => window.innerWidth > 720,
  );

  useEffect(() => {
    listPapers()
      .then((loadedPapers) => {
        setPapers(loadedPapers);
        const previousPaper = window.localStorage.getItem(SELECTED_PAPER_KEY);
        const selectedPaper = loadedPapers.find(
          (paper) => paper.id === previousPaper,
        );
        setSelectedPaperId(selectedPaper?.id ?? loadedPapers[0]?.id ?? null);
      })
      .catch((reason: unknown) => {
        setError(errorMessage(reason, "app.errorPaperList"));
      })
      .finally(() => setIsLoading(false));
  }, []);

  useEffect(() => {
    if (selectedPaperId) {
      window.localStorage.setItem(SELECTED_PAPER_KEY, selectedPaperId);
    }
  }, [selectedPaperId]);

  const selectedPaper = useMemo(
    () => papers.find((paper) => paper.id === selectedPaperId) ?? null,
    [papers, selectedPaperId],
  );

  const pageNumber = selectedPaper
    ? (pagesByPaper[selectedPaper.id] ?? loadSavedPage(selectedPaper.id))
    : 1;

  const changePage = (nextPage: number) => {
    if (!selectedPaper) {
      return;
    }

    setFocusedSourceRegion((current) =>
      current?.paperId === selectedPaper.id && current.source_page === nextPage
        ? current
        : null,
    );

    setPagesByPaper((currentPages) => ({
      ...currentPages,
      [selectedPaper.id]: nextPage,
    }));
    window.localStorage.setItem(
      savedPageKey(selectedPaper.id),
      String(nextPage),
    );
  };

  const choosePaper = (paperId: string) => {
    setSelectedPaperId(paperId);
    setSelection(null);
    setFocusedSourceRegion(null);
  };

  const focusSourceRegion = (layout: PageLayout, region: PageSourceRegion) => {
    if (!selectedPaper) return;
    changePage(region.source_page);
    setFocusedSourceRegion({
      ...region,
      paperId: selectedPaper.id,
      pageWidth: layout.page_width,
      pageHeight: layout.page_height,
    });
  };

  const handlePdfImport = async (file: File | undefined) => {
    if (!file || isImporting) {
      return;
    }

    setIsImporting(true);
    setError(null);
    setImportMessage(null);
    try {
      const result = await importPaper(file);
      const loadedPapers = await listPapers();
      setPapers(loadedPapers);
      setSelectedPaperId(result.paper.id);
      setSelection(null);
      setFocusedSourceRegion(null);
      setLibraryOpen(true);
      setImportMessage(
        result.imported ? t("app.importSuccess") : t("app.importDuplicate"),
      );
    } catch (reason: unknown) {
      setError(errorMessage(reason, "app.errorImportPdf"));
    } finally {
      setIsImporting(false);
    }
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">{t("app.workspaceEyebrow")}</p>
          <h1>ResearchCopilot</h1>
        </div>
        <div className="topbar-actions">
          <button type="button" onClick={() => setLibraryOpen((open) => !open)}>
            {libraryOpen ? t("app.collapseLibrary") : t("app.openLibrary")}
          </button>
          <button
            type="button"
            disabled={!selectedPaper}
            onClick={() => setAssistantOpen((open) => !open)}
          >
            {assistantOpen ? t("app.collapseAssistant") : t("app.openAssistant")}
          </button>
          <label className="ui-language-picker">
            <span>{t("app.interfaceLanguage")}</span>
            <select
              aria-label={t("app.interfaceLanguage")}
              value={language}
              onChange={(event) => setLanguage(event.target.value as UiLanguage)}
            >
              <option value="zh-CN">{t("app.languageChinese")}</option>
              <option value="en">{t("app.languageEnglish")}</option>
            </select>
          </label>
          <div className="milestone-badge">{t("app.milestone")}</div>
        </div>
      </header>

      <div
        className={`workspace${libraryOpen ? "" : " library-collapsed"}${
          assistantOpen ? "" : " assistant-collapsed"
        }`}
      >
        <aside className="library-panel">
          <div className="panel-heading">
            <p className="eyebrow">{t("app.libraryEyebrow")}</p>
            <h2>{t("app.papers")}</h2>
            <span>{t("app.paperCount", { count: papers.length })}</span>
          </div>

          <label className="import-paper-button">
            <input
              type="file"
              accept="application/pdf,.pdf"
              disabled={isImporting}
              onChange={(event) => {
                void handlePdfImport(event.target.files?.[0]);
                event.currentTarget.value = "";
              }}
            />
            {isImporting ? t("app.importing") : t("app.importPdf")}
          </label>
          {importMessage && <p className="import-message">{importMessage}</p>}

          {isLoading && <p className="muted panel-message">{t("app.scanning")}</p>}
          {error && <p className="error panel-message">{error}</p>}
          {!isLoading && !error && papers.length === 0 && (
            <div className="panel-message empty-library">
              <strong>{t("app.emptyLibraryTitle")}</strong>
              <p>{t("app.emptyLibraryBody")}</p>
            </div>
          )}

          <nav className="paper-list" aria-label={t("app.localPapersAria")}>
            {papers.map((paper) => (
              <button
                type="button"
                key={paper.id}
                className={paper.id === selectedPaperId ? "selected" : ""}
                onClick={() => choosePaper(paper.id)}
              >
                <span className="paper-icon">PDF</span>
                <span className="paper-details">
                  <strong>{paper.name}</strong>
                  <small>
                    {paper.page_count === null
                      ? t("app.pageCountFailed")
                      : t("app.pageCount", { count: paper.page_count })}
                  </small>
                </span>
              </button>
            ))}
          </nav>
        </aside>

        {selectedPaper ? (
          <>
            <PdfReader
              paper={selectedPaper}
              pageNumber={pageNumber}
              onPageChange={changePage}
              onTextSelection={setSelection}
              focusedSourceRegion={focusedSourceRegion}
            />
            {assistantOpen && (
              <AssistantPanel
                key={selectedPaper.id}
                paper={selectedPaper}
                pageNumber={pageNumber}
                selection={selection}
                onClearSelection={() => setSelection(null)}
                onNavigateToPage={changePage}
                onFocusSourceRegion={focusSourceRegion}
              />
            )}
          </>
        ) : (
          <section className="welcome-state">
            <h2>{t("app.welcomeTitle")}</h2>
            <p>{t("app.welcomeBody")}</p>
          </section>
        )}
      </div>
    </main>
  );
}
