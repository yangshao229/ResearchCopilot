"""Pure, page-bounded context windows for offline retrieval diagnostics."""

from __future__ import annotations

from collections.abc import Mapping, Sequence


def expand_candidate_neighbours(
    hits: Sequence[Mapping[str, int | float | str]],
    chunks: Sequence[Mapping[str, int | str]],
    *,
    before: int = 0,
    after: int = 0,
) -> list[dict[str, int | float | str]]:
    """Add page-bounded neighbouring chunks to an internal rerank pool.

    Existing hits keep their order and metadata. Neighbours are appended in
    hit order and remain independent chunks, so a caller can still enforce an
    unchanged final Top-k evidence budget after reranking.
    """
    if before < 0 or after < 0:
        raise ValueError("Neighbour counts must be non-negative.")

    indexed = {
        (int(chunk["source_page"]), int(chunk["chunk_index"])): chunk
        for chunk in chunks
    }
    selected = [dict(hit) for hit in hits]
    seen: set[tuple[int, int]] = set()
    for hit in hits:
        key = (int(hit["source_page"]), int(hit["chunk_index"]))
        chunk = indexed.get(key)
        if chunk is None or str(chunk["text"]) != str(hit["text"]):
            raise ValueError("Retrieved chunk does not match the current PDF page data.")
        seen.add(key)

    for hit in hits:
        page = int(hit["source_page"])
        index = int(hit["chunk_index"])
        neighbour_indexes = [
            *(index - offset for offset in range(1, before + 1)),
            *(index + offset for offset in range(1, after + 1)),
        ]
        for neighbour_index in neighbour_indexes:
            key = (page, neighbour_index)
            neighbour = indexed.get(key)
            if neighbour is None or key in seen:
                continue
            selected.append(dict(neighbour))
            seen.add(key)
    return selected


def window_text(
    hit: Mapping[str, int | float | str],
    chunks: Sequence[Mapping[str, int | str]],
    *,
    before: int = 0,
    after: int = 0,
    overlap: int = 100,
) -> str:
    """Expand a retrieved chunk only to its immediate neighbours on the same PDF page."""
    if before < 0 or after < 0 or overlap < 0:
        raise ValueError("Window sizes and overlap must be non-negative.")

    page = int(hit["source_page"])
    index = int(hit["chunk_index"])
    same_page = {
        int(chunk["chunk_index"]): str(chunk["text"])
        for chunk in chunks
        if int(chunk["source_page"]) == page
    }
    selected = same_page.get(index)
    if selected is None or selected != str(hit["text"]):
        raise ValueError("Retrieved chunk does not match the current PDF page data.")

    indexes = [index]
    for offset in range(1, before + 1):
        previous = index - offset
        if previous not in same_page:
            break
        indexes.insert(0, previous)
    for offset in range(1, after + 1):
        following = index + offset
        if following not in same_page:
            break
        indexes.append(following)

    assembled = same_page[indexes[0]]
    for neighbour in indexes[1:]:
        following_text = same_page[neighbour]
        if (
            overlap
            and len(assembled) >= overlap
            and len(following_text) >= overlap
            and assembled[-overlap:] == following_text[:overlap]
        ):
            assembled += following_text[overlap:]
        else:
            assembled += "\n" + following_text
    return assembled


def contains_support(
    texts: Sequence[str], required_phrases: Sequence[str]
) -> bool | None:
    """Diagnostic only: exact human-selected spans, not a general answerability gate."""
    if not required_phrases:
        return None
    if any(not phrase.strip() for phrase in required_phrases):
        raise ValueError("Support phrases must not be empty.")
    normalized_texts = [" ".join(text.split()).casefold() for text in texts]
    return all(
        any(" ".join(phrase.split()).casefold() in text for text in normalized_texts)
        for phrase in required_phrases
    )


def contains_support_on_one_page(
    hits: Sequence[Mapping[str, int | float | str]],
    texts: Sequence[str],
    required_phrases: Sequence[str],
) -> bool | None:
    """Do not combine unrelated PDF pages into a single answer-bearing span."""
    if len(hits) != len(texts):
        raise ValueError("Hits and context texts must have the same length.")
    if not required_phrases:
        return None
    by_page: dict[int, list[str]] = {}
    for hit, item_text in zip(hits, texts, strict=True):
        by_page.setdefault(int(hit["source_page"]), []).append(item_text)
    return any(contains_support(page_texts, required_phrases) for page_texts in by_page.values())
