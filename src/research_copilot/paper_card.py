import json
from pathlib import Path

from research_copilot.page_store import load_page_data


def build_paper_card(page_data: dict[str, object]) -> str:
    source_pdf = str(page_data.get("source_pdf", "unknown.pdf"))
    title = Path(source_pdf).stem
    raw_pages = page_data.get("pages")

    if not isinstance(raw_pages, list):
        raise ValueError("page data must contain a pages list")

    lines = [
        "---",
        f"title: {json.dumps(title, ensure_ascii=False)}",
        f"source_pdf: {json.dumps(source_pdf, ensure_ascii=False)}",
        'status: "draft-needs-human-review"',
        "human_confirmed: false",
        "---",
        "",
        f"# {title}",
        "",
        "> [!warning] Human review required",
        "> This draft was generated automatically. Confirm every claim before moving it into formal notes.",
        "",
        "## Review checklist",
        "",
        "- [ ] Confirm title and bibliographic metadata",
        "- [ ] State the research question",
        "- [ ] Summarize the method",
        "- [ ] Verify key findings against cited pages",
        "- [ ] Add limitations and personal notes",
        "",
        "## Research question",
        "",
        "_TODO: confirm manually._",
        "",
        "## Method",
        "",
        "_TODO: confirm manually._",
        "",
        "## Key findings",
        "",
        "_TODO: confirm manually and cite pages._",
        "",
        "## Page index",
        "",
    ]

    for raw_page in raw_pages:
        if not isinstance(raw_page, dict):
            raise ValueError("each page must be a dictionary")

        page_number = int(raw_page["source_page"])
        text = " ".join(str(raw_page.get("text", "")).split())
        preview = text[:240] if text else "(no extractable text)"
        lines.append(
            f"- [[{source_pdf}#page={page_number}|Page {page_number}]] — {preview}"
        )

    return "\n".join(lines) + "\n"


def write_paper_card(page_data_path: Path, output_path: Path) -> None:
    if output_path.exists():
        raise FileExistsError(f"Refusing to overwrite existing note: {output_path}")

    page_data = load_page_data(page_data_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        build_paper_card(page_data),
        encoding="utf-8",
    )
