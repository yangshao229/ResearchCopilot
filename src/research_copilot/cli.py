import argparse
import ipaddress
import socket
import threading
import time
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


DEFAULT_SERVER_PORT = 8000
MAX_PORT_ATTEMPTS = 20


def _require_loopback_host(host: str) -> None:
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is None or not address.is_loopback:
        raise ValueError(
            "当前自测版没有账号认证，只允许监听本机回环地址，"
            "例如 127.0.0.1、localhost 或 ::1。"
        )


def _port_is_available(host: str, port: int) -> bool:
    family = socket.AF_INET6 if ":" in host else socket.AF_INET
    try:
        with socket.socket(family, socket.SOCK_STREAM) as probe:
            probe.bind((host, port))
    except PermissionError as error:
        raise ValueError(
            "系统拒绝监听本地端口；请检查终端或运行环境的网络权限。"
        ) from error
    except OSError:
        return False
    return True


def select_server_port(host: str, requested_port: int | None) -> int:
    _require_loopback_host(host)
    if requested_port is not None:
        if not _port_is_available(host, requested_port):
            raise ValueError(f"端口 {requested_port} 已被占用，请选择其他端口。")
        return requested_port

    for port in range(DEFAULT_SERVER_PORT, DEFAULT_SERVER_PORT + MAX_PORT_ATTEMPTS):
        if _port_is_available(host, port):
            return port
    raise ValueError("本地端口 8000–8019 均不可用，无法启动阅读器。")


def _open_browser_when_ready(server: object, url: str) -> None:
    for _ in range(150):
        if getattr(server, "started", False):
            webbrowser.open(url)
            return
        if getattr(server, "should_exit", False):
            return
        time.sleep(0.1)


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
        help="Loopback address only; this self-test version has no authentication.",
    )
    serve_parser.add_argument(
        "--port",
        type=int,
        default=None,
        help="Use a specific port; by default choose the first free port from 8000 to 8019.",
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
    parser = build_parser()
    args = parser.parse_args()

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
        try:
            port = select_server_port(args.host, args.port)
        except ValueError as error:
            parser.error(str(error))

        browser_host = args.host
        if ":" in browser_host:
            browser_host = f"[{browser_host}]"
        workspace_url = f"http://{browser_host}:{port}/"
        server = uvicorn.Server(
            uvicorn.Config(create_app(args.paper_directory), host=args.host, port=port)
        )
        print(f"ResearchCopilot: {workspace_url}", flush=True)
        if port != DEFAULT_SERVER_PORT and args.port is None:
            print("端口 8000 已被其他服务占用，已自动选择可用端口。", flush=True)
        if not args.no_open:
            threading.Thread(
                target=_open_browser_when_ready,
                args=(server, workspace_url),
                daemon=True,
            ).start()
        try:
            server.run()
        except KeyboardInterrupt:
            pass
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
