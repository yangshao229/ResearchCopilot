def search_chunks(
    query: str,
    chunks: list[dict[str, int | str]],
    limit: int = 5,
) -> list[dict[str, int | str]]:
    if limit <= 0:
        return []

    terms = [term for term in query.casefold().split() if term]

    if not terms:
        return []

    results: list[dict[str, int | str]] = []

    for chunk in chunks:
        text = str(chunk["text"]).casefold()
        score = sum(text.count(term) for term in terms)

        if score > 0:
            results.append(
                {
                    **chunk,
                    "score": score,
                }
            )

    results.sort(
        key=lambda item: (
            -int(item["score"]),
            int(item["source_page"]),
            int(item["chunk_index"]),
        )
    )

    return results[:limit]