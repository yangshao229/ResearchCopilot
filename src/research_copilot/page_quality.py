"""Conservative checks before sending extracted PDF text to a model."""

from __future__ import annotations

import re
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

PageQualityStatus = Literal["ready", "review", "blocked"]
PageQualityIssue = Literal[
    "no_text", "short_text", "damaged_text", "long_text", "math_review",
    "column_order_review", "column_order_mismatch",
]

_MATH_GLYPHS = re.compile(r"[∑∏∫√≤≥≠≈∈∉⊂⊆⊕⊗∂∇∞]")
_GREEK_ASSIGNMENT = re.compile(r"[α-ωΑ-Ωϵε]\d{0,2}\s*=")


class PageQuality(BaseModel):
    model_config = ConfigDict(extra="forbid")

    source_page: int = Field(ge=1)
    extractable_chars: int = Field(ge=0)
    status: PageQualityStatus
    issues: list[PageQualityIssue]


def inspect_page_text(source_page: int, text: str, max_chars: int) -> PageQuality:
    """Only detect obvious failures; `ready` does not certify layout order."""
    stripped = text.strip()
    size = len(stripped)
    issues: list[PageQualityIssue] = []
    if not stripped:
        issues.append("no_text")
    else:
        replacement_count = stripped.count("\ufffd")
        if replacement_count >= 3 and replacement_count / size >= 0.02:
            issues.append("damaged_text")
        if size > max_chars:
            issues.append("long_text")
        if size < 80:
            issues.append("short_text")
        if _MATH_GLYPHS.search(stripped) or _GREEK_ASSIGNMENT.search(stripped):
            issues.append("math_review")
    status: PageQualityStatus = (
        "blocked" if any(issue in issues for issue in ("no_text", "damaged_text", "long_text"))
        else "review" if issues else "ready"
    )
    return PageQuality(
        source_page=source_page,
        extractable_chars=size,
        status=status,
        issues=issues,
    )
