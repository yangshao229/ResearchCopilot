import json
from pathlib import Path

from research_copilot.storage import atomic_write_json


def save_page_data(page_data: dict[str, object], output_path: Path) -> None:
    atomic_write_json(output_path, page_data)


def load_page_data(input_path: Path) -> dict[str, object]:
    with input_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)
