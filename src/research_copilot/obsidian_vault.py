"""Inspect a selected Obsidian vault and create explicitly approved notes."""

from __future__ import annotations

import json
import os
import re
from hashlib import sha256
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4

import yaml
from pydantic import BaseModel, Field

from research_copilot.domain import ReadingRecord, SourceDocumentRef
from research_copilot.paper_library import PaperSummary
from research_copilot.storage import atomic_write_json


MAX_NOTE_BYTES = 1_000_000
MAX_NOTES = 2_000
SHA256_PATTERN = re.compile(r"^[0-9a-fA-F]{64}$")
SAFE_RECORD_ID = re.compile(r"^[A-Za-z0-9_-]{1,80}$")
PAPER_UID_PATTERN = re.compile(r"^paper-[0-9a-f]{32}$")


def _escape_link_label(value: str) -> str:
    return value.replace("\\", "\\\\").replace("[", "\\[").replace("]", "\\]")


class VaultNote(BaseModel):
    path: str
    kind: str
    uid: str
    title: str
    paper_uid: str | None = None
    pdf_sha256: str | None = None


class VaultIssue(BaseModel):
    path: str
    message: str


class VaultStatus(BaseModel):
    connected: bool
    path: str | None = None
    notes: list[VaultNote] = Field(default_factory=list)
    issues: list[VaultIssue] = Field(default_factory=list)
    legacy_card_count: int = 0


class VaultNotePreview(BaseModel):
    relative_path: str
    markdown: str
    sha256: str
    already_exists: bool


class VaultDocument(BaseModel):
    note: VaultNote
    markdown: str
    sha256: str


class VaultCatalogPreview(BaseModel):
    new_sources: list[str]
    existing_count: int
    base_will_create: bool
    sha256: str


CATALOG_BASE_NAME = "ResearchCopilot 论文库.base"
CATALOG_BASE = (
    "filters:\n"
    "  and:\n"
    "    - 'file.inFolder(\"Sources\")'\n"
    "    - 'kind == \"paper_source\"'\n"
    "views:\n"
    "  - type: table\n"
    "    name: 论文库\n"
    "    order:\n"
    "      - file.name\n"
    "      - title\n"
    "      - reading_status\n"
    "      - page_count\n"
    "      - source_language\n"
)


class _UniqueKeyLoader(yaml.SafeLoader):
    pass


def _unique_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode) -> dict:
    result: dict = {}
    for key_node, value_node in node.value:
        key = loader.construct_object(key_node)
        if key in result:
            raise ValueError(f"YAML 属性重复：{key}")
        result[key] = loader.construct_object(value_node)
    return result


_UniqueKeyLoader.add_constructor(
    yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _unique_mapping
)


