from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any
from uuid import uuid4


def validated_json_path(root_directory: Path, key: str) -> Path:
    if not re.fullmatch(r"[A-Za-z0-9_-]+", key):
        raise ValueError("Invalid storage key.")
    return root_directory / f"{key}.json"


def read_json(path: Path, default: Any) -> Any:
    if not path.exists():
        return default
    with path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)


def atomic_write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_name(f".{path.name}.{uuid4().hex}.tmp")
    temporary_path.write_text(
        json.dumps(data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary_path.replace(path)
