import type { ReadingScope, SelectionContextPreview } from "./api";
import type { MessageKey, MessageParams, UiLanguage } from "./i18n";

type Translator = (key: MessageKey, params?: MessageParams) => string;

export function scopeStatus(scope: ReadingScope, language: UiLanguage, t: Translator): string {
  if (language === "zh-CN") return scope.note || t("evidence.fullPaper");
  if (scope.resolution === "fallback") return t("status.scopeFallback");
  if (scope.kind === "section" && scope.start_page !== null && scope.end_page !== null) {
    return t("status.scopeSection", {
      title: scope.section_title,
      start: scope.start_page,
      end: scope.end_page,
    });
  }
  return t("evidence.fullPaper");
}

export function selectionStatus(
  preview: SelectionContextPreview,
  language: UiLanguage,
  t: Translator,
): string {
  if (language === "zh-CN") return preview.note;
  if (preview.method === "paragraph") return t("status.selectionParagraph");
  if (preview.method === "page_window") return t("status.selectionWindow");
  return t("status.selectionOnly");
}
