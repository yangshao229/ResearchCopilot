import { useEffect, useRef, useState } from "react";
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
  const [fitWidth, setFitWidth] = useState(true);
  const [continuous, setContinuous] = useState(true);
  const [stageWidth, setStageWidth] = useState(0);
  const stageRef = useRef<HTMLDivElement | null>(null);
  const pageElements = useRef(new Map<number, HTMLDivElement>());
  const pageChangeCameFromScroll = useRef(false);
  const programmaticTargetPage = useRef<number | null>(null);

  useEffect(() => {
    setPageCount(paper.page_count ?? 0);
    setScale(1.1);
    setFitWidth(true);
    setContinuous(true);
    pageElements.current.clear();
  }, [paper.id, paper.page_count]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage) {
      return;
    }

    const resizeObserver = new ResizeObserver(([entry]) => {
      setStageWidth(entry.contentRect.width);
    });
    resizeObserver.observe(stage);
    return () => resizeObserver.disconnect();
  }, []);

  useEffect(() => {
    if (!continuous || pageChangeCameFromScroll.current) {
      pageChangeCameFromScroll.current = false;
      return;
    }
    const targetElement = pageElements.current.get(pageNumber);
    if (targetElement) {
      programmaticTargetPage.current = pageNumber;
      targetElement.scrollIntoView({ block: "start" });
    }
  }, [continuous, pageNumber]);

  useEffect(() => {
    const stage = stageRef.current;
    if (!stage || !continuous) {
      return;
    }

    let animationFrame = 0;
    const updateVisiblePage = () => {
      animationFrame = 0;
      const stageTop = stage.getBoundingClientRect().top;
      const programmaticTarget = programmaticTargetPage.current;
      if (programmaticTarget !== null) {
        const targetElement = pageElements.current.get(programmaticTarget);
        const targetDistance = targetElement
          ? Math.abs(targetElement.getBoundingClientRect().top - stageTop - 18)
          : Number.POSITIVE_INFINITY;
        if (targetDistance > 32) {
          return;
        }
        programmaticTargetPage.current = null;
      }
      let closestPage = pageNumber;
      let closestDistance = Number.POSITIVE_INFINITY;
      for (const [candidatePage, element] of pageElements.current) {
        const distance = Math.abs(element.getBoundingClientRect().top - stageTop - 18);
        if (distance < closestDistance) {
          closestDistance = distance;
          closestPage = candidatePage;
        }
      }
      if (closestPage !== pageNumber) {
        pageChangeCameFromScroll.current = true;
        onPageChange(closestPage);
      }
    };
    const handleScroll = () => {
      if (!animationFrame) {
        animationFrame = window.requestAnimationFrame(updateVisiblePage);
      }
    };
    stage.addEventListener("scroll", handleScroll, { passive: true });
    return () => {
      stage.removeEventListener("scroll", handleScroll);
      if (animationFrame) {
        window.cancelAnimationFrame(animationFrame);
      }
    };
  }, [continuous, onPageChange, pageNumber]);

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
      const selectionNode =
        range.commonAncestorContainer instanceof Element
          ? range.commonAncestorContainer
          : range.commonAncestorContainer.parentElement;
      const pageElement = selectionNode?.closest<HTMLElement>(
        "[data-source-page]",
      );
      onTextSelection({
        text,
        sourcePage: Number(pageElement?.dataset.sourcePage ?? pageNumber),
      });
    }
  };

  const renderedPages = continuous
    ? Array.from({ length: pageCount }, (_, index) => index + 1)
    : [pageNumber];
  const fittedPageWidth = fitWidth && stageWidth > 0
    ? Math.max(240, stageWidth - 52)
    : undefined;

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
            className={continuous ? "active" : ""}
            onClick={() => setContinuous((value) => !value)}
          >
            {continuous ? "连续" : "单页"}
          </button>
          <button
            type="button"
            className={fitWidth ? "active" : ""}
            onClick={() => setFitWidth((value) => !value)}
          >
            适合宽度
          </button>
          <button
            type="button"
            aria-label="缩小"
            onClick={() => {
              setFitWidth(false);
              setScale((value) => Math.max(0.6, value - 0.15));
            }}
          >
            −
          </button>
          <span>{fitWidth ? "自适应" : `${Math.round(scale * 100)}%`}</span>
          <button
            type="button"
            aria-label="放大"
            onClick={() => {
              setFitWidth(false);
              setScale((value) => Math.min(2.2, value + 0.15));
            }}
          >
            +
          </button>
        </div>
      </header>

      <div
        ref={stageRef}
        className="document-stage"
        onMouseUp={captureTextSelection}
      >
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
          <div className={continuous ? "pdf-pages continuous" : "pdf-pages"}>
            {renderedPages.map((renderedPage) => (
              <div
                className="pdf-page-wrapper"
                data-source-page={renderedPage}
                key={renderedPage}
                ref={(element) => {
                  if (element) {
                    pageElements.current.set(renderedPage, element);
                  } else {
                    pageElements.current.delete(renderedPage);
                  }
                }}
              >
                <Page
                  pageNumber={renderedPage}
                  width={fittedPageWidth}
                  scale={fitWidth ? undefined : scale}
                  renderTextLayer
                  renderAnnotationLayer
                  onRenderSuccess={() => {
                    if (
                      continuous &&
                      renderedPage === pageNumber &&
                      !pageChangeCameFromScroll.current
                    ) {
                      const targetElement = pageElements.current.get(renderedPage);
                      if (targetElement) {
                        programmaticTargetPage.current = renderedPage;
                        targetElement.scrollIntoView({ block: "start" });
                      }
                    }
                  }}
                />
                <span className="rendered-page-number">第 {renderedPage} 页</span>
              </div>
            ))}
          </div>
        </Document>
      </div>
    </section>
  );
}
