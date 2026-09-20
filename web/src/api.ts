export type Paper = {
  id: string;
  name: string;
  relative_path: string;
  page_count: number | null;
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
