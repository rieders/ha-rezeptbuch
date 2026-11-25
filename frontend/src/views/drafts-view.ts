import { mdiAlertOutline, mdiFileDocumentEditOutline } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "../components/rb-icon";
import type { PanelContext } from "../context";
import { formatDate } from "../format";
import { errorText } from "../i18n";
import { shared } from "../styles";
import type { Draft } from "../types";

export class RbDraftsView extends LitElement {
  static override properties = {
    ctx: { attribute: false },
    _drafts: { state: true },
    _error: { state: true },
    _loaded: { state: true },
  };
  declare ctx: PanelContext;
  declare _drafts: Draft[];
  declare _error: string;
  declare _loaded: boolean;

  constructor() {
    super();
    this._drafts = [];
    this._error = "";
    this._loaded = false;
  }

  override connectedCallback(): void {
    super.connectedCallback();
    void this.load();
  }

  private async load() {
    try {
      this._drafts = (await this.ctx.api.drafts()).drafts;
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    } finally {
      this._loaded = true;
    }
  }

  static override styles = [
    shared,
    css`
      .list {
        display: grid;
        gap: 10px;
      }
      .item {
        display: flex;
        gap: 12px;
        align-items: center;
      }
      .item img,
      .ph {
        width: 72px;
        height: 72px;
        object-fit: cover;
        border-radius: 8px;
        flex: none;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
        display: flex;
        align-items: center;
        justify-content: center;
      }
      .warn {
        color: var(--warning-color, #ffa600);
        --rb-icon-size: 18px;
      }
    `,
  ];

  override render() {
    const { t, language } = this.ctx;
    if (this._error) return html`<p class="error">${this._error}</p>`;
    if (!this._loaded) return html`<p class="muted">${t("common.loading")}</p>`;
    if (!this._drafts.length) return html`<p class="muted">${t("drafts.empty")}</p>`;
    const source = { url: t("drafts.from_url"), photo: t("drafts.from_photo"), manual: t("drafts.manual") };
    return html`<div class="list">
      ${this._drafts.map((d) => {
        const thumb = d.images.find((i) => i.path === d.image) ?? d.images[0];
        return html`<div class="card item">
          ${thumb?.url
            ? html`<img src=${thumb.url} alt="" loading="lazy" />`
            : html`<span class="ph"><rb-icon .path=${mdiFileDocumentEditOutline}></rb-icon></span>`}
          <div class="grow">
            <div><strong>${d.title || "–"}</strong></div>
            <div class="muted row">
              <span>${source[d.source_type]} · ${formatDate(language, d.created)}</span>
              ${d.warnings.length
                ? html`<span class="row warn"><rb-icon .path=${mdiAlertOutline}></rb-icon>${d.warnings.length}</span>`
                : nothing}
            </div>
          </div>
          <button class="primary" @click=${() => this.ctx.go({ view: "draft", draftId: d.id })}>
            ${t("drafts.open")}
          </button>
        </div>`;
      })}
    </div>`;
  }
}

if (!customElements.get("rb-drafts-view")) customElements.define("rb-drafts-view", RbDraftsView);
