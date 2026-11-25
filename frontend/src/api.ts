// Zugriff auf die Rezeptbuch-WebSocket-Befehle und den Foto-Upload.
import type {
  ApiError,
  CategoryTree,
  Draft,
  HomeAssistant,
  PanelInfo,
  Recipe,
  RecipeSummary,
  VersionDiff,
} from "./types";

export interface ListQuery {
  query?: string;
  category_id?: number | null;
  uncategorized?: boolean;
  tags?: string[];
  sort?: string;
  limit?: number;
  offset?: number;
}

export type ImportResult =
  | { status: "draft"; draft: Draft }
  | { status: "duplicate"; recipe_id: number; title: string; source_url: string };

export function toApiError(err: unknown): ApiError {
  if (err && typeof err === "object") {
    const e = err as { code?: unknown; message?: unknown };
    return { code: String(e.code ?? "unknown_error"), message: String(e.message ?? "") };
  }
  return { code: "unknown_error", message: String(err) };
}

export class Api {
  /** Getter statt fester Referenz: HA liefert bei jeder Zustandsänderung ein neues hass-Objekt. */
  constructor(private readonly getHass: () => HomeAssistant) {}

  private get hass(): HomeAssistant {
    return this.getHass();
  }

  private ws<T>(type: string, data: Record<string, unknown> = {}): Promise<T> {
    return this.hass.callWS<T>({ type: `rezeptbuch/${type}`, ...data });
  }

  info() {
    return this.ws<PanelInfo>("info");
  }
  list(q: ListQuery) {
    const data: Record<string, unknown> = { ...q };
    for (const k of Object.keys(data)) if (data[k] === undefined || data[k] === "") delete data[k];
    return this.ws<{ total: number; items: RecipeSummary[] }>("recipes/list", data);
  }
  recipe(recipeId: number, versionId?: number | null, servings?: number | null) {
    return this.ws<Recipe>("recipe/get", {
      recipe_id: recipeId,
      ...(versionId ? { version_id: versionId } : {}),
      ...(servings ? { servings } : {}),
    });
  }
  diff(oldVersionId: number, newVersionId: number) {
    return this.ws<VersionDiff>("recipe/diff", { old_version_id: oldVersionId, new_version_id: newVersionId });
  }
  setDefaultVersion(recipeId: number, versionId: number) {
    return this.ws("recipe/set_default_version", { recipe_id: recipeId, version_id: versionId });
  }
  rate(recipeId: number, stars: number | null, comment: string, cooked: boolean, versionId?: number) {
    return this.ws("recipe/rate", {
      recipe_id: recipeId,
      stars,
      comment: comment || null,
      cooked,
      ...(versionId ? { version_id: versionId } : {}),
    });
  }
  annotate(recipeId: number, text: string) {
    return this.ws("recipe/annotate", { recipe_id: recipeId, text });
  }
  deleteRecipe(recipeId: number) {
    return this.ws("recipe/delete", { recipe_id: recipeId });
  }
  categories() {
    return this.ws<CategoryTree>("categories");
  }
  tags() {
    return this.ws<{ tags: { name: string; count: number }[] }>("tags");
  }
  drafts() {
    return this.ws<{ drafts: Draft[] }>("drafts");
  }
  draft(draftId: number) {
    return this.ws<Draft>("draft/get", { draft_id: draftId });
  }
  updateDraft(draftId: number, changes: Record<string, unknown>) {
    return this.ws<Draft>("draft/update", { draft_id: draftId, ...changes });
  }
  confirmDraft(draftId: number, allowDuplicate = false) {
    return this.ws<{ recipe_id: number }>("draft/confirm", { draft_id: draftId, allow_duplicate: allowDuplicate });
  }
  discardDraft(draftId: number) {
    return this.ws("draft/discard", { draft_id: draftId });
  }
  importUrl(url: string, allowDuplicate = false) {
    return this.ws<ImportResult>("import/url", { url, allow_duplicate: allowDuplicate });
  }
  addToShoppingList(recipeId: number, servings?: number | null) {
    return this.ws<{ items: string[] }>("shopping/add", { recipe_id: recipeId, ...(servings ? { servings } : {}) });
  }

  /** Fotos (bereits verkleinert) hochladen → Entwurf. Reihenfolge = Seitenreihenfolge. */
  async uploadPhotos(photos: Blob[]): Promise<ImportResult> {
    const form = new FormData();
    photos.forEach((blob, i) => form.append("photo", blob, `seite-${i + 1}.jpg`));
    const path = "/api/rezeptbuch/import/photo";
    let response: Response;
    if (this.hass.fetchWithAuth) {
      response = await this.hass.fetchWithAuth(path, { method: "POST", body: form });
    } else {
      const token = this.hass.auth?.accessToken ?? this.hass.auth?.data?.access_token ?? "";
      response = await fetch(path, { method: "POST", body: form, headers: { Authorization: `Bearer ${token}` } });
    }
    const body = (await response.json().catch(() => ({}))) as Record<string, unknown>;
    if (!response.ok) {
      throw { code: body.code ?? `http_${response.status}`, message: body.message ?? response.statusText };
    }
    return body as unknown as ImportResult;
  }
}
