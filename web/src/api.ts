export type Paper = {
  id: string;
  name: string;
  relative_path: string;
  page_count: number | null;
  detected_source_language: "en" | "zh-CN" | "mixed" | "unknown";
};

export type PaperImportResult = {
  paper: Paper;
  imported: boolean;
  message: string;
};

export type PaperSection = {
  title: string;
  level: number;
  source_page: number;
  source: "bookmark" | "heuristic";
  confidence: "high" | "medium";
};

export type PaperStructure = {
  page_count: number;
  sections: PaperSection[];
  method: "bookmarks" | "heuristic" | "unavailable";
  warnings: string[];
};

export type ConversationSession = {
  id: string;
  paper_id: string;
  title: string;
  created_at: string;
};

export type ReadingQuestion = {
  role: "overview" | "method" | "experiments" | "critique";
  label: string;
  section_title: string;
  question: string;
  source_page: number;
};

export type PaperReadingGuide = {
  questions: ReadingQuestion[];
  method: string;
  warnings: string[];
};

export type SearchMode = "keyword" | "semantic" | "hybrid";
export type ScopePreference = "auto" | "full_paper";
export type LanguagePolicy = {
  explanation_language: "follow_question" | "zh-CN" | "en";
  translation_target: "zh-CN" | "en";
  terminology_policy:
    | "bilingual_first_use"
    | "preserve_english"
    | "translate_all";
  source_language_override: "auto" | "zh-CN" | "en";
};
export type GlossaryEntry = {
  id: string;
  source: string;
  translation: string;
  target_language: "zh-CN" | "en";
};
export type ReadingTask =
  | "lookup"
  | "translate"
  | "explain"
  | "formula"
  | "question"
  | "structure"
  | "summarize";
export type ReadingAnchor = {
  source_page: number | null;
  selected_text: string;
  section_title: string;
};
export type SelectionContextPreview = {
  source_page: number;
  selected_text: string;
  context_text: string;
  method: "paragraph" | "page_window" | "selection_only";
  note: string;
  glossary_terms: GlossaryEntry[];
};
export type ReadingScope = {
  kind: "full_paper" | "section" | "selection";
  resolution: "full_paper" | "matched" | "fallback";
  section_title: string;
  start_page: number | null;
  end_page: number | null;
  note: string;
};
export type ReadingCategory =
  | "unclassified"
  | "summary"
  | "research_problem"
  | "method"
  | "experiments"
  | "contributions"
  | "limitations"
  | "open_questions";

export type SearchResult = {
  source_page: number;
  chunk_index: number;
  text: string;
  score: number;
  keyword_rank: number;
  keyword_score: number;
  semantic_rank: number;
  semantic_score: number;
  fusion_score: number;
  reference_penalty: number;
  rerank_score: number;
};

export type Evidence = SearchResult & {
  evidence_id: number;
};

export type AnswerCitation = {
  evidence_id: number;
  source_page: number;
  quote: string;
};

export type PaperAnswer = {
  answer: string;
  explanation: string;
  citations: AnswerCitation[];
  insufficient_evidence: boolean;
  uncertainty: string;
  evidence: Evidence[];
  provider: string;
  model: string;
  history_id: string | null;
  scope: ReadingScope;
  language: LanguagePolicy;
  cache_hit: boolean;
};

export type PageTranslation = {
  source_page: number;
  source_chars: number;
  target_language: "zh-CN" | "en";
  translated_text: string;
  model: string;
  cache_hit: boolean;
};

export type ReadingRecord = {
  id: string;
  paper_id: string;
  paper_name: string;
  created_at: string;
  question: string;
  task: ReadingTask;
  session_id: string;
  anchor: ReadingAnchor | null;
  context_text: string;
  search_mode: SearchMode;
  answer: string;
  explanation: string;
  citations: AnswerCitation[];
  insufficient_evidence: boolean;
  uncertainty: string;
  provider: string;
  model: string;
  confirmed: boolean;
  personal_note: string;
  category: ReadingCategory;
  scope: ReadingScope;
  language: LanguagePolicy;
};

export type PaperSearchExecution = {
  results: SearchResult[];
  scope: ReadingScope;
};

