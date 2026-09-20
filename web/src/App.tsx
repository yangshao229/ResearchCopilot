import { useEffect, useMemo, useState } from "react";

import { listPapers, type Paper } from "./api";
import AssistantPanel from "./components/AssistantPanel";
import PdfReader, { type PdfSelection } from "./components/PdfReader";


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
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
  const [pagesByPaper, setPagesByPaper] = useState<Record<string, number>>({});
  const [selection, setSelection] = useState<PdfSelection | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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
        setError(reason instanceof Error ? reason.message : "论文列表加载失败。");
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
  };

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local paper workspace</p>
          <h1>ResearchCopilot</h1>
        </div>
        <div className="milestone-badge">M2 · 问题到证据</div>
      </header>

      <div className="workspace">
        <aside className="library-panel">
          <div className="panel-heading">
            <p className="eyebrow">本地资料库</p>
            <h2>论文</h2>
            <span>{papers.length} 篇</span>
          </div>

          {isLoading && <p className="muted panel-message">正在扫描论文…</p>}
          {error && <p className="error panel-message">{error}</p>}
          {!isLoading && !error && papers.length === 0 && (
            <div className="panel-message empty-library">
              <strong>还没有本地论文</strong>
              <p>将 PDF 放入 data/raw 后刷新页面。</p>
            </div>
          )}

          <nav className="paper-list" aria-label="本地论文">
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
                      ? "页数读取失败"
                      : `${paper.page_count} 页`}
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
            />
            <AssistantPanel
              key={selectedPaper.id}
              paper={selectedPaper}
              selection={selection}
              onClearSelection={() => setSelection(null)}
              onNavigateToPage={changePage}
            />
          </>
        ) : (
          <section className="welcome-state">
            <h2>导入第一篇论文开始阅读</h2>
            <p>ResearchCopilot 会保留 PDF 原文和真实页码。</p>
          </section>
        )}
      </div>
    </main>
  );
}
