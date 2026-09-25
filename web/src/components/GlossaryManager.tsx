import { useEffect, useState } from "react";

import {
  addPaperGlossaryEntry,
  deletePaperGlossaryEntry,
  listPaperGlossary,
  type GlossaryEntry,
} from "../api";

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
          setError(reason instanceof Error ? reason.message : "术语表加载失败。");
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
      setError(reason instanceof Error ? reason.message : "术语保存失败。");
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
      setError(reason instanceof Error ? reason.message : "术语删除失败。");
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
      <summary>当前论文术语表 · {currentEntries.length} 条</summary>
      <p>只在本次选区或同页上下文命中时用于翻译；术语不是论文证据。</p>
      {currentEntries.length > 0 && (
        <ul>
          {currentEntries.map((entry) => (
            <li key={entry.id}>
              <span>{entry.source} → {entry.translation}</span>
              <button
                type="button"
                disabled={isBusy}
                aria-label={`删除术语 ${entry.source}`}
                onClick={() => void deleteEntry(entry.id)}
              >
                删除
              </button>
            </li>
          ))}
        </ul>
      )}
      <div className="glossary-fields">
        <input
          aria-label="术语原文"
          value={source}
          onChange={(event) => setSource(event.target.value)}
          maxLength={100}
          placeholder="英文术语，如 attention head"
        />
        <input
          aria-label="指定译名"
          value={translation}
          onChange={(event) => setTranslation(event.target.value)}
          maxLength={100}
          placeholder={targetLanguage === "zh-CN" ? "指定中文译名" : "Preferred English term"}
        />
      </div>
      <div className="glossary-actions">
        <button
          type="button"
          disabled={!cleanedSelection || cleanedSelection.length > 100 || isBusy}
          onClick={() => setSource(cleanedSelection)}
        >
          使用当前选区作原文
        </button>
        <button
          type="button"
          disabled={!source.trim() || !translation.trim() || isBusy}
          onClick={() => void addEntry()}
        >
          保存术语
        </button>
      </div>
      {error && <p className="search-error" role="alert">{error}</p>}
    </details>
  );
}
