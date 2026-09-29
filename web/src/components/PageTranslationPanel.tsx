import { useEffect, useRef, useState } from "react";

import {
  getPageQuality,
  getPageTranslation,
  translatePage,
  type PageQuality,
  type PageTranslation,
} from "../api";
import { useI18n } from "../i18n-context";
import FormulaClip from "./FormulaClip";

type Props = {
  paperId: string;
  sourcePage: number;
  targetLanguage: "zh-CN" | "en";
};

export default function PageTranslationPanel({
  paperId,
  sourcePage,
  targetLanguage,
}: Props) {
  const { t, errorMessage } = useI18n();
  const [translation, setTranslation] = useState<PageTranslation | null>(null);
  const [quality, setQuality] = useState<PageQuality | null>(null);
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
          <div className="page-translation-text">
            {translation.translated_text
              .split(/(\[\[RC_FORMULA_\d{2}\]\])/g)
              .map((part, index) => {
                const region = translation.formula_regions?.find(
                  (candidate) => candidate.marker === part,
                );
                return region ? (
                  <FormulaClip key={`${part}-${index}`} paperId={paperId} region={region} />
                ) : (
                  <span key={`${part}-${index}`}>{part}</span>
                );
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
