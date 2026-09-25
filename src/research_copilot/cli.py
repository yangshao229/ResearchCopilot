import argparse
import threading
import webbrowser
from pathlib import Path

from dotenv import load_dotenv

from research_copilot.paper_card import write_paper_card
from research_copilot.paper_library import DEFAULT_PAPER_DIRECTORY, PROJECT_ROOT
from research_copilot.paper_search import (
    search_page_data,
    semantic_search_page_data,
)
from research_copilot.pdf_importer import import_pdf_to_json
from research_copilot.semantic_retriever import DEFAULT_EMBEDDING_MODEL


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="research-copilot",
        description="Import and search research papers.",
    )

    subparsers = parser.add_subparsers(
        dest="command",
        required=True,
    )

    import_parser = subparsers.add_parser(
        "import",
        help="Import a PDF as page-aware JSON.",
    )
    import_parser.add_argument(
        "pdf_path",
        type=Path,
    )
    import_parser.add_argument(
        "output_path",
        type=Path,
    )

    card_parser = subparsers.add_parser(
        "card",
        help="Create a human-reviewable Obsidian Markdown draft.",
    )
    card_parser.add_argument(
        "page_data_path",
        type=Path,
    )
    card_parser.add_argument(
        "output_path",
        type=Path,
    )

    search_parser = subparsers.add_parser(
        "search",
        help="Search an imported paper.",
    )
    search_parser.add_argument(
        "page_data_path",
        type=Path,
    )
    search_parser.add_argument("query")
    search_parser.add_argument(
        "--limit",
        type=int,
        default=5,
    )
    search_parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
    )
    search_parser.add_argument(
        "--overlap",
        type=int,
        default=100,
    )

    semantic_parser = subparsers.add_parser(
        "semantic-search",
        help="Search an imported paper with multilingual embeddings.",
    )
    semantic_parser.add_argument(
        "page_data_path",
        type=Path,
    )
    semantic_parser.add_argument("query")
    semantic_parser.add_argument(
        "--limit",
        type=int,
        default=5,
    )
    semantic_parser.add_argument(
        "--chunk-size",
        type=int,
        default=1000,
    )
    semantic_parser.add_argument(
        "--overlap",
        type=int,
        default=100,
    )
    semantic_parser.add_argument(
        "--model",
        default=DEFAULT_EMBEDDING_MODEL,
    )

    serve_parser = subparsers.add_parser(
        "serve",
        help="Start the local paper-reading web app.",
    )
    serve_parser.add_argument(
        "--host",
        default="127.0.0.1",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=8000,
    )
    serve_parser.add_argument(
        "--paper-directory",
        type=Path,
        default=DEFAULT_PAPER_DIRECTORY,
    )
    serve_parser.add_argument(
        "--no-open",
        action="store_true",
        help="Do not open the reading workspace in the default browser.",
    )

    return parser


def main() -> None:
    args = build_parser().parse_args()

    if args.command == "import":
        import_pdf_to_json(
            args.pdf_path,
            args.output_path,
        )
        print(
            f"Imported {args.pdf_path.name} "
            f"-> {args.output_path}"
        )
        return

    if args.command == "card":
        write_paper_card(
            args.page_data_path,
            args.output_path,
        )
        print(
            f"Created review draft -> {args.output_path}"
        )
        return

    if args.command == "serve":
        import uvicorn

        from research_copilot.web_app import create_app

        load_dotenv(PROJECT_ROOT / ".env")
        if not args.no_open:
            workspace_url = f"http://{args.host}:{args.port}/"
            threading.Timer(0.8, webbrowser.open, args=(workspace_url,)).start()
        uvicorn.run(
            create_app(args.paper_directory),
            host=args.host,
            port=args.port,
        )
        return

    if args.command == "semantic-search":
        results = semantic_search_page_data(
            args.page_data_path,
            args.query,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            limit=args.limit,
            model_name=args.model,
        )
    else:
        results = search_page_data(
            args.page_data_path,
            args.query,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
            limit=args.limit,
        )

    if not results:
        print("No matches found.")
        return

    for result in results:
        score = result["score"]
        score_text = f"{score:.4f}" if isinstance(score, float) else str(score)
        print(
            f'Page {result["source_page"]} '
            f"| score={score_text}"
        )
        print(result["text"])
        print()
