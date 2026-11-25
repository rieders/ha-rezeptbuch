import { mdiArrowDown, mdiArrowUp, mdiCamera, mdiClose, mdiImagePlus, mdiLink } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "../components/rb-icon";
import type { PanelContext } from "../context";
import { downscale } from "../image";
import { errorText } from "../i18n";
import { shared } from "../styles";

interface Photo {
  file: File;
  url: string;
}

export class RbImportView extends LitElement {
  static override properties = {
    ctx: { attribute: false },
    _tab: { state: true },
    _url: { state: true },
    _photos: { state: true },
    _busy: { state: true },
    _error: { state: true },
    _duplicate: { state: true },
  };
  declare ctx: PanelContext;
  declare _tab: "url" | "photo";
  declare _url: string;
  declare _photos: Photo[];
  declare _busy: boolean;
  declare _error: string;
  declare _duplicate: { recipe_id: number; title: string } | null;

  constructor() {
    super();
    this._tab = "url";
    this._url = "";
    this._photos = [];
    this._busy = false;
    this._error = "";
    this._duplicate = null;
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    this._photos.forEach((p) => URL.revokeObjectURL(p.url));
  }

  private async importUrl(allowDuplicate = false) {
    this._busy = true;
    this._error = "";
    this._duplicate = null;
    try {
      const result = await this.ctx.api.importUrl(this._url.trim(), allowDuplicate);
      if (result.status === "duplicate") this._duplicate = { recipe_id: result.recipe_id, title: result.title };
      else this.ctx.go({ view: "draft", draftId: result.draft.id });
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    } finally {
      this._busy = false;
    }
  }

  private addFiles(e: Event) {
    const input = e.target as HTMLInputElement;
    const files = Array.from(input.files ?? []).filter((f) => f.type.startsWith("image/") || !f.type);
    this._photos = [...this._photos, ...files.map((file) => ({ file, url: URL.createObjectURL(file) }))].slice(0, 10);
    input.value = "";
  }

  private move(index: number, delta: number) {
    const next = [...this._photos];
    const target = index + delta;
    if (target < 0 || target >= next.length) return;
    [next[index], next[target]] = [next[target], next[index]];
    this._photos = next;
  }

  private removePhoto(index: number) {
    URL.revokeObjectURL(this._photos[index].url);
    this._photos = this._photos.filter((_, i) => i !== index);
  }

  private async analyze() {
    this._busy = true;
    this._error = "";
    try {
      const blobs = await Promise.all(this._photos.map((p) => downscale(p.file)));
      const result = await this.ctx.api.uploadPhotos(blobs);
      if (result.status === "draft") this.ctx.go({ view: "draft", draftId: result.draft.id });
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    } finally {
      this._busy = false;
    }
  }

  static override styles = [
    shared,
    css`
      .tabs {
        display: flex;
        gap: 8px;
        margin-bottom: 16px;
      }
      .tabs button[aria-selected="true"] {
        background: var(--primary-color);
        color: var(--text-primary-color, #fff);
        border-color: var(--primary-color);
      }
      .pages {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
        gap: 10px;
        margin: 12px 0;
      }
      .page {
        position: relative;
      }
      .page img {
        width: 100%;
        aspect-ratio: 3 / 4;
        object-fit: cover;
        border-radius: 8px;
        display: block;
      }
      .page .tools {
        display: flex;
        justify-content: space-between;
      }
      input[type="file"] {
        display: none;
      }
      .card {
        max-width: 900px;
      }
    `,
  ];

  override render() {
    const { t } = this.ctx;
    return html`
      <h1>${t("import.title")}</h1>
      <div class="tabs" role="tablist">
        <button role="tab" aria-selected=${this._tab === "url"} @click=${() => (this._tab = "url")}>
          <rb-icon .path=${mdiLink}></rb-icon>${t("import.tab_url")}
        </button>
        <button role="tab" aria-selected=${this._tab === "photo"} @click=${() => (this._tab = "photo")}>
          <rb-icon .path=${mdiCamera}></rb-icon>${t("import.tab_photo")}
        </button>
      </div>
      <div class="card">${this._tab === "url" ? this.renderUrl() : this.renderPhoto()}</div>
      ${this._error ? html`<p class="error">${this._error}</p>` : nothing}
    `;
  }

  private renderUrl() {
    const { t } = this.ctx;
    return html`<label for="url">${t("import.url_label")}</label>
      <div class="row">
        <input
          id="url"
          class="grow"
          type="url"
          inputmode="url"
          autocomplete="off"
          placeholder="https://…"
          .value=${this._url}
          @input=${(e: Event) => (this._url = (e.target as HTMLInputElement).value)}
          @keydown=${(e: KeyboardEvent) => e.key === "Enter" && this._url.trim() && this.importUrl()}
        />
        <button class="primary" ?disabled=${this._busy || !this._url.trim()} @click=${() => this.importUrl()}>
          ${this._busy ? t("import.working") : t("import.url_button")}
        </button>
      </div>
      ${this._duplicate
        ? html`<p class="warning row">
            <span class="grow">${t("import.duplicate", { title: this._duplicate.title })}</span>
            <button @click=${() => this.ctx.go({ view: "recipe", recipeId: this._duplicate!.recipe_id })}>
              ${t("import.open_existing")}
            </button>
            <button @click=${() => this.importUrl(true)}>${t("draft.save_anyway")}</button>
          </p>`
        : nothing}`;
  }

  private renderPhoto() {
    const { t } = this.ctx;
    if (this.ctx.info && !this.ctx.info.ai_task_available) return html`<p class="warning">${t("import.no_ai")}</p>`;
    return html`<p class="muted">${t("import.photo_hint")}</p>
      <div class="row">
        <label class="btn" for="files"><rb-icon .path=${mdiImagePlus}></rb-icon>${t("import.choose")}</label>
        <input id="files" type="file" accept="image/*" multiple @change=${this.addFiles} />
        <label class="btn" for="camera"><rb-icon .path=${mdiCamera}></rb-icon>${t("import.camera")}</label>
        <input id="camera" type="file" accept="image/*" capture="environment" @change=${this.addFiles} />
      </div>
      <div class="pages">
        ${this._photos.map(
          (p, i) => html`<div class="page">
            <img src=${p.url} alt=${t("import.page", { n: i + 1 })} />
            <div class="tools">
              <button class="icon" aria-label=${t("import.move_up")} ?disabled=${i === 0} @click=${() => this.move(i, -1)}>
                <rb-icon .path=${mdiArrowUp}></rb-icon>
              </button>
              <span class="muted" style="align-self:center">${t("import.page", { n: i + 1 })}</span>
              <button
                class="icon"
                aria-label=${t("import.move_down")}
                ?disabled=${i === this._photos.length - 1}
                @click=${() => this.move(i, 1)}
              >
                <rb-icon .path=${mdiArrowDown}></rb-icon>
              </button>
              <button class="icon" aria-label=${t("import.remove")} @click=${() => this.removePhoto(i)}>
                <rb-icon .path=${mdiClose}></rb-icon>
              </button>
            </div>
          </div>`,
        )}
      </div>
      <button class="primary" ?disabled=${this._busy || !this._photos.length} @click=${this.analyze}>
        ${this._busy ? t("import.analyzing") : t("import.analyze")}
      </button>`;
  }
}

if (!customElements.get("rb-import-view")) customElements.define("rb-import-view", RbImportView);