def _read_note(path: Path, relative_path: str) -> VaultNote:
    if path.stat().st_size > MAX_NOTE_BYTES:
        raise ValueError("笔记超过 1 MB，本轮只读校验已跳过")
    content = path.read_text(encoding="utf-8-sig")
    lines = content.splitlines()
    if not lines or lines[0] != "---":
        raise ValueError("缺少 YAML 属性；旧笔记不会自动当作已确认知识")
    try:
        end = lines.index("---", 1)
    except ValueError as error:
        raise ValueError("YAML 属性没有结束标记") from error
    try:
        fields = yaml.load("\n".join(lines[1:end]), Loader=_UniqueKeyLoader)
    except (yaml.YAMLError, ValueError, TypeError) as error:
        raise ValueError(f"YAML 无法解析：{error}") from error
    if not isinstance(fields, dict):
        raise ValueError("YAML 属性必须是字段列表")
    kind = fields.get("kind")
    schema_version = fields.get("schema_version")
    if (
        type(schema_version) is not int
        or schema_version != 1
        or kind not in {"paper", "reading_note", "paper_source"}
    ):
        raise ValueError("不是 ResearchCopilot v1 论文卡或阅读笔记；原文件未改动")
    uid = fields.get("uid")
    if not isinstance(uid, str) or not uid.strip():
        raise ValueError("缺少有效 uid")
    if kind in {"paper", "paper_source"}:
        title = fields.get("title")
        fingerprint = fields.get("pdf_sha256")
        if not isinstance(title, str) or not title.strip():
            raise ValueError("论文卡缺少标题")
        if not isinstance(fingerprint, str) or not SHA256_PATTERN.fullmatch(fingerprint):
            raise ValueError("论文卡缺少有效 PDF SHA-256 指纹")
        if kind == "paper_source" and (
            not isinstance(fields.get("paper_uid"), str)
            or not PAPER_UID_PATTERN.fullmatch(fields["paper_uid"])
            or uid != f"source-{fields['paper_uid']}"
        ):
            raise ValueError("论文来源缺少有效 paper_uid 或 uid 不匹配")
    else:
        if fields.get("review_status") != "confirmed":
            raise ValueError("阅读笔记尚未人工确认")
        if not isinstance(fields.get("paper_uid"), str) or not fields["paper_uid"].strip():
            raise ValueError("阅读笔记缺少 paper_uid")
        title = fields.get("title") or uid
    return VaultNote(
        path=relative_path,
        kind=kind,
        uid=uid.strip(),
        title=str(title).strip(),
        paper_uid=(
            fields["paper_uid"].strip() if kind in {"reading_note", "paper_source"}
            else uid.strip()
        ),
        pdf_sha256=fields.get("pdf_sha256") if kind in {"paper", "paper_source"} else None,
    )


