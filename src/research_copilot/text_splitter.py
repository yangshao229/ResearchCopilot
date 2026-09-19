def chunk_pages(
    pages: list[dict[str, int | str]],
    chunk_size: int = 1000,
    overlap: int = 100,
) -> list[dict[str, int | str]]:
    if chunk_size <= 0:
        raise ValueError("chunk_size must be greater than 0")
    if overlap < 0 or overlap >= chunk_size:
        raise ValueError(" overlap must be between 0 and chunk_size")
    chunks: list[dict[str, int | str]] = []

    for page in pages:
        source_page = int(page["source_page"])
        text = str(page["text"]).strip()

        if not text:
            continue

        start = 0
        chunk_index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            chunk_text = text[start:end]

            chunks.append(
                {
                    "source_page": source_page,
                    "chunk_index": chunk_index,
                    "text": chunk_text,
                }
            )

            if end == len(text):
                break

            start = end - overlap
            chunk_index += 1

    return chunks
