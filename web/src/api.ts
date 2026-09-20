export type Paper = {
  id: string;
  name: string;
  relative_path: string;
  page_count: number | null;
};

export type SearchMode = "keyword" | "semantic" | "hybrid";

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

export function paperFileUrl(paperId: string): string {
  return `/api/papers/${encodeURIComponent(paperId)}/file`;
}

export async function searchPaper(
  paperId: string,
  query: string,
  mode: SearchMode,
  limit = 5,
): Promise<SearchResult[]> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/search`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, mode, limit }),
    },
  );

  if (!response.ok) {
    throw await responseError(response, "证据检索失败");
  }

  return (await response.json()) as SearchResult[];
}

export async function answerPaper(
  paperId: string,
  query: string,
  mode: SearchMode,
  limit = 5,
): Promise<PaperAnswer> {
  const response = await fetch(
    `/api/papers/${encodeURIComponent(paperId)}/answer`,
    {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query, mode, limit }),
    },
  );

  if (!response.ok) {
    throw await responseError(response, "论文回答生成失败");
  }

  return (await response.json()) as PaperAnswer;
}
