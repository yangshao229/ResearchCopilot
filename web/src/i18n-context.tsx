import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from "react";

import {
  UI_LANGUAGE_KEY,
  resolveUiLanguage,
  translate,
  type MessageKey,
  type MessageParams,
  type UiLanguage,
} from "./i18n";

type I18nContextValue = {
  language: UiLanguage;
  locale: "zh-CN" | "en-US";
  setLanguage: (language: UiLanguage) => void;
  t: (key: MessageKey, params?: MessageParams) => string;
  errorMessage: (reason: unknown, fallbackKey: MessageKey) => string;
};

const I18nContext = createContext<I18nContextValue | null>(null);

export function I18nProvider({ children }: { children: ReactNode }) {
  const [language, setLanguageState] = useState<UiLanguage>(() => {
    let savedLanguage: string | null = null;
    try {
      savedLanguage = window.localStorage.getItem(UI_LANGUAGE_KEY);
    } catch {
      // Private browsing may block storage; browser language remains usable.
    }
    return resolveUiLanguage(savedLanguage, window.navigator.language);
  });

  useEffect(() => {
    document.documentElement.lang = language;
  }, [language]);

  const setLanguage = useCallback((nextLanguage: UiLanguage) => {
    try {
      window.localStorage.setItem(UI_LANGUAGE_KEY, nextLanguage);
    } catch {
      // Keep the current page functional even when persistence is unavailable.
    }
    setLanguageState(nextLanguage);
  }, []);

  const t = useCallback(
    (key: MessageKey, params?: MessageParams) =>
      translate(language, key, params),
    [language],
  );

  const errorMessage = useCallback(
    (reason: unknown, fallbackKey: MessageKey) => {
      if (!(reason instanceof Error) || !reason.message.trim()) {
        return t(fallbackKey);
      }
      if (language === "zh-CN" || !/[\u3400-\u9fff]/u.test(reason.message)) {
        return reason.message;
      }
      return t(fallbackKey);
    },
    [language, t],
  );

  const value = useMemo<I18nContextValue>(
    () => ({
      language,
      locale: language === "zh-CN" ? "zh-CN" : "en-US",
      setLanguage,
      t,
      errorMessage,
    }),
    [errorMessage, language, setLanguage, t],
  );

  return <I18nContext.Provider value={value}>{children}</I18nContext.Provider>;
}

export function useI18n(): I18nContextValue {
  const context = useContext(I18nContext);
  if (!context) {
    throw new Error("useI18n must be used inside I18nProvider");
  }
  return context;
}

export type { UiLanguage } from "./i18n";
