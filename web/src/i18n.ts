import enMessages from "./locales/en.json";
import zhCNMessages from "./locales/zh-CN.json";

export type UiLanguage = "zh-CN" | "en";
export type MessageKey = keyof typeof zhCNMessages;
export type MessageParams = Record<string, string | number>;

export const UI_LANGUAGE_KEY = "research-copilot:ui-language";

const catalogs: Record<UiLanguage, Record<MessageKey, string>> = {
  "zh-CN": zhCNMessages,
  en: enMessages,
};

export function resolveUiLanguage(
  savedLanguage: string | null,
  browserLanguage: string,
): UiLanguage {
  if (savedLanguage === "zh-CN" || savedLanguage === "en") {
    return savedLanguage;
  }
  return browserLanguage.toLowerCase().startsWith("zh") ? "zh-CN" : "en";
}

export function translate(
  language: UiLanguage,
  key: MessageKey,
  params: MessageParams = {},
): string {
  const message = catalogs[language][key] ?? catalogs["zh-CN"][key] ?? key;
  return message.replace(/\{([a-zA-Z0-9_]+)\}/g, (match, name: string) =>
    Object.prototype.hasOwnProperty.call(params, name)
      ? String(params[name])
      : match,
  );
}