export type PaperCardPreview = {
  paper_id: string;
  paper_name: string;
  confirmed_record_count: number;
  markdown: string;
  output_filename: string;
  existing_card: boolean;
  diff: string;
};

async function responseError(
  response: Response,
  fallback: string,
): Promise<Error> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (body.detail) {
      return new Error(body.detail);
    }
  } catch {
    // The server did not return a JSON error body.
  }
  return new Error(`${fallback}：${response.status}`);
}

export async function listPapers(): Promise<Paper[]> {
  const response = await fetch("/api/papers");

  if (!response.ok) {
    throw new Error(`论文列表加载失败：${response.status}`);
  }

  return (await response.json()) as Paper[];
}

export async function getPageTranslation(
  paperId: string,
  sourcePage: number,
): Promise<PageTranslation | null> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/translation`,
  );
  if (!response.ok) {
    throw await responseError(response, "页译文加载失败");
  }
  return (await response.json()) as PageTranslation | null;
}

export async function translatePage(
  paperId: string,
  sourcePage: number,
  refresh = false,
): Promise<PageTranslation> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/translation`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    },
  );
  if (!response.ok) {
    throw await responseError(response, "当前页翻译失败");
  }
  return (await response.json()) as PageTranslation;
}

export async function getPaperLanguagePreferences(
  paperId: string,
): Promise<LanguagePolicy> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/language`,
  );
  if (!response.ok) {
    throw await responseError(response, "论文语言偏好加载失败");
  }
  return (await response.json()) as LanguagePolicy;
}

export async function savePaperLanguagePreferences(
  paperId: string,
  policy: LanguagePolicy,
): Promise<LanguagePolicy> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/language`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(policy),
    },
  );
  if (!response.ok) {
    throw await responseError(response, "论文语言偏好保存失败");
  }
  return (await response.json()) as LanguagePolicy;
}

export async function listPaperGlossary(paperId: string): Promise<GlossaryEntry[]> {
  const response = await fetch(`/api/papers/${encodeURIComponent(paperId)}/glossary`);
  if (!response.ok) throw await responseError(response, "论文术语表加载失败");
  return (await response.json()) as GlossaryEntry[];
}

export async function addPaperGlossaryEntry(
  paperId: string,
  source: string,
  translation: string,
  targetLanguage: GlossaryEntry["target_language"],
): Promise<GlossaryEntry> {
  const response = await fetch(`/api/papers/${encodeURIComponent(paperId)}/glossary`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ source, translation, target_language: targetLanguage }),
  });
  if (!response.ok) throw await responseError(response, "论文术语保存失败");
  return (await response.json()) as GlossaryEntry;
}

export async function deletePaperGlossaryEntry(
  paperId: string,
  entryId: string,
): Promise<void> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/glossary/${encodeURIComponent(entryId)}`,
    { method: "DELETE" },
  );
  if (!response.ok) throw await responseError(response, "论文术语删除失败");
}

export async function importPaper(file: File): Promise<PaperImportResult> {
  const response = await fetch("/api/papers/import", {
    method: "POST",
    headers: {
      "Content-Type": "application/pdf",
      "X-PDF-Filename": encodeURIComponent(file.name),
    },
    body: file,
  });

  if (!response.ok) {
    throw await responseError(response, "PDF 导入失败");
  }

  return (await response.json()) as PaperImportResult;
}

export function paperFileUrl(paperId: string): string {
  return `/api/papers/${encodeURIComponent(paperId)}/file`;
}

export async function getPaperStructure(
  paperId: string,
): Promise<PaperStructure> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/structure`,
  );
  if (!response.ok) {
    throw await responseError(response, "论文目录加载失败");
  }
  return (await response.json()) as PaperStructure;
}

export async function getPaperReadingGuide(
  paperId: string,
): Promise<PaperReadingGuide> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/guide`,
  );
  if (!response.ok) {
    throw await responseError(response, "论文阅读路线加载失败");
  }
  return (await response.json()) as PaperReadingGuide;
}

export async function listConversationSessions(
  paperId: string,
): Promise<ConversationSession[]> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/sessions`,
  );
  if (!response.ok) {
    throw await responseError(response, "阅读会话加载失败");
  }
  return (await response.json()) as ConversationSession[];
}

