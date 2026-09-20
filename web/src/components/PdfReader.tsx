import { useEffect, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Document, Page } from "react-pdf";

import { paperFileUrl, type Paper } from "../api";


export type PdfSelection = {
  text: string;
  sourcePage: number;
};

type PdfReaderProps = {
  paper: Paper;
  pageNumber: number;
  onPageChange: (pageNumber: number) => void;
  onTextSelection: (selection: PdfSelection) => void;
};

export default function PdfReader({
  paper,
  pageNumber,
  onPageChange,
  onTextSelection,
}: PdfReaderProps) {
  const [pageCount, setPageCount] = useState(paper.page_count ?? 0);
  const [scale, setScale] = useState(1.1);

  useEffect(() => {
    setPageCount(paper.page_count ?? 0);
    setScale(1.1);
  }, [paper.id, paper.page_count]);

  const goToPage = (nextPage: number) => {
    const upperBound = pageCount || paper.page_count || 1;
    onPageChange(Math.min(Math.max(nextPage, 1), upperBound));
  };

  const captureTextSelection = (event: ReactMouseEvent<HTMLDivElement>) => {
    const selection = window.getSelection();
    if (!selection || selection.isCollapsed || selection.rangeCount === 0) {
      return;
    }

    const range = selection.getRangeAt(0);
    if (!event.currentTarget.contains(range.commonAncestorContainer)) {
      return;
    }

    const text = selection.toString().replace(/\s+/g, " ").trim();
    if (text) {
      onTextSelection({
        text,
        sourcePage: pageNumber,
      });
    }
  };

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

        <span className="selection-hint">选择原文可发送到右侧</span>

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

      <div className="document-stage" onMouseUp={captureTextSelection}>
        <Document
          file={paperFileUrl(paper.id)}
          loading={<div className="reader-message">正在加载 PDF…</div>}
          error={<div className="reader-message error">PDF 加载失败。</div>}
          onLoadSuccess={({ numPages }) => {
            setPageCount(numPages);
            if (pageNumber > numPages) {
              onPageChange(numPages);
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
