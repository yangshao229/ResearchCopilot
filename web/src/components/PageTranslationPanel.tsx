import { useEffect, useRef, useState } from "react";

import {
  getPageQuality,
  getPageLayout,
  getPageTranslation,
  translatePage,
  type PageLayout,
  type PageQuality,
  type PageSourceRegion,
  type PageTranslation,
} from "../api";
import { useI18n } from "../i18n-context";
import OriginalPdfClip from "./OriginalPdfClip";

type Props = {
  paperId: string;
  sourcePage: number;
  targetLanguage: "zh-CN" | "en";
  onFocusSourceRegion: (layout: PageLayout, region: PageSourceRegion) => void;
};

export default function PageTranslationPanel({
  paperId,
  sourcePage,
  targetLanguage,
  onFocusSourceRegion,
}: Props) {
  const { t, errorMessage } = useI18n();
  const [translation, setTranslation] = useState<PageTranslation | null>(null);
  const [quality, setQuality] = useState<PageQuality | null>(null);
  const [layout, setLayout] = useState<PageLayout | null>(null);
  const [layoutError, setLayoutError] = useState(false);
  const [loading, setLoading] = useState(true);
  const [translating, setTranslating] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const currentPageKey = useRef("");
  const pageKey = `${paperId}:${sourcePage}:${targetLanguage}`;
  currentPageKey.current = pageKey;

  useEffect(() => {
    let active = true;
    setTranslation(null);
    setQuality(null);
    setLayout(null);
    setLayoutError(false);
    setError(null);
    setLoading(true);
    setTranslating(false);
    getPageQuality(paperId, sourcePage)
      .then(async (report) => {
        if (active) setQuality(report);
        if (report.status === "blocked") return;
        const cached = await getPageTranslation(paperId, sourcePage);
        if (active && cached?.target_language === targetLanguage) setTranslation(cached);
      })
      .catch((reason: unknown) => {
        if (active) setError(errorMessage(reason, "translation.errorLoad"));
      })
      .finally(() => {
        if (active) setLoading(false);
      });
    getPageLayout(paperId, sourcePage)
      .then((result) => {
        if (active) setLayout(result);
      })
      .catch(() => {
        if (active) setLayoutError(true);
      });
    return () => {
      active = false;
    };
  }, [paperId, sourcePage, targetLanguage]);

  const runTranslation = async (refresh: boolean) => {
    if (!quality || quality.status === "blocked") return;
    const requestedKey = pageKey;
    setTranslating(true);
    setError(null);
    try {
      const result = await translatePage(paperId, sourcePage, refresh);
      if (currentPageKey.current === requestedKey) {
        setTranslation(result);
      }
    } catch (reason: unknown) {
      if (currentPageKey.current === requestedKey) {
        setError(
          reason instanceof Error && reason.message.includes("DEEPSEEK_API_KEY")
            ? t("translation.noKey")
            : errorMessage(reason, "translation.errorGenerate"),
        );
      }
    } finally {
      if (currentPageKey.current === requestedKey) setTranslating(false);
    }
  };

  return (
    <div className="assistant-content page-translation-content">
      <p className="eyebrow">{t("translation.eyebrow")}</p>
      <h2>{t("translation.title", { page: sourcePage })}</h2>
      <p className="assistant-intro">{t("translation.intro")}</p>
      <p className="translation-boundary">{t("translation.boundary")}</p>
      <p className="translation-target">
        {t("translation.target", {
          language:
            targetLanguage === "zh-CN"
              ? t("assistant.languageChinese")
              : t("assistant.languageEnglish"),
        })}
      </p>
      {loading && <p role="status">{t("translation.loadingCache")}</p>}
      {error && <p className="search-error" role="alert">{error}</p>}
      {quality && (
        <div className={`translation-quality translation-quality-${quality.status}`} role="status">
          <strong>{t(`translation.quality.${quality.status}`)}</strong>
          <span>{t("translation.quality.chars", { count: quality.extractable_chars })}</span>
          {quality.issues.map((issue) => (
            <p key={issue}>{t(`translation.quality.${issue}`)}</p>
          ))}
          <p>{t("translation.quality.limit")}</p>
        </div>
      )}
      {layout?.risk_flags.length ? (
        <div className="layout-risk" role="status">
          <strong>{t("translation.layoutReviewTitle")}</strong>
          {layout.risk_flags.map((flag) => (
            <p key={flag}>{t(`translation.layoutRisk.${flag}`)}</p>
          ))}
          <p>{t("translation.layoutOrderUnverified")}</p>
        </div>
      ) : null}
      {(layout || layoutError) && (
        <details className="source-region-details">
          <summary>{t("translation.sourceRegions", { count: layout?.regions.length ?? 0 })}</summary>
          <p>{t("translation.sourceRegionsLimit")}</p>
          {layoutError && <p role="alert">{t("translation.sourceRegionsError")}</p>}
          {layout?.status === "no_text" && <p>{t("translation.sourceRegionsEmpty")}</p>}
          {layout?.status === "unsupported_rotation" && (
            <p>{t("translation.sourceRegionsRotated")}</p>
          )}
          {layout?.truncated && <p>{t("translation.sourceRegionsTruncated")}</p>}
          <div className="source-region-list">
            {layout?.regions.map((region, index) => (
              <button
                key={region.id}
                type="button"
                onClick={() => onFocusSourceRegion(layout, region)}
                title={t("translation.focusSourceRegion")}
              >
                <small>{t("translation.sourceRegionLabel", { index: index + 1 })}</small>
                <span>{region.text.replace(/\s+/g, " ").slice(0, 170)}</span>
              </button>
            ))}
          </div>
        </details>
      )}
      {!loading && !translation && (
        <button
          type="button"
          className="translation-action"
          disabled={translating || !quality || quality.status === "blocked"}
          onClick={() => void runTranslation(false)}
        >
          {translating ? t("translation.translating") : t("translation.translatePage")}
        </button>
      )}
      {translation && (
        <section className="page-translation-result" aria-label={t("translation.resultAria")}>
          <div className="page-translation-heading">
            <strong>{t("translation.resultTitle", { page: translation.source_page })}</strong>
            <small>{translation.cache_hit ? t("translation.cached") : translation.model}</small>
          </div>
          {translation.formula_regions?.length > 0 && (
            <p className="translation-math-notice">{t("translation.mathNotice")}</p>
          )}
          {translation.table_regions?.length > 0 && (
            <p className="translation-math-notice">{t("translation.tableNotice")}</p>
          )}
          <div className="page-translation-text">
            {translation.translated_text
              .split(/(\[\[RC_(?:FORMULA|TABLE)_\d{2}\]\])/g)
              .map((part, index) => {
                const formula = translation.formula_regions?.find(
                  (candidate) => candidate.marker === part,
                );
                if (formula) return (
                  <OriginalPdfClip key={`${part}-${index}`} paperId={paperId} region={formula} kind="formula" />
                );
                const table = translation.table_regions?.find(
                  (candidate) => candidate.marker === part,
                );
                if (table) return (
                  <OriginalPdfClip key={`${part}-${index}`} paperId={paperId} region={table} kind="table" />
                );
                return <span key={`${part}-${index}`}>{part}</span>;
              })}
          </div>
          <p className="translation-source-count">
            {t("translation.sourceCount", { count: translation.source_chars })}
          </p>
          <button
            type="button"
            disabled={translating || !quality || quality.status === "blocked"}
            onClick={() => void runTranslation(true)}
          >
            {translating ? t("translation.translating") : t("translation.retranslate")}
          </button>
        </section>
      )}
    </div>
  );
}
