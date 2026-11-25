import { mdiBookOpenPageVariant, mdiFileDocumentEditOutline, mdiMenu, mdiPlus } from "@mdi/js";
import { LitElement, css, html } from "lit";
import { Api, toApiError } from "./api";
import "./components/rb-icon";
import "./components/rb-timer-bar";
import type { PanelContext } from "./context";
import { translator } from "./i18n";
import { type Route, navigate, parseRoute } from "./router";
import { shared } from "./styles";
import type { HomeAssistant, PanelInfo, PanelRoute } from "./types";
import "./views/draft-editor";
import "./views/drafts-view";
import "./views/import-view";
import "./views/recipe-list";
import "./views/recipe-view";

/** Einstieg des Panels (panel_custom, webcomponent "rezeptbuch-panel"). */
export class RezeptbuchPanel extends LitElement {
  static override properties = {
    hass: { attribute: false },
    narrow: { type: Boolean },
    route: { attribute: false },
    _info: { state: true },
    _toast: { state: true },
    _ctx: { state: true },
  };
  declare hass: HomeAssistant;
  declare narrow: boolean;
  declare route: PanelRoute | undefined;
  declare _info: PanelInfo | null;
  declare _toast: string;
  declare _ctx: PanelContext | null;
  private _api = new Api(() => this.hass);
  private _language = "";
  private _toastTimer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    super();
    this.narrow = false;
    this._info = null;
    this._toast = "";
    this._ctx = null;
  }

  override willUpdate(changed: Map<string, unknown>): void {
    const language = this.hass?.locale?.language ?? this.hass?.language ?? "de";
    // Kontext nur bei Sprach-/Rechteänderung neu bauen – nicht bei jedem neuen hass-Objekt
    if (this.hass && (!this._ctx || language !== this._language || changed.has("_info"))) {
      this._language = language;
      this._ctx = {
        hass: this.hass,
        api: this._api,
        t: translator(language),
        language,
        prefix: this.route?.prefix ?? "/rezeptbuch",
        info: this._info,
        go: (route: Route) => navigate(this.route?.prefix ?? "/rezeptbuch", route),
        toast: (message: string) => this.showToast(message),
        fail: (err: unknown) => toApiError(err),
      };
    }
  }

  override firstUpdated(): void {
    void this._api
      .info()
      .then((info) => (this._info = info))
      .catch(() => (this._info = null));
  }

  private showToast(message: string) {
    this._toast = message;
    clearTimeout(this._toastTimer);
    this._toastTimer = setTimeout(() => (this._toast = ""), 4000);
  }

  private toggleMenu() {
    this.dispatchEvent(new Event("hass-toggle-menu", { bubbles: true, composed: true }));
  }

  static override styles = [
    shared,
    css`
      :host {
        display: flex;
        flex-direction: column;
        height: 100%;
        min-height: 100vh;
        background: var(--primary-background-color);
      }
      header {
        position: sticky;
        top: 0;
        z-index: 3;
        display: flex;
        align-items: center;
        gap: 4px;
        min-height: var(--header-height, 56px);
        padding: 0 8px;
        padding-top: env(safe-area-inset-top, 0);
        background: var(--app-header-background-color, var(--primary-color));
        color: var(--app-header-text-color, var(--text-primary-color, #fff));
      }
      header .title {
        font-size: 1.25rem;
        margin: 0 8px;
        flex: 1;
        white-space: nowrap;
        overflow: hidden;
        text-overflow: ellipsis;
      }
      header button {
        color: inherit;
        background: transparent;
        border-color: transparent;
      }
      header button[aria-current="page"] {
        border-color: currentColor;
      }
      main {
        flex: 1;
        width: 100%;
        max-width: 1400px;
        margin: 0 auto;
        padding: 16px;
        padding-bottom: calc(16px + env(safe-area-inset-bottom, 0));
      }
      rb-timer-bar {
        position: sticky;
        bottom: 0;
        z-index: 3;
        padding-bottom: env(safe-area-inset-bottom, 0);
      }
      .toast {
        position: fixed;
        left: 50%;
        bottom: calc(24px + env(safe-area-inset-bottom, 0));
        transform: translateX(-50%);
        z-index: 5;
        max-width: calc(100% - 32px);
        padding: 12px 18px;
        border-radius: 8px;
        background: var(--primary-text-color);
        color: var(--primary-background-color);
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.3);
      }
      @media (max-width: 600px) {
        header .label {
          display: none;
        }
        main {
          padding: 10px;
        }
      }
    `,
  ];

  override render() {
    const ctx = this._ctx;
    if (!ctx) return html``;
    const { t } = ctx;
    const route = parseRoute(this.route?.path);
    const active = route.view === "recipe" ? "list" : route.view === "draft" ? "drafts" : route.view;
    const nav = (view: "list" | "drafts" | "import", icon: string, label: string) =>
      html`<button aria-current=${active === view ? "page" : "false"} @click=${() => ctx.go({ view } as Route)}>
        <rb-icon .path=${icon}></rb-icon><span class="label">${label}</span>
      </button>`;
    return html`
      <header>
        ${this.narrow
          ? html`<button class="icon" aria-label=${t("nav.menu")} @click=${this.toggleMenu}>
              <rb-icon .path=${mdiMenu}></rb-icon>
            </button>`
          : ""}
        <span class="title">${t("app.title")}</span>
        ${nav("list", mdiBookOpenPageVariant, t("nav.recipes"))}
        ${nav("drafts", mdiFileDocumentEditOutline, t("nav.drafts"))} ${nav("import", mdiPlus, t("nav.import"))}
      </header>
      <main>${this.renderView(route, ctx)}</main>
      <rb-timer-bar .t=${t}></rb-timer-bar>
      ${this._toast ? html`<div class="toast" role="status">${this._toast}</div>` : ""}
    `;
  }

  private renderView(route: Route, ctx: PanelContext) {
    switch (route.view) {
      case "recipe":
        return html`<rb-recipe-view .ctx=${ctx} .recipeId=${route.recipeId}></rb-recipe-view>`;
      case "drafts":
        return html`<rb-drafts-view .ctx=${ctx}></rb-drafts-view>`;
      case "draft":
        return html`<rb-draft-editor .ctx=${ctx} .draftId=${route.draftId}></rb-draft-editor>`;
      case "import":
        return html`<rb-import-view .ctx=${ctx}></rb-import-view>`;
      default:
        return html`<rb-recipe-list .ctx=${ctx}></rb-recipe-list>`;
    }
  }
}

if (!customElements.get("rezeptbuch-panel")) customElements.define("rezeptbuch-panel", RezeptbuchPanel);
