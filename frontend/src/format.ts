import type { Translate } from "./i18n";

/** Minuten lesbar: 45 → "45 Min.", 90 → "1 Std. 30 Min." */
export function formatMinutes(t: Translate, minutes: number | null | undefined): string {
  if (!minutes || minutes <= 0) return "";
  const h = Math.floor(minutes / 60);
  const m = Math.round(minutes % 60);
  if (!h) return t("common.minutes", { n: m });
  if (!m) return t("common.hours", { h });
  return t("common.hours_minutes", { h, m });
}

/** Restzeit eines Timers: 65000 ms → "1:05", 3725000 → "1:02:05". */
export function formatClock(ms: number): string {
  const total = Math.max(0, Math.ceil(ms / 1000));
  const h = Math.floor(total / 3600);
  const m = Math.floor((total % 3600) / 60);
  const s = total % 60;
  const mm = h ? String(m).padStart(2, "0") : String(m);
  return `${h ? `${h}:` : ""}${mm}:${String(s).padStart(2, "0")}`;
}

/** Zahl mit Komma (de) bzw. Punkt (en). */
export function formatNumber(language: string, value: number, digits = 1): string {
  return new Intl.NumberFormat(language.startsWith("de") ? "de-DE" : "en-US", {
    maximumFractionDigits: digits,
  }).format(value);
}

export function formatDate(language: string, iso: string | null | undefined): string {
  if (!iso) return "";
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return "";
  return new Intl.DateTimeFormat(language.startsWith("de") ? "de-DE" : "en-US", { dateStyle: "medium" }).format(date);
}

/** Schritte im Entwurfs-Editor: durch Leerzeile getrennt. */
export function splitSteps(text: string): string[] {
  return text
    .split(/\n\s*\n/)
    .map((s) => s.replace(/\s*\n\s*/g, " ").trim())
    .filter(Boolean);
}

export function splitLines(text: string): string[] {
  return text
    .split("\n")
    .map((l) => l.trim())
    .filter(Boolean);
}

export function splitTags(text: string): string[] {
  return [...new Set(text.split(",").map((s) => s.trim()).filter(Boolean))];
}
