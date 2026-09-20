export type Paper = {
  id: string;
  name: string;
  relative_path: string;
  page_count: number | null;
};

export type SearchMode = "keyword" | "semantic";

export type SearchResult = {
  source_page: number;
  chunk_index: number;
  text: string;
  score: number;
};

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
    throw new Error(`证据检索失败：${response.status}`);
  }

  return (await response.json()) as SearchResult[];
}
