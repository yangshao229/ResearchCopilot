import json

from pathlib import Path


def save_page_data(page_data: dict[str, object], output_path: Path) -> None:
    with output_path.open("w", encoding="utf-8") as output_file:
        json.dump(page_data, output_file, ensure_ascii=False, indent=2)
def load_page_data(input_path: Path) -> dict[str, object]:
    with input_path.open("r", encoding="utf-8") as input_file:
        return json.load(input_file)