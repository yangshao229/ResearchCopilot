import json
import re
from pathlib import Path


PROJECT_ROOT = Path(__file__).parents[1]
LOCALES = PROJECT_ROOT / "web" / "src" / "locales"
COMPONENT_FILES = (
    PROJECT_ROOT / "web" / "src" / "App.tsx",
    PROJECT_ROOT / "web" / "src" / "main.tsx",
    PROJECT_ROOT / "web" / "src" / "components" / "AssistantPanel.tsx",
    PROJECT_ROOT / "web" / "src" / "components" / "GlossaryManager.tsx",
    PROJECT_ROOT / "web" / "src" / "components" / "PdfReader.tsx",
    PROJECT_ROOT
    / "web"
    / "src"
    / "components"
    / "assistant"
    / "AssistantViews.tsx",
)
PLACEHOLDER_PATTERN = re.compile(r"\{([a-zA-Z0-9_]+)\}")
CJK_PATTERN = re.compile(r"[\u3400-\u9fff]")


def load_catalog(name: str) -> dict[str, str]:
    return json.loads((LOCALES / name).read_text(encoding="utf-8"))


def test_ui_catalogs_have_matching_nonempty_keys_and_placeholders() -> None:
    chinese = load_catalog("zh-CN.json")
    english = load_catalog("en.json")

    assert chinese.keys() == english.keys()
    assert len(chinese) >= 150

    for key in chinese:
        assert chinese[key].strip(), f"Chinese message is empty: {key}"
        assert english[key].strip(), f"English message is empty: {key}"
        assert set(PLACEHOLDER_PATTERN.findall(chinese[key])) == set(
            PLACEHOLDER_PATTERN.findall(english[key])
        ), f"Placeholder mismatch: {key}"


def test_visible_react_ui_does_not_bypass_the_message_catalog() -> None:
    # These lines build model-task content. They intentionally remain independent
    # from the interface language and are not visible interface chrome.
    allowed_model_content_markers = (
        "`${instruction}\\n\\nPDF 第",
        'const query = task === "translate"',
        "onClick={() => useSelection(",
    )
    violations: list[str] = []

    for path in COMPONENT_FILES:
        for line_number, line in enumerate(
            path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            if CJK_PATTERN.search(line) and not any(
                marker in line for marker in allowed_model_content_markers
            ):
                violations.append(f"{path.relative_to(PROJECT_ROOT)}:{line_number}: {line}")

    assert not violations, "User-visible Chinese bypasses the UI catalog:\n" + "\n".join(
        violations
    )


def test_interface_language_stays_browser_local() -> None:
    core = (PROJECT_ROOT / "web" / "src" / "i18n.ts").read_text(encoding="utf-8")
    provider = (PROJECT_ROOT / "web" / "src" / "i18n-context.tsx").read_text(
        encoding="utf-8"
    )

    assert '"research-copilot:ui-language"' in core
    assert 'savedLanguage === "zh-CN" || savedLanguage === "en"' in core
    assert 'startsWith("zh") ? "zh-CN" : "en"' in core
    assert "window.localStorage.setItem(UI_LANGUAGE_KEY" in provider
    assert "fetch(" not in provider
