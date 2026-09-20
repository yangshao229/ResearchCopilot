import { useEffect, useMemo, useState } from "react";
import { Document, Page } from "react-pdf";

import { listPapers, paperFileUrl, type Paper } from "./api";

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

type ReaderProps = {
  paper: Paper;
};

function PdfReader({ paper }: ReaderProps) {
  const [pageNumber, setPageNumber] = useState(() => loadSavedPage(paper.id));
  const [pageCount, setPageCount] = useState(paper.page_count ?? 0);
  const [scale, setScale] = useState(1.1);

  const goToPage = (nextPage: number) => {
    const upperBound = pageCount || paper.page_count || 1;
    setPageNumber(Math.min(Math.max(nextPage, 1), upperBound));
  };

  useEffect(() => {
    window.localStorage.setItem(savedPageKey(paper.id), String(pageNumber));
  }, [paper.id, pageNumber]);

  return (
    <section className="reader" aria-label="PDF 阅读区">
      <header className="reader-toolbar">
        <div className="page-controls">
          <button
            type="button"
            onClick={() => goToPage(pageNumber - 1)}
            disabled={pageNumber <= 1}
          >
            上一页
          </button>
          <label>
            第
            <input
              aria-label="当前页码"
              type="number"
              min="1"
              max={pageCount || undefined}
              value={pageNumber}
              onChange={(event) => goToPage(Number(event.target.value))}
            />
            页
          </label>
          <span className="muted">/ {pageCount || "—"}</span>
          <button
            type="button"
            onClick={() => goToPage(pageNumber + 1)}
            disabled={pageCount > 0 && pageNumber >= pageCount}
          >
            下一页
          </button>
        </div>

        <div className="zoom-controls">
          <button
            type="button"
            aria-label="缩小"
            onClick={() => setScale((value) => Math.max(0.6, value - 0.15))}
          >
            −
          </button>
          <span>{Math.round(scale * 100)}%</span>
          <button
            type="button"
            aria-label="放大"
            onClick={() => setScale((value) => Math.min(2.2, value + 0.15))}
          >
            +
          </button>
        </div>
      </header>

      <div className="document-stage">
        <Document
          file={paperFileUrl(paper.id)}
          loading={<div className="reader-message">正在加载 PDF…</div>}
          error={<div className="reader-message error">PDF 加载失败。</div>}
          onLoadSuccess={({ numPages }) => {
            setPageCount(numPages);
            if (pageNumber > numPages) {
              setPageNumber(numPages);
            }
          }}
        >
          <Page
            pageNumber={pageNumber}
            scale={scale}
            renderTextLayer
            renderAnnotationLayer
          />
        </Document>
      </div>
    </section>
  );
}

type AssistantPanelProps = {
  paper: Paper;
};

function AssistantPanel({ paper }: AssistantPanelProps) {
  const [question, setQuestion] = useState("");

  return (
    <aside className="assistant-panel">
      <div className="assistant-tabs" role="tablist" aria-label="阅读辅助功能">
        <button type="button" className="active" role="tab" aria-selected="true">
          提问
        </button>
        <button type="button" role="tab" aria-selected="false" disabled>
          证据
        </button>
        <button type="button" role="tab" aria-selected="false" disabled>
          笔记
        </button>
        <button type="button" role="tab" aria-selected="false" disabled>
          总结
        </button>
      </div>

      <div className="assistant-content">
        <p className="eyebrow">当前论文</p>
        <h2>{paper.name}</h2>
        <p className="assistant-intro">
          M1 先建立稳定的阅读空间。下一阶段会把选区、检索证据和带页码回答接入这里。
        </p>

        <div className="empty-conversation">
          <span>阅读助手尚未接入模型</span>
          <p>你现在可以先检查 PDF 阅读、翻页、缩放和页码恢复是否符合习惯。</p>
        </div>
      </div>

      <form className="question-box" onSubmit={(event) => event.preventDefault()}>
        <label htmlFor="question">关于这篇论文的问题</label>
        <textarea
          id="question"
          value={question}
          onChange={(event) => setQuestion(event.target.value)}
          placeholder="例如：作者为什么不再使用循环结构？"
          rows={4}
        />
        <button type="submit" disabled title="将在 M3 接入带引用问答">
          下一阶段接入
        </button>
      </form>
    </aside>
  );
}

export default function App() {
  const [papers, setPapers] = useState<Paper[]>([]);
  const [selectedPaperId, setSelectedPaperId] = useState<string | null>(null);
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

  return (
    <main className="app-shell">
      <header className="topbar">
        <div>
          <p className="eyebrow">Local paper workspace</p>
          <h1>ResearchCopilot</h1>
        </div>
        <div className="milestone-badge">M1 · 阅读器外壳</div>
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
                onClick={() => setSelectedPaperId(paper.id)}
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
            <PdfReader key={selectedPaper.id} paper={selectedPaper} />
            <AssistantPanel key={selectedPaper.id} paper={selectedPaper} />
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