export async function createConversationSession(
  paperId: string,
  title: string,
): Promise<ConversationSession> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/sessions`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title }),
    },
  );
  if (!response.ok) {
    throw await responseError(response, "阅读会话创建失败");
  }
  return (await response.json()) as ConversationSession;
}

export async function searchPaper(
  paperId: string,
  query: string,
  mode: SearchMode,
  limit = 5,
  scopePreference: ScopePreference = "auto",
): Promise<PaperSearchExecution> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        mode,
        limit,
        scope_preference: scopePreference,
      }),
    },
  );

  if (!response.ok) {
    throw await responseError(response, "证据检索失败");
  }

  const scopeHeader = response.headers.get("X-Reading-Scope");
  const scope = scopeHeader
    ? (JSON.parse(scopeHeader) as ReadingScope)
    : {
        kind: "full_paper" as const,
        resolution: "full_paper" as const,
        section_title: "",
        start_page: null,
        end_page: null,
        note: "全文检索。",
      };
  return {
    results: (await response.json()) as SearchResult[],
    scope,
  };
}

export async function answerPaper(
  paperId: string,
  query: string,
  mode: SearchMode,
  sessionId = "default",
  limit = 5,
  scopePreference: ScopePreference = "auto",
  language?: LanguagePolicy,
  task: ReadingTask = "question",
  anchor?: ReadingAnchor,
  refreshTranslation = false,
): Promise<PaperAnswer> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/answer`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({
        query,
        mode,
        limit,
        session_id: sessionId,
        scope_preference: scopePreference,
        task,
        ...(anchor ? { anchor } : {}),
        ...(refreshTranslation ? { refresh_translation: true } : {}),
        ...(language ? { language } : {}),
      }),
    },
  );

  if (!response.ok) {
    throw await responseError(response, "论文回答生成失败");
  }

  return (await response.json()) as PaperAnswer;
}

export async function previewSelectionContext(
  paperId: string,
  sourcePage: number,
  selectedText: string,
  targetLanguage: GlossaryEntry["target_language"] = "zh-CN",
): Promise<SelectionContextPreview> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/selection-context`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        source_page: sourcePage,
        selected_text: selectedText,
        target_language: targetLanguage,
      }),
    },
  );
  if (!response.ok) {
    throw await responseError(response, "选区上下文读取失败");
  }
  return (await response.json()) as SelectionContextPreview;
}

export async function listReadingHistory(
  paperId: string,
  sessionId?: string,
): Promise<ReadingRecord[]> {
  const query = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/history${query}`,
  );
  if (!response.ok) {
    throw await responseError(response, "阅读记录加载失败");
  }
  return (await response.json()) as ReadingRecord[];
}

export async function updateReadingRecord(
  paperId: string,
  recordId: string,
  confirmed: boolean,
  personalNote: string,
  category: ReadingCategory,
): Promise<ReadingRecord> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/history/${encodeURIComponent(recordId)}`,
    {
      method: "PATCH",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        confirmed,
        personal_note: personalNote,
        category,
      }),
    },
  );
  if (!response.ok) {
    throw await responseError(response, "阅读记录保存失败");
  }
  return (await response.json()) as ReadingRecord;
}

export function exportReadingRecordUrl(
  paperId: string,
  recordId: string,
): string {
  return `/api/papers/${encodeURIComponent(paperId)}/history/${encodeURIComponent(recordId)}/export`;
}

export async function previewPaperCard(
  paperId: string,
): Promise<PaperCardPreview> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/card/preview`,
  );
  if (!response.ok) {
    throw await responseError(response, "论文卡片预览生成失败");
  }
  return (await response.json()) as PaperCardPreview;
}

export async function downloadPaperCard(
  paperId: string,
  paperName: string,
  newVersion: boolean,
): Promise<void> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/card/export?new_version=${newVersion}`,
    { method: "POST" },
  );
  if (!response.ok) {
    throw await responseError(response, "论文卡片导出失败");
  }

  const downloadUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = `${paperName.replace(/\.pdf$/i, "")}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
}
