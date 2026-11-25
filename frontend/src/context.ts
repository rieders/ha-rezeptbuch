import type { Api } from "./api";
import type { Translate } from "./i18n";
import type { Route } from "./router";
import type { ApiError, Category, HomeAssistant, PanelInfo } from "./types";

/** Gemeinsamer Kontext, den das Panel an alle Ansichten weitergibt. */
export interface PanelContext {
  hass: HomeAssistant;
  api: Api;
  t: Translate;
  language: string;
  prefix: string;
  info: PanelInfo | null;
  go(route: Route): void;
  toast(message: string): void;
  fail(err: unknown): ApiError;
}

/** Kategoriebaum flach mit Einrückung (für Auswahllisten). */
export function flattenCategories(nodes: Category[], depth = 0): { category: Category; depth: number }[] {
  return nodes.flatMap((c) => [{ category: c, depth }, ...flattenCategories(c.children, depth + 1)]);
}
