from __future__ import annotations

import re
from typing import Literal, Sequence


DetectedSourceLanguage = Literal["en", "zh-CN", "mixed", "unknown"]


def detect_source_language(pages: Sequence[str]) -> DetectedSourceLanguage:
    """Estimate the PDF's source language locally; never treat this as certain."""
    sample = " ".join(pages[:5])[:20000]
    english_words = len(re.findall(r"[A-Za-z]{2,}", sample))
    chinese_units = sum("\u4e00" <= char <= "\u9fff" for char in sample) / 2
    total = english_words + chinese_units
    if total < 40:
        return "unknown"
    english_share = english_words / total
    chinese_share = chinese_units / total
    if english_words >= 40 and chinese_units >= 40 and min(english_share, chinese_share) >= 0.25:
        return "mixed"
    if english_share >= 0.75 and english_words >= 40:
        return "en"
    if chinese_share >= 0.75 and chinese_units >= 40:
        return "zh-CN"
    return "mixed"
