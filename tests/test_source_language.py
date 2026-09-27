from research_copilot.source_language import detect_source_language


def test_detects_english_and_chinese_from_local_text() -> None:
    english = "The attention mechanism processes tokens in parallel. " * 25
    chinese = "本研究提出一种用于论文阅读的模型，并分析实验结果。" * 25

    assert detect_source_language([english]) == "en"
    assert detect_source_language([chinese]) == "zh-CN"


def test_mixed_and_unreadable_papers_are_not_forced_into_one_language() -> None:
    english = "This paper studies a model and its results. " * 30
    chinese = "本文讨论模型的设计和实验结果。" * 30

    assert detect_source_language([english + chinese]) == "mixed"
    assert detect_source_language(["", "∑ ∫ 123 + =", ""]) == "unknown"


def test_only_initial_pages_are_sampled() -> None:
    english = "A method uses attention to understand the sequence. " * 30
    chinese = "本研究讨论中文数据和模型设计。" * 30

    assert detect_source_language([english] * 5 + [chinese] * 5) == "en"
