"""Evaluate a frozen fine-grained evidence gate on calibration and held-out cases."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from research_copilot.real_multi_paper_evaluation import (
    evaluate_fine_grained_evidence,
)


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TRUTH = (
    PROJECT_ROOT / "docs/evaluations/m8_4d_fine_grained_evidence_truth.json"
)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--truth", type=Path, default=DEFAULT_TRUTH)
    parser.add_argument(
        "--paper-directory", type=Path, default=PROJECT_ROOT / "data/raw"
    )
    args = parser.parse_args()
    truth = json.loads(args.truth.read_text(encoding="utf-8"))
    try:
        report = evaluate_fine_grained_evidence(truth, args.paper_directory)
    except (KeyError, OSError, ValueError) as error:
        parser.exit(2, f"细粒度证据评测无法运行：{error}\n")
    print(json.dumps(report, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