class ObsidianVaultStore:
    def __init__(self, config_path: Path, legacy_card_directory: Path) -> None:
        self.config_path = config_path
        self.legacy_card_directory = legacy_card_directory

    def connect(self, raw_path: str) -> VaultStatus:
        if not raw_path.strip():
            raise ValueError("请填写 Obsidian Vault 文件夹的完整路径。")
        selected = Path(raw_path).expanduser()
        if not selected.is_absolute():
            raise ValueError("请填写 Vault 文件夹的完整路径，而不是相对路径。")
        root = selected.resolve(strict=True)
        if not root.is_dir() or not (root / ".obsidian").is_dir():
            raise ValueError("所选文件夹不是已创建的 Obsidian Vault（缺少 .obsidian）。")
        status = self._scan(root)
        atomic_write_json(self.config_path, {"path": str(root)})
        return status

    def disconnect(self) -> VaultStatus:
        self.config_path.unlink(missing_ok=True)
        return self.status()

    def status(self) -> VaultStatus:
        if not self.config_path.exists():
            return VaultStatus(connected=False, legacy_card_count=self._legacy_count())
        try:
            configured = json.loads(self.config_path.read_text(encoding="utf-8"))
            root = Path(configured["path"]).resolve(strict=True)
            if not root.is_dir() or not (root / ".obsidian").is_dir():
                raise ValueError("已连接的 Vault 文件夹不再可用")
            return self._scan(root)
        except (OSError, ValueError, KeyError, TypeError) as error:
            return VaultStatus(
                connected=False,
                issues=[VaultIssue(path="", message=str(error))],
                legacy_card_count=self._legacy_count(),
            )

    def read_document(self, paper_uid: str, uid: str) -> VaultDocument:
        root = self._connected_root()
        status = self._scan(root)
        if status.issues:
            raise ValueError("Vault 中有未通过校验的文件；请先在知识库面板查看问题。")
        note = next(
            (item for item in status.notes if item.uid == uid and item.paper_uid == paper_uid),
            None,
        )
        if note is None:
            raise KeyError(uid)
        source = root / note.path
        if source.is_symlink() or not source.resolve(strict=True).is_relative_to(root):
            raise ValueError("笔记位置已改变，拒绝读取。")
        payload = source.read_bytes()
        if len(payload) > MAX_NOTE_BYTES:
            raise ValueError("笔记超过 1 MB，拒绝读取。")
        current = _read_note(source, note.path)
        if current != note or source.read_bytes() != payload:
            raise ValueError("笔记在读取期间发生变化，请重试。")
        return VaultDocument(
            note=current,
            markdown=payload.decode("utf-8-sig"),
            sha256=sha256(payload).hexdigest(),
        )

    def preview_source_catalog(self, papers: list[PaperSummary]) -> VaultCatalogPreview:
        root = self._connected_root()
        status = self._scan(root)
        if status.issues:
            raise ValueError("Vault 中有未通过校验的文件；请先检查知识库面板。")
        existing = {note.uid: note for note in status.notes}
        new_sources: list[str] = []
        digest = sha256(str(root).encode("utf-8"))
        seen: set[str] = set()
        for paper in sorted(papers, key=lambda item: item.paper_uid or ""):
            self._validate_paper(paper)
            if paper.page_count is None:
                raise ValueError(f"无法读取 PDF 页数：{paper.name}")
            assert paper.paper_uid is not None and paper.pdf_sha256 is not None
            if paper.paper_uid in seen:
                raise ValueError(f"论文身份重复：{paper.paper_uid}")
            seen.add(paper.paper_uid)
            relative = f"Sources/{paper.paper_uid}.md"
            target = self._target_path(root, relative, create_directory=False)
            uid = f"source-{paper.paper_uid}"
            if target.is_symlink():
                raise ValueError(f"来源文件是符号链接：{relative}")
            if target.exists():
                note = _read_note(target, relative)
                if (
                    note.kind != "paper_source" or note.uid != uid
                    or note.paper_uid != paper.paper_uid
                    or note.pdf_sha256 != paper.pdf_sha256
                ):
                    raise ValueError(f"来源文件与当前 PDF 不一致：{relative}")
                digest.update(target.read_bytes())
            else:
                if uid in existing:
                    raise ValueError(f"Vault 中已有重复的论文来源 UID：{uid}")
                new_sources.append(relative)
                digest.update(self._render_paper_source(paper).encode("utf-8"))
            digest.update(relative.encode("utf-8"))
        base_path = root / CATALOG_BASE_NAME
        if base_path.is_symlink() or (base_path.exists() and not base_path.is_file()):
            raise ValueError("论文库 Bases 文件不是普通文件，拒绝覆盖。")
        base_will_create = not base_path.exists()
        digest.update(base_path.read_bytes() if base_path.exists() else CATALOG_BASE.encode("utf-8"))
        return VaultCatalogPreview(
            new_sources=new_sources,
            existing_count=len(papers) - len(new_sources),
            base_will_create=base_will_create,
            sha256=digest.hexdigest(),
        )

    def save_source_catalog(
        self, papers: list[PaperSummary], expected_sha256: str
    ) -> VaultStatus:
        preview = self.preview_source_catalog(papers)
        if preview.sha256 != expected_sha256:
            raise ValueError("论文或 Vault 在预览后发生变化，请重新预览。")
        root = self._connected_root()
        by_uid = {paper.paper_uid: paper for paper in papers}
        for relative in preview.new_sources:
            uid = Path(relative).stem
            paper = by_uid[uid]
            note_preview = VaultNotePreview(
                relative_path=relative,
                markdown=self._render_paper_source(paper),
                sha256="",
                already_exists=False,
            )
            self._create_previewed_note(root, note_preview, f"source-{uid}")
        if preview.base_will_create:
            self._create_exclusive_file(root / CATALOG_BASE_NAME, CATALOG_BASE)
        return self._scan(root)

    def preview_reading_note(
        self, paper: PaperSummary, record: ReadingRecord
    ) -> VaultNotePreview:
        root = self._connected_root()
        self._validate_record(paper, record)
        relative_path = f"Notes/record-{record.id}.md"
        target = self._target_path(root, relative_path, create_directory=False)
        markdown = self._render_reading_note(paper, record)
        if len(markdown.encode("utf-8")) > MAX_NOTE_BYTES:
            raise ValueError("阅读笔记超过 1 MB，无法写入 Vault。")
        return VaultNotePreview(
            relative_path=relative_path,
            markdown=markdown,
            sha256=self._preview_digest(root, markdown),
            already_exists=target.exists() or target.is_symlink(),
        )

    def save_reading_note(
        self, paper: PaperSummary, record: ReadingRecord, expected_sha256: str
    ) -> VaultNote:
        preview = self.preview_reading_note(paper, record)
        if preview.sha256 != expected_sha256:
            raise ValueError("阅读记录或 PDF 在预览后发生变化，请重新预览。")
        if preview.already_exists:
            raise FileExistsError("这条笔记已在 Vault 中；当前版本不会覆盖 Obsidian 文件。")
        root = self._connected_root()
        return self._create_previewed_note(root, preview, f"record-{record.id}")

    def preview_paper_card(self, paper: PaperSummary) -> VaultNotePreview:
        root = self._connected_root()
        self._validate_paper(paper)
        status = self._scan(root)
        if status.issues:
            raise ValueError("Vault 中仍有未通过校验的文件；修复后才能创建正式论文卡。")
        linked_notes = sorted(
            (
                note for note in status.notes
                if note.kind == "reading_note" and note.paper_uid == paper.paper_uid
            ),
            key=lambda note: note.path,
        )
        if not linked_notes:
            raise ValueError("请先将至少一条已确认的阅读笔记保存到 Obsidian。")
        relative_path = f"Papers/{paper.paper_uid}.md"
        target = self._target_path(root, relative_path, create_directory=False)
        markdown = self._render_paper_card(paper, linked_notes)
        if len(markdown.encode("utf-8")) > MAX_NOTE_BYTES:
            raise ValueError("论文卡超过 1 MB，无法写入 Vault。")
        return VaultNotePreview(
            relative_path=relative_path,
            markdown=markdown,
            sha256=self._preview_digest(
                root, markdown, self._linked_note_fingerprint(root, linked_notes)
            ),
            already_exists=target.exists() or target.is_symlink(),
        )

    def save_paper_card(self, paper: PaperSummary, expected_sha256: str) -> VaultNote:
        preview = self.preview_paper_card(paper)
        if preview.sha256 != expected_sha256:
            raise ValueError("入库笔记或 PDF 在预览后发生变化，请重新预览论文卡。")
        if preview.already_exists:
            raise FileExistsError("论文卡已在 Vault 中；当前版本不会覆盖 Obsidian 文件。")
        root = self._connected_root()
        return self._create_previewed_note(root, preview, paper.paper_uid)

    def _create_previewed_note(
        self, root: Path, preview: VaultNotePreview, uid: str
    ) -> VaultNote:
        vault_status = self._scan(root)
        if vault_status.issues:
            raise ValueError("Vault 中仍有未通过校验的文件；修复后才能写入正式笔记。")
        if any(note.uid == uid for note in vault_status.notes):
            raise FileExistsError("Vault 中已有相同 UID 的笔记，拒绝重复写入。")
        target = self._target_path(root, preview.relative_path, create_directory=True)
        self._create_exclusive_file(target, preview.markdown)
        return _read_note(target, preview.relative_path)

    @staticmethod
    def _create_exclusive_file(target: Path, content: str) -> None:
        temporary = target.with_name(f".{target.name}.{uuid4().hex}.tmp")
        try:
            with temporary.open("x", encoding="utf-8", newline="\n") as output:
                output.write(content)
                output.flush()
                os.fsync(output.fileno())
            os.link(temporary, target)  # Atomic create-if-absent; never replaces a note.
        finally:
            temporary.unlink(missing_ok=True)

    def _connected_root(self) -> Path:
        if not self.config_path.exists():
            raise ValueError("尚未连接 Obsidian Vault。")
        configured = json.loads(self.config_path.read_text(encoding="utf-8"))
        root = Path(configured["path"]).resolve(strict=True)
        if not root.is_dir() or not (root / ".obsidian").is_dir():
            raise ValueError("已连接的 Obsidian Vault 不再可用。")
        return root

    @staticmethod
    def _target_path(root: Path, relative_path: str, *, create_directory: bool) -> Path:
        folder_name, filename = relative_path.split("/", 1)
        if (
            folder_name not in {"Notes", "Papers", "Sources"}
            or Path(filename).name != filename
            or filename in {".", ".."}
            or not filename.endswith(".md")
        ):
            raise ValueError("Vault 笔记路径无效。")
        directory = root / folder_name
        if directory.is_symlink() or (directory.exists() and not directory.is_dir()):
            raise ValueError(f"Vault 的 {folder_name} 不是普通文件夹，拒绝写入。")
        if create_directory:
            directory.mkdir(exist_ok=True)
        return directory / filename

    @staticmethod
    def _validate_paper(paper: PaperSummary) -> None:
        if (
            not paper.paper_uid
            or not PAPER_UID_PATTERN.fullmatch(paper.paper_uid)
            or not paper.pdf_sha256
            or not SHA256_PATTERN.fullmatch(paper.pdf_sha256)
            or paper.pdf_version_status != "current"
        ):
            raise ValueError("论文身份或 PDF 版本待核对，不能正式入库。")

    @staticmethod
    def _validate_record(paper: PaperSummary, record: ReadingRecord) -> None:
        if record.paper_id != paper.id:
            raise ValueError("阅读记录不属于当前论文。")
        ObsidianVaultStore._validate_paper(paper)
        if not record.confirmed or not record.personal_note.strip():
            raise ValueError("请先人工确认并写下个人理解。")
        if not record.question.strip():
            raise ValueError("阅读记录缺少原始问题，不能生成正式笔记。")
        if not SAFE_RECORD_ID.fullmatch(record.id):
            raise ValueError("阅读记录 ID 无效，不能生成安全文件名。")
        if not record.citations or not paper.page_count:
            raise ValueError("正式阅读笔记至少需要一条可核对的 PDF 原文引用。")
        if any(
            citation.source_page > paper.page_count or not citation.quote.strip()
            for citation in record.citations
        ):
            raise ValueError("原文引用缺少短引或页码超出 PDF 范围。")
        current_source = SourceDocumentRef(
            paper_uid=paper.paper_uid,
            pdf_sha256=paper.pdf_sha256,
        )
        if any(
            citation.source is not None
            and citation.source != current_source.at_page(citation.source_page)
            for citation in record.citations
        ):
            raise ValueError("原文引用属于另一版 PDF；请回到原文重新核对后再入库。")

    @staticmethod
    def _preview_digest(root: Path, markdown: str, source_fingerprint: bytes = b"") -> str:
        digest = sha256()
        digest.update(str(root).encode("utf-8"))
        digest.update(b"\0")
        digest.update(markdown.encode("utf-8"))
        digest.update(b"\0")
        digest.update(source_fingerprint)
        return digest.hexdigest()

    @staticmethod
    def _linked_note_fingerprint(root: Path, notes: list[VaultNote]) -> bytes:
        digest = sha256()
        for note in notes:
            source = root / note.path
            if source.is_symlink() or not source.resolve(strict=True).is_relative_to(root):
                raise ValueError("阅读笔记位置在预览期间发生变化，请重新预览。")
            digest.update(note.path.encode("utf-8"))
            digest.update(b"\0")
            digest.update(source.read_bytes())
            digest.update(b"\0")
        return digest.digest()

    @staticmethod
    def _render_reading_note(paper: PaperSummary, record: ReadingRecord) -> str:
        title = " ".join(record.question.split())
        quotes = "\n\n".join(
            f"- PDF 第 {citation.source_page} 页 · "
            f"`{paper.paper_uid}` · `{paper.pdf_sha256}`\n\n"
            + "\n".join(
                f"> {line}" for line in citation.quote.strip().splitlines()
            )
            for citation in record.citations
        )
        return (
            "---\n"
            "schema_version: 1\n"
            "kind: reading_note\n"
            f"uid: record-{record.id}\n"
            f"paper_uid: {paper.paper_uid}\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            "review_status: confirmed\n"
            f"created_at: {json.dumps(record.created_at)}\n"
            f"reading_record_uid: {record.id}\n"
            f"reading_session_uid: {json.dumps(record.session_id)}\n"
            "---\n\n"
            f"# {title}\n\n"
            "## 我的理解\n\n"
            f"{record.personal_note.strip()}\n\n"
            "## 原文依据\n\n"
            f"{quotes}\n\n"
            "## 仍待核对\n\n"
            "- [ ] 阅读时继续核对这条理解的适用范围。\n"
        )

    @staticmethod
    def _render_paper_card(paper: PaperSummary, notes: list[VaultNote]) -> str:
        title = Path(paper.name).stem
        links = "\n".join(
            f"- [{_escape_link_label(' '.join(note.title.split()))}]"
            f"(../{quote(note.path, safe='/')})"
            for note in notes
        )
        return (
            "---\n"
            "schema_version: 1\n"
            "kind: paper\n"
            f"uid: {paper.paper_uid}\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"pdf_sha256: {paper.pdf_sha256}\n"
            "review_status: confirmed\n"
            "---\n\n"
            f"# {title}\n\n"
            "> 本卡只索引我已确认并保存的阅读笔记；请以 PDF 原文核对具体论断。\n\n"
            "## 已确认的阅读笔记\n\n"
            f"{links}\n\n"
            "## 继续阅读\n\n"
            "- [ ] 继续核对论文中的方法、实验和局限。\n"
        )

    @staticmethod
    def _render_paper_source(paper: PaperSummary) -> str:
        assert paper.paper_uid is not None and paper.pdf_sha256 is not None
        title = Path(paper.name).stem
        return (
            "---\n"
            "schema_version: 1\n"
            "kind: paper_source\n"
            f"uid: source-{paper.paper_uid}\n"
            f"paper_uid: {paper.paper_uid}\n"
            f"title: {json.dumps(title, ensure_ascii=False)}\n"
            f"pdf_filename: {json.dumps(paper.name, ensure_ascii=False)}\n"
            f"pdf_sha256: {paper.pdf_sha256}\n"
            f"page_count: {paper.page_count}\n"
            f"source_language: {paper.detected_source_language}\n"
            "reading_status: 待读\n"
            "---\n\n"
            f"# {title}\n\n"
            "> 这是已导入 PDF 的来源目录，不是已确认的论文总结；标题暂按文件名显示。\n\n"
            "请在 ResearchCopilot 中阅读 PDF、核对原文，再把自己的理解保存为正式笔记。\n"
        )

    def _legacy_count(self) -> int:
        return sum(1 for _ in self.legacy_card_directory.glob("*.md"))

    def _scan(self, root: Path) -> VaultStatus:
        notes: list[VaultNote] = []
        issues: list[VaultIssue] = []
        seen_uids: dict[str, str] = {}
        for folder in ("Papers", "Notes", "Sources"):
            base = root / folder
            if not base.exists():
                continue
            if base.is_symlink() or not base.is_dir():
                issues.append(VaultIssue(path=folder, message="目录不是普通文件夹，已跳过"))
                continue
            for current, directory_names, file_names in os.walk(base, followlinks=False):
                directory_names[:] = sorted(
                    name for name in directory_names
                    if not name.startswith(".") and not (Path(current) / name).is_symlink()
                )
                for name in sorted(file_names):
                    if not name.lower().endswith(".md"):
                        continue
                    path = Path(current) / name
                    relative = path.relative_to(root).as_posix()
                    if len(notes) + len(issues) >= MAX_NOTES:
                        issues.append(VaultIssue(path="", message="超过 2000 个文件，已停止扫描"))
                        return VaultStatus(connected=True, path=str(root), notes=notes,
                                           issues=issues, legacy_card_count=self._legacy_count())
                    if path.is_symlink():
                        issues.append(VaultIssue(path=relative, message="符号链接已跳过"))
                        continue
                    try:
                        note = _read_note(path, relative)
                    except (OSError, UnicodeError, ValueError, TypeError) as error:
                        issues.append(VaultIssue(path=relative, message=str(error)))
                        continue
                    previous = seen_uids.get(note.uid)
                    if previous:
                        issues.append(VaultIssue(path=relative, message=f"uid 与 {previous} 重复"))
                        continue
                    seen_uids[note.uid] = relative
                    notes.append(note)
        return VaultStatus(
            connected=True, path=str(root), notes=notes, issues=issues,
            legacy_card_count=self._legacy_count(),
        )
