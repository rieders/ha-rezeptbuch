// Routen innerhalb des Panels: /rezeptbuch/…
export type Route =
  | { view: "list" }
  | { view: "recipe"; recipeId: number }
  | { view: "drafts" }
  | { view: "draft"; draftId: number }
  | { view: "import" };

export function parseRoute(path: string | undefined): Route {
  const parts = (path ?? "").split("/").filter(Boolean);
  const id = Number(parts[1]);
  switch (parts[0]) {
    case "rezept":
      return Number.isInteger(id) && id > 0 ? { view: "recipe", recipeId: id } : { view: "list" };
    case "entwuerfe":
      return { view: "drafts" };
    case "entwurf":
      return Number.isInteger(id) && id > 0 ? { view: "draft", draftId: id } : { view: "drafts" };
    case "import":
      return { view: "import" };
    default:
      return { view: "list" };
  }
}

export function routePath(route: Route): string {
  switch (route.view) {
    case "recipe":
      return `/rezept/${route.recipeId}`;
    case "drafts":
      return "/entwuerfe";
    case "draft":
      return `/entwurf/${route.draftId}`;
    case "import":
      return "/import";
    default:
      return "";
  }
}

/** Navigation wie im HA-Frontend: pushState + "location-changed" → HA aktualisiert route. */
export function navigate(prefix: string, route: Route, replace = false): void {
  const url = `${prefix}${routePath(route)}`;
  if (replace) history.replaceState(null, "", url);
  else history.pushState(null, "", url);
  window.dispatchEvent(new CustomEvent("location-changed", { detail: { replace } }));
}
