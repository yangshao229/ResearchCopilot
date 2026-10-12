import sys
from hashlib import sha256
from pathlib import Path

import pytest
from pypdf import PdfWriter

import research_copilot.cli as cli
from research_copilot.cli import main
from research_copilot.page_store import (
    load_page_data,
    save_page_data,
)


def test_server_uses_next_free_port_when_default_is_busy(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_port_is_available", lambda _host, port: port == 8001)

    assert cli.select_server_port("127.0.0.1", None) == 8001


@pytest.mark.parametrize("host", ["0.0.0.0", "::", "192.168.1.10", "example.com"])
def test_server_refuses_non_loopback_host(host: str, monkeypatch) -> None:
    monkeypatch.setattr(
        cli,
        "_port_is_available",
        lambda _host, _port: pytest.fail("must reject before opening a socket"),
    )

    with pytest.raises(ValueError, match="没有账号认证"):
        cli.select_server_port(host, None)


@pytest.mark.parametrize("host", ["127.0.0.1", "localhost", "::1"])
def test_server_accepts_loopback_host(host: str, monkeypatch) -> None:
    monkeypatch.setattr(cli, "_port_is_available", lambda _host, _port: True)

    assert cli.select_server_port(host, 8765) == 8765


def test_explicit_server_port_does_not_silently_change(monkeypatch) -> None:
    monkeypatch.setattr(cli, "_port_is_available", lambda _host, _port: False)

    with pytest.raises(ValueError, match="8765"):
        cli.select_server_port("127.0.0.1", 8765)


def test_server_reports_socket_permission_denial_not_port_conflict(monkeypatch) -> None:
    def reject_socket(*_args: object) -> None:
        raise PermissionError("Operation not permitted")

    monkeypatch.setattr(cli.socket, "socket", reject_socket)

    with pytest.raises(ValueError, match="网络权限"):
        cli.select_server_port("127.0.0.1", None)


def test_browser_opens_only_after_server_is_ready(monkeypatch) -> None:
    opened: list[str] = []
    monkeypatch.setattr(cli.webbrowser, "open", opened.append)
    server = type("FakeServer", (), {"started": True, "should_exit": False})()

    cli._open_browser_when_ready(server, "http://127.0.0.1:8001/")

    assert opened == ["http://127.0.0.1:8001/"]


def test_import_command_creates_page_data(
    tmp_path: Path,
    monkeypatch,
) -> None:
    pdf_path = tmp_path / "paper.pdf"
    output_path = tmp_path / "paper.json"

    writer = PdfWriter()
    writer.add_blank_page(width=72, height=72)

    with pdf_path.open("wb") as pdf_file:
        writer.write(pdf_file)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "import",
            str(pdf_path),
            str(output_path),
        ],
    )

    main()

    assert load_page_data(output_path) == {
        "source_pdf": "paper.pdf",
        "source_pdf_sha256": sha256(pdf_path.read_bytes()).hexdigest(),
        "pages": [
            {
                "source_page": 1,
                "text": "",
            }
        ],
    }


def test_search_command_prints_page_citation(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    page_data_path = tmp_path / "paper.json"

    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [
                {
                    "source_page": 1,
                    "text": "Attention connects tokens.",
                },
                {
                    "source_page": 2,
                    "text": "Attention uses attention weights.",
                },
            ],
        },
        page_data_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "search",
            str(page_data_path),
            "attention",
            "--chunk-size",
            "100",
            "--overlap",
            "0",
        ],
    )

    main()

    output = capsys.readouterr().out

    assert "Page 2 | score=2" in output
    assert "Attention uses attention weights." in output


def test_card_command_creates_markdown_draft(
    tmp_path: Path,
    monkeypatch,
) -> None:
    page_data_path = tmp_path / "paper.json"
    output_path = tmp_path / "paper.md"
    save_page_data(
        {
            "source_pdf": "paper.pdf",
            "pages": [],
        },
        page_data_path,
    )

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "research-copilot",
            "card",
            str(page_data_path),
            str(output_path),
        ],
    )

    main()

    markdown = output_path.read_text(encoding="utf-8")
    assert 'status: "draft-needs-human-review"' in markdown
