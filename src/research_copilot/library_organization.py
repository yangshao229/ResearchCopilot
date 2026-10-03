from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
from threading import RLock
from uuid import uuid4

from pydantic import BaseModel, ConfigDict, Field

from research_copilot.storage import atomic_write_json, read_json


MAX_COLLECTIONS = 100
MAX_TAGS_PER_PAPER = 20


class LibraryCollection(BaseModel):
    model_config = ConfigDict(extra="forbid")

    id: str
    name: str = Field(min_length=1, max_length=80)
    created_at: str


class PaperOrganization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collection_ids: list[str] = Field(default_factory=list, max_length=MAX_COLLECTIONS)
    tags: list[str] = Field(default_factory=list, max_length=MAX_TAGS_PER_PAPER)


class LibraryOrganization(BaseModel):
    model_config = ConfigDict(extra="forbid")

    collections: list[LibraryCollection] = Field(default_factory=list)
    papers: dict[str, PaperOrganization] = Field(default_factory=dict)


class LibraryOrganizationStore:
    def __init__(self, root_directory: Path) -> None:
        self.root_directory = root_directory.resolve()
        self.path = self.root_directory / "organization.json"
        self._lock = RLock()

    def list_collections(self) -> list[LibraryCollection]:
        with self._lock:
            return list(self._load().collections)

    def get_paper(self, paper_id: str) -> PaperOrganization:
        with self._lock:
            return self._load().papers.get(paper_id, PaperOrganization())

    def create_collection(self, name: str) -> LibraryCollection:
        with self._lock:
            cleaned_name = " ".join(name.strip().split())
            if not cleaned_name:
                raise ValueError("集合名称不能为空。")
            if len(cleaned_name) > 80:
                raise ValueError("集合名称不能超过 80 个字符。")

            data = self._load()
            if len(data.collections) >= MAX_COLLECTIONS:
                raise ValueError("集合数量已达到上限。")
            if any(
                collection.name.casefold() == cleaned_name.casefold()
                for collection in data.collections
            ):
                raise ValueError("已经存在同名集合。")

            collection = LibraryCollection(
                id=uuid4().hex,
                name=cleaned_name,
                created_at=datetime.now(UTC).isoformat(),
            )
            data.collections.append(collection)
            self._write(data)
            return collection

    def delete_collection(self, collection_id: str) -> None:
        with self._lock:
            data = self._load()
            if not any(item.id == collection_id for item in data.collections):
                raise KeyError(collection_id)

            data.collections = [
                item for item in data.collections if item.id != collection_id
            ]
            for paper_id, organization in list(data.papers.items()):
                collection_ids = [
                    item for item in organization.collection_ids
                    if item != collection_id
                ]
                data.papers[paper_id] = organization.model_copy(
                    update={"collection_ids": collection_ids}
                )
            self._write(data)

    def save_paper(
        self,
        paper_id: str,
        collection_ids: list[str],
        tags: list[str],
    ) -> PaperOrganization:
        with self._lock:
            data = self._load()
            known_collection_ids = {item.id for item in data.collections}
            normalized_collection_ids = list(dict.fromkeys(collection_ids))
            unknown = set(normalized_collection_ids) - known_collection_ids
            if unknown:
                raise ValueError("论文组织信息包含不存在的集合。")

            normalized_tags: list[str] = []
            seen_tags: set[str] = set()
            for tag in tags:
                cleaned_tag = " ".join(tag.strip().split())
                if not cleaned_tag:
                    continue
                if len(cleaned_tag) > 40:
                    raise ValueError("每个标签不能超过 40 个字符。")
                folded = cleaned_tag.casefold()
                if folded not in seen_tags:
                    normalized_tags.append(cleaned_tag)
                    seen_tags.add(folded)
            if len(normalized_tags) > MAX_TAGS_PER_PAPER:
                raise ValueError("每篇论文最多保存 20 个标签。")

            organization = PaperOrganization(
                collection_ids=normalized_collection_ids,
                tags=normalized_tags,
            )
            data.papers[paper_id] = organization
            self._write(data)
            return organization

    def _load(self) -> LibraryOrganization:
        return LibraryOrganization.model_validate(
            read_json(self.path, {"collections": [], "papers": {}})
        )

    def _write(self, data: LibraryOrganization) -> None:
        atomic_write_json(self.path, data.model_dump(mode="json"))
