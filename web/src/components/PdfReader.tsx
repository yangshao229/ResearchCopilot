import { useEffect, useRef, useState } from "react";
import type { MouseEvent as ReactMouseEvent } from "react";
import { Document, Page } from "react-pdf";

import { paperFileUrl, type PageSourceRegion, type Paper } from "../api";
import { useI18n } from "../i18n-context";


export type PdfSelection = {
  text: string;
  sourcePage: number;
};

export type FocusedSourceRegion = PageSourceRegion & {
  paperId: string;
  pageWidth: number;
  pageHeight: number;
};

type PdfReaderProps = {
  paper: Paper;
  pageNumber: number;
  onPageChange: (pageNumber: number) => void;
  onTextSelection: (selection: PdfSelection) => void;
  focusedSourceRegion: FocusedSourceRegion | null;
};

export default function PdfReader({
  paper,
  pageNumber,
  onPageChange,
  onTextSelection,
  focusedSourceRegion,
}: PdfReaderProps) {
  const { language, t } = useI18n();
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

    const updateWidth = () => setStageWidth(stage.clientWidth);
    updateWidth();
    if (typeof ResizeObserver === "undefined") {
      window.addEventListener("resize", updateWidth);
      return () => window.removeEventListener("resize", updateWidth);
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
    if (
      !focusedSourceRegion ||
      focusedSourceRegion.paperId !== paper.id ||
      focusedSourceRegion.source_page !== pageNumber
    ) return;
    const animationFrame = window.requestAnimationFrame(() => {
      const stage = stageRef.current;
      const wrapper = pageElements.current.get(focusedSourceRegion.source_page);
      const canvas = wrapper?.querySelector("canvas");
      if (!stage || !wrapper || !canvas) return;
      const stageTop = stage.getBoundingClientRect().top;
      const canvasTop = canvas.getBoundingClientRect().top;
      const relativeTop = focusedSourceRegion.top / focusedSourceRegion.pageHeight;
      stage.scrollTo({
        top: stage.scrollTop + canvasTop - stageTop + relativeTop * canvas.clientHeight
          - stage.clientHeight * 0.3,
        behavior: "smooth",
      });
    });
    return () => window.cancelAnimationFrame(animationFrame);
  }, [focusedSourceRegion, pageNumber, paper.id, continuous, stageWidth]);

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
    <section className="reader" aria-label={t("reader.aria")}>
      <header className="reader-toolbar">
        <div className="page-controls">
          <button
            type="button"
            onClick={() => goToPage(pageNumber - 1)}
            disabled={pageNumber <= 1}
          >
            {t("reader.previous")}
          </button>
          <label>
            {t("reader.pagePrefix")}
            <input
              aria-label={t("reader.currentPageAria")}
              type="number"
              min="1"
              max={pageCount || undefined}
              value={pageNumber}
              onChange={(event) => goToPage(Number(event.target.value))}
            />
            {t("reader.pageSuffix")}
          </label>
          <span className="muted">
            {language === "zh-CN" ? "/ " : ""}{pageCount || "—"}
          </span>
          <button
            type="button"
            onClick={() => goToPage(pageNumber + 1)}
            disabled={pageCount > 0 && pageNumber >= pageCount}
          >
            {t("reader.next")}
          </button>
        </div>

        <span className="selection-hint">{t("reader.selectionHint")}</span>

        <div className="zoom-controls">
          <button
            type="button"
            className={continuous ? "active" : ""}
            onClick={() => setContinuous((value) => !value)}
          >
            {continuous ? t("reader.continuous") : t("reader.singlePage")}
          </button>
          <button
            type="button"
            className={fitWidth ? "active" : ""}
            onClick={() => setFitWidth((value) => !value)}
          >
            {t("reader.fitWidth")}
          </button>
          <button
            type="button"
            aria-label={t("reader.zoomOutAria")}
            onClick={() => {
              setFitWidth(false);
              setScale((value) => Math.max(0.6, value - 0.15));
            }}
          >
            −
          </button>
          <span>{fitWidth ? t("reader.autoScale") : `${Math.round(scale * 100)}%`}</span>
          <button
            type="button"
            aria-label={t("reader.zoomInAria")}
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
          loading={<div className="reader-message">{t("reader.loading")}</div>}
          error={<div className="reader-message error">{t("reader.error")}</div>}
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
                {focusedSourceRegion?.paperId === paper.id &&
                  focusedSourceRegion.source_page === renderedPage && (
                    <div
                      className="source-region-highlight"
                      role="img"
                      aria-label={t("reader.sourceRegionHighlight")}
                      style={{
                        left: `${100 * focusedSourceRegion.left / focusedSourceRegion.pageWidth}%`,
                        top: `${100 * focusedSourceRegion.top / focusedSourceRegion.pageHeight}%`,
                        width: `${100 * focusedSourceRegion.width / focusedSourceRegion.pageWidth}%`,
                        height: `${100 * focusedSourceRegion.height / focusedSourceRegion.pageHeight}%`,
                      }}
                    />
                  )}
                <span className="rendered-page-number">
                  {t("reader.renderedPage", { page: renderedPage })}
                </span>
              </div>
            ))}
          </div>
        </Document>
      </div>
    </section>
  );
}
