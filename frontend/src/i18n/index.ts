// Übersetzung nach hass.language (de/en, Fallback Deutsch für de-*, sonst Englisch).
import type { ApiError } from "../types";
import { de, type TranslationKey } from "./de";
import { en } from "./en";

export type { TranslationKey };
export const LANGUAGES = { de, en } as const;
export type Language = keyof typeof LANGUAGES;

export function pickLanguage(language: string | undefined): Language {
  return (language ?? "").toLowerCase().startsWith("de") ? "de" : "en";
}

export type Translate = (key: TranslationKey, params?: Record<string, string | number>) => string;

export function translator(language: string | undefined): Translate {
  const dict: Record<TranslationKey, string> = LANGUAGES[pickLanguage(language)];
  return (key, params) => {
    let text: string = dict[key] ?? de[key] ?? key;
    if (params) {
      for (const [name, value] of Object.entries(params)) text = text.split(`{${name}}`).join(String(value));
    }
    return text;
  };
}

/** Fehler der API in einen lesbaren, übersetzten Text verwandeln. */
export function errorText(t: Translate, err: ApiError): string {
  const key = `error.${err.code}` as TranslationKey;
  if (key in de) return t(key);
  return t("common.error", { message: err.message || err.code });
}
