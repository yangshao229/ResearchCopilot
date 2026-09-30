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

export type PdfClipRegion = {
  marker: string;
  source_page: number;
  left: number;
  top: number;
  width: number;
  height: number;
};

export type PageTranslation = {
  source_page: number;
  source_chars: number;
  target_language: "zh-CN" | "en";
  translated_text: string;
  formula_regions: PdfClipRegion[];
  table_regions: PdfClipRegion[];
  model: string;
  cache_hit: boolean;
};

export type PageQuality = {
  source_page: number;
  extractable_chars: number;
  status: "ready" | "review" | "blocked";
  issues: (
    | "no_text"
    | "short_text"
    | "damaged_text"
    | "long_text"
    | "math_review"
    | "column_order_review"
    | "column_order_mismatch"
  )[];
};

export type PageSourceRegion = {
  id: string;
  source_page: number;
  text: string;
  left: number;
  top: number;
  width: number;
  height: number;
};

export type PageLayout = {
  source_page: number;
  page_width: number;
  page_height: number;
  status: "ready" | "no_text" | "unsupported_rotation";
  order_verified: boolean;
  risk_flags: (
    | "multi_column_candidate"
    | "table_rulings_candidate"
    | "small_glyph_fragments"
  )[];
  truncated: boolean;
  regions: PageSourceRegion[];
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

async function requestResponse(
  url: string,
  fallback: string,
  options?: RequestInit,
): Promise<Response> {
  const response = await fetch(url, options);
  if (!response.ok) {
    throw await responseError(response, fallback);
  }
  return response;
}

async function requestJson<T>(
  url: string,
  fallback: string,
  options?: RequestInit,
): Promise<T> {
  const response = await requestResponse(url, fallback, options);
  return (await response.json()) as T;
}

function jsonOptions(method: string, body: unknown): RequestInit {
  return {
    method,
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  };
}

export async function listPapers(): Promise<Paper[]> {
  return requestJson<Paper[]>("/api/papers", "论文列表加载失败");
}

export async function getPageTranslation(
  paperId: string,
  sourcePage: number,
): Promise<PageTranslation | null> {
  return requestJson<PageTranslation | null>(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/translation`,
    "页译文加载失败",
  );
}

export async function getPageQuality(
  paperId: string,
  sourcePage: number,
): Promise<PageQuality> {
  return requestJson<PageQuality>(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/quality`,
    "页解析质量读取失败",
  );
}

export async function getPageLayout(
  paperId: string,
  sourcePage: number,
): Promise<PageLayout> {
  return requestJson<PageLayout>(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/layout`,
    "页原文位置读取失败",
  );
}

export async function translatePage(
  paperId: string,
  sourcePage: number,
  refresh = false,
): Promise<PageTranslation> {
  return requestJson<PageTranslation>(
    `/api/papers/${encodeURIComponent(paperId)}/pages/${sourcePage}/translation`,
    "当前页翻译失败",
    jsonOptions("POST", { refresh }),
  );
}

export async function getPaperLanguagePreferences(
  paperId: string,
): Promise<LanguagePolicy> {
  return requestJson<LanguagePolicy>(
    `/api/papers/${encodeURIComponent(paperId)}/language`,
    "论文语言偏好加载失败",
  );
}

export async function savePaperLanguagePreferences(
  paperId: string,
  policy: LanguagePolicy,
): Promise<LanguagePolicy> {
  return requestJson<LanguagePolicy>(
    `/api/papers/${encodeURIComponent(paperId)}/language`,
    "论文语言偏好保存失败",
    jsonOptions("PUT", policy),
  );
}

export async function listPaperGlossary(paperId: string): Promise<GlossaryEntry[]> {
  return requestJson<GlossaryEntry[]>(
    `/api/papers/${encodeURIComponent(paperId)}/glossary`,
    "论文术语表加载失败",
  );
}

export async function addPaperGlossaryEntry(
  paperId: string,
  source: string,
  translation: string,
  targetLanguage: GlossaryEntry["target_language"],
): Promise<GlossaryEntry> {
  return requestJson<GlossaryEntry>(
    `/api/papers/${encodeURIComponent(paperId)}/glossary`,
    "论文术语保存失败",
    jsonOptions("POST", { source, translation, target_language: targetLanguage }),
  );
}

export async function deletePaperGlossaryEntry(
  paperId: string,
  entryId: string,
): Promise<void> {
  await requestResponse(
    `/api/papers/${encodeURIComponent(paperId)}/glossary/${encodeURIComponent(entryId)}`,
    "论文术语删除失败",
    { method: "DELETE" },
  );
}

export async function importPaper(file: File): Promise<PaperImportResult> {
  return requestJson<PaperImportResult>(
    "/api/papers/import",
    "PDF 导入失败",
    {
      method: "POST",
      headers: {
        "Content-Type": "application/pdf",
        "X-PDF-Filename": encodeURIComponent(file.name),
      },
      body: file,
    },
  );
}

export function paperFileUrl(paperId: string): string {
  return `/api/papers/${encodeURIComponent(paperId)}/file`;
}

export async function getPaperStructure(
  paperId: string,
): Promise<PaperStructure> {
  return requestJson<PaperStructure>(
    `/api/papers/${encodeURIComponent(paperId)}/structure`,
    "论文目录加载失败",
  );
}

export async function getPaperReadingGuide(
  paperId: string,
): Promise<PaperReadingGuide> {
  return requestJson<PaperReadingGuide>(
    `/api/papers/${encodeURIComponent(paperId)}/guide`,
    "论文阅读路线加载失败",
  );
}

export async function listConversationSessions(
  paperId: string,
): Promise<ConversationSession[]> {
  return requestJson<ConversationSession[]>(
    `/api/papers/${encodeURIComponent(paperId)}/sessions`,
    "阅读会话加载失败",
  );
}

export async function createConversationSession(
  paperId: string,
  title: string,
): Promise<ConversationSession> {
  return requestJson<ConversationSession>(
    `/api/papers/${encodeURIComponent(paperId)}/sessions`,
    "阅读会话创建失败",
    jsonOptions("POST", { title }),
  );
}

export async function searchPaper(
  paperId: string,
  query: string,
  mode: SearchMode,
  limit = 5,
  scopePreference: ScopePreference = "auto",
): Promise<PaperSearchExecution> {
  const response = await requestResponse(
    `/api/papers/${encodeURIComponent(paperId)}/search`,
    "证据检索失败",
    jsonOptions("POST", { query, mode, limit, scope_preference: scopePreference }),
  );

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
  return requestJson<PaperAnswer>(
    `/api/papers/${encodeURIComponent(paperId)}/answer`,
    "论文回答生成失败",
    jsonOptions("POST", {
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
  );
}

export async function previewSelectionContext(
  paperId: string,
  sourcePage: number,
  selectedText: string,
  targetLanguage: GlossaryEntry["target_language"] = "zh-CN",
): Promise<SelectionContextPreview> {
  return requestJson<SelectionContextPreview>(
    `/api/papers/${encodeURIComponent(paperId)}/selection-context`,
    "选区上下文读取失败",
    jsonOptions("POST", {
      source_page: sourcePage,
      selected_text: selectedText,
      target_language: targetLanguage,
    }),
  );
}

export async function listReadingHistory(
  paperId: string,
  sessionId?: string,
): Promise<ReadingRecord[]> {
  const query = sessionId
    ? `?session_id=${encodeURIComponent(sessionId)}`
    : "";
  return requestJson<ReadingRecord[]>(
    `/api/papers/${encodeURIComponent(paperId)}/history${query}`,
    "阅读记录加载失败",
  );
}

export async function updateReadingRecord(
  paperId: string,
  recordId: string,
  confirmed: boolean,
  personalNote: string,
  category: ReadingCategory,
): Promise<ReadingRecord> {
  return requestJson<ReadingRecord>(
    `/api/papers/${encodeURIComponent(paperId)}/history/${encodeURIComponent(recordId)}`,
    "阅读记录保存失败",
    jsonOptions("PATCH", {
      confirmed,
      personal_note: personalNote,
      category,
    }),
  );
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
  return requestJson<PaperCardPreview>(
    `/api/papers/${encodeURIComponent(paperId)}/card/preview`,
    "论文卡片预览生成失败",
  );
}

export async function downloadPaperCard(
  paperId: string,
  paperName: string,
  newVersion: boolean,
): Promise<void> {
  const response = await requestResponse(
    `/api/papers/${encodeURIComponent(paperId)}/card/export?new_version=${newVersion}`,
    "论文卡片导出失败",
    { method: "POST" },
  );

  const downloadUrl = URL.createObjectURL(await response.blob());
  const link = document.createElement("a");
  link.href = downloadUrl;
  link.download = `${paperName.replace(/\.pdf$/i, "")}.md`;
  document.body.appendChild(link);
  link.click();
  link.remove();
  URL.revokeObjectURL(downloadUrl);
}
