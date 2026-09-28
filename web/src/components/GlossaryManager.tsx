import { useEffect, useState } from "react";

import {
  addPaperGlossaryEntry,
  deletePaperGlossaryEntry,
  listPaperGlossary,
  type GlossaryEntry,
} from "../api";
import { useI18n } from "../i18n-context";

type GlossaryManagerProps = {
  paperId: string;
  targetLanguage: GlossaryEntry["target_language"];
  selectionText: string;
  onChange: () => void;
};

export default function GlossaryManager({
  paperId,
  targetLanguage,
  selectionText,
  onChange,
}: GlossaryManagerProps) {
  const { t, errorMessage } = useI18n();
  const [entries, setEntries] = useState<GlossaryEntry[]>([]);
  const [source, setSource] = useState("");
  const [translation, setTranslation] = useState("");
  const [error, setError] = useState<string | null>(null);
  const [isBusy, setIsBusy] = useState(false);

  useEffect(() => {
    let isCurrent = true;
    setEntries([]);
    setError(null);
    listPaperGlossary(paperId)
      .then((saved) => {
        if (isCurrent) setEntries(saved);
      })
      .catch((reason: unknown) => {
        if (isCurrent) {
          setError(errorMessage(reason, "glossary.errorLoad"));
        }
      });
    return () => {
      isCurrent = false;
    };
  }, [paperId]);

  useEffect(() => {
    setSource("");
    setTranslation("");
  }, [paperId, targetLanguage]);

  const addEntry = async () => {
    if (!source.trim() || !translation.trim() || isBusy) return;
    setIsBusy(true);
    setError(null);
    try {
      const saved = await addPaperGlossaryEntry(
        paperId,
        source.trim(),
        translation.trim(),
        targetLanguage,
      );
      setEntries((current) => [...current, saved]);
      setSource("");
      setTranslation("");
      onChange();
    } catch (reason: unknown) {
      setError(errorMessage(reason, "glossary.errorSave"));
    } finally {
      setIsBusy(false);
    }
  };

  const deleteEntry = async (entryId: string) => {
    if (isBusy) return;
    setIsBusy(true);
    setError(null);
    try {
      await deletePaperGlossaryEntry(paperId, entryId);
      setEntries((current) => current.filter((entry) => entry.id !== entryId));
      onChange();
    } catch (reason: unknown) {
      setError(errorMessage(reason, "glossary.errorDelete"));
    } finally {
      setIsBusy(false);
    }
  };

  const currentEntries = entries.filter(
    (entry) => entry.target_language === targetLanguage,
  );
  const cleanedSelection = selectionText.trim().replace(/\s+/g, " ");

  return (
    <details className="glossary-manager">
      <summary>{t("glossary.summary", { count: currentEntries.length })}</summary>
      <p>{t("glossary.help")}</p>
      {currentEntries.length > 0 && (
        <ul>
          {currentEntries.map((entry) => (
            <li key={entry.id}>
              <span>{entry.source} → {entry.translation}</span>
              <button
                type="button"
                disabled={isBusy}
                aria-label={t("glossary.deleteAria", { term: entry.source })}
                onClick={() => void deleteEntry(entry.id)}
              >
                {t("glossary.delete")}
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="glossary-fields">
        <input
          aria-label={t("glossary.sourceAria")}
          value={source}
          onChange={(event) => setSource(event.target.value)}
          maxLength={100}
          placeholder={t("glossary.sourcePlaceholder")}
        />
        <input
          aria-label={t("glossary.translationAria")}
          value={translation}
          onChange={(event) => setTranslation(event.target.value)}
          maxLength={100}
          placeholder={
            targetLanguage === "zh-CN"
              ? t("glossary.chineseTranslationPlaceholder")
              : t("glossary.englishTranslationPlaceholder")
          }
        />
      </div>
      <div className="glossary-actions">
        <button
          type="button"
          disabled={!cleanedSelection || cleanedSelection.length > 100 || isBusy}
          onClick={() => setSource(cleanedSelection)}
        >
          {t("glossary.useSelection")}
        </button>
        <button
          type="button"
          disabled={!source.trim() || !translation.trim() || isBusy}
          onClick={() => void addEntry()}
        >
          {t("glossary.save")}
        </button>
      </div>
      {error && <p className="search-error" role="alert">{error}</p>}
    </details>
  );
}
