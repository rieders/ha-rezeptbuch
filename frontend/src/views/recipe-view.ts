import { mdiArrowLeft, mdiCartPlus, mdiDelete, mdiMinus, mdiOpenInNew, mdiPlus, mdiTimerOutline } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "../components/rb-icon";
import "../components/rb-stars";
import type { PanelContext } from "../context";
import { formatClock, formatDate, formatMinutes, formatNumber } from "../format";
import { errorText } from "../i18n";
import { shared } from "../styles";
import { timerStore } from "../timers";
import type { Annotation, Recipe, VersionDiff } from "../types";
import "./diff-view";

export class RbRecipeView extends LitElement {
  static override properties = {
    ctx: { attribute: false },
    recipeId: { type: Number },
    _recipe: { state: true },
    _versionId: { state: true },
    _servings: { state: true },
    _checked: { state: true },
    _diff: { state: true },
    _showDiff: { state: true },
    _error: { state: true },
    _stars: { state: true },
    _cooked: { state: true },
    _comment: { state: true },
    _note: { state: true },
    _confirmDelete: { state: true },
    _busy: { state: true },
  };
  declare ctx: PanelContext;
  declare recipeId: number;
  declare _recipe: Recipe | null;
  declare _versionId: number | null;
  declare _servings: number | null;
  declare _checked: Set<number>;
  declare _diff: VersionDiff | null;
  declare _showDiff: boolean;
  declare _error: string;
  declare _stars: number | null;
  declare _cooked: boolean;
  declare _comment: string;
  declare _note: string;
  declare _confirmDelete: boolean;
  declare _busy: boolean;

  constructor() {
    super();
    this._recipe = null;
    this._versionId = null;
    this._servings = null;
    this._checked = new Set();
    this._diff = null;
    this._showDiff = false;
    this._error = "";
    this._stars = null;
    this._cooked = true;
    this._comment = "";
    this._note = "";
    this._confirmDelete = false;
    this._busy = false;
  }

  override updated(changed: Map<string, unknown>): void {
    if (changed.has("recipeId")) {
      this._versionId = null;
      this._servings = null;
      this._checked = new Set();
      this._showDiff = false;
      void this.load();
    }
  }

  /** Lädt (und signiert Bild-URLs neu) – bei jeder Anzeige. */
  private async load() {
    this._error = "";
    try {
      this._recipe = await this.ctx.api.recipe(this.recipeId, this._versionId, this._servings);
      if (this._showDiff) await this.loadDiff();
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    }
  }

  private async loadDiff() {
    const r = this._recipe;
    const original = r?.versions.find((v) => v.is_original);
    if (!r || !original) return;
    this._diff = await this.ctx.api.diff(original.id, r.version.id);
  }

  private changeServings(delta: number) {
    const r = this._recipe;
    if (!r) return;
    const current = r.version.data.servings ?? r.version.original_servings ?? 1;
    const step = current < 2 ? 0.5 : 1;
    const next = Math.max(0.5, Math.min(500, current + delta * step));
    this.setServings(next);
  }

  private setServings(value: number) {
    if (!Number.isFinite(value) || value <= 0) return;
    this._servings = value;
    void this.load();
  }

  private toggle(index: number) {
    const next = new Set(this._checked);
    if (next.has(index)) next.delete(index);
    else next.add(index);
    this._checked = next;
  }

  private async run(action: () => Promise<unknown>, success?: string) {
    this._busy = true;
    try {
      await action();
      if (success) this.ctx.toast(success);
    } catch (err) {
      this.ctx.toast(errorText(this.ctx.t, this.ctx.fail(err)));
    } finally {
      this._busy = false;
    }
  }

  static override styles = [
    shared,
    css`
      .top {
        display: flex;
        align-items: center;
        gap: 8px;
        margin-bottom: 12px;
      }
      .top h1 {
        margin: 0;
        flex: 1;
      }
      .hero {
        width: 100%;
        max-height: 360px;
        object-fit: cover;
        border-radius: var(--ha-card-border-radius, 12px);
        margin-bottom: 12px;
      }
      .layout {
        display: grid;
        grid-template-columns: minmax(260px, 1fr) 2fr;
        gap: 16px;
        align-items: start;
      }
      @media (max-width: 860px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .stepper {
        display: inline-flex;
        align-items: center;
        gap: 4px;
      }
      .stepper input {
        width: 80px;
        text-align: center;
      }
      ul.ingredients {
        list-style: none;
        padding: 0;
        margin: 0;
      }
      ul.ingredients li {
        display: flex;
        gap: 10px;
        align-items: flex-start;
        min-height: 44px;
        padding: 8px 0;
        border-bottom: 1px solid var(--divider-color);
        cursor: pointer;
      }
      ul.ingredients li.done span.txt {
        text-decoration: line-through;
        opacity: 0.55;
      }
      ul.ingredients input {
        width: 22px;
        min-height: 22px;
        margin-top: 2px;
      }
      .qty {
        font-weight: 500;
        white-space: nowrap;
      }
      ul.ingredients li.group {
        cursor: default;
        border: none;
        min-height: 0;
        padding: 0;
      }
      .group {
        margin: 14px 0 4px;
        font-weight: 500;
        color: var(--secondary-text-color);
      }
      ol.steps {
        padding-left: 1.4em;
        margin: 0;
      }
      ol.steps li {
        padding: 6px 0 12px;
        line-height: 1.55;
        font-size: 1.05rem;
      }
      .note {
        font-size: 0.85rem;
        color: var(--secondary-text-color);
        border-left: 3px solid var(--primary-color);
        padding-left: 8px;
        margin-top: 4px;
      }
      .section {
        margin-top: 16px;
      }
      .history li {
        margin-bottom: 8px;
      }
      rb-stars.pick {
        --rb-star-size: 36px;
      }
      .version select {
        width: auto;
        min-width: 200px;
      }
    `,
  ];

  override render() {
    const { t } = this.ctx;
    if (this._error) {
      return html`<p class="error">${this._error}</p>
        <button @click=${() => this.load()}>${t("common.retry")}</button>`;
    }
    const r = this._recipe;
    if (!r) return html`<p class="muted">${t("common.loading")}</p>`;
    const data = r.version.data;
    return html`
      <div class="top">
        <button class="icon" aria-label=${t("common.back")} @click=${() => this.ctx.go({ view: "list" })}>
          <rb-icon .path=${mdiArrowLeft}></rb-icon>
        </button>
        <h1>${r.title}</h1>
        <button ?disabled=${this._busy} @click=${this.addToShopping}>
          <rb-icon .path=${mdiCartPlus}></rb-icon><span>${t("recipe.shopping")}</span>
        </button>
        ${this.ctx.info?.is_admin
          ? html`<button
              class="danger"
              ?disabled=${this._busy}
              @click=${this.deleteRecipe}
              aria-label=${t("recipe.delete")}
            >
              <rb-icon .path=${mdiDelete}></rb-icon>${this._confirmDelete ? t("common.confirm_delete") : nothing}
            </button>`
          : nothing}
      </div>
      ${r.image_url ? html`<img class="hero" src=${r.image_url} alt="" />` : nothing}
      ${r.description ? html`<p>${r.description}</p>` : nothing}
      <div class="row muted">
        ${data.prep_time ? html`<span>${t("recipe.prep")}: ${formatMinutes(t, data.prep_time)}</span>` : nothing}
        ${data.cook_time ? html`<span>${t("recipe.cook")}: ${formatMinutes(t, data.cook_time)}</span>` : nothing}
        ${data.total_time ? html`<span>${t("recipe.total")}: ${formatMinutes(t, data.total_time)}</span>` : nothing}
      </div>
      <div class="row section">
        ${r.categories.map((c) => html`<span class="chip">${c.path.join(" › ")}</span>`)}
        ${r.tags.map((tag) => html`<span class="chip">#${tag}</span>`)}
        ${r.source_url
          ? html`<a class="btn" href=${r.source_url} target="_blank" rel="noopener noreferrer"
              ><rb-icon .path=${mdiOpenInNew}></rb-icon>${t("recipe.source")}</a
            >`
          : nothing}
      </div>
      ${this.renderVersions(r)} ${this._showDiff && this._diff ? this.renderDiff() : nothing}
      <div class="layout section">
        <div class="card">
          <h2>${t("recipe.ingredients")}</h2>
          ${this.renderServings(r)} ${this.renderIngredients(r)}
        </div>
        <div class="card">
          <h2>${t("recipe.steps")}</h2>
          ${this.renderSteps(r)}
        </div>
      </div>
      <div class="layout section">
        <div class="card">${this.renderNotes(r)}</div>
        <div class="card">${this.renderRatings(r)}</div>
      </div>
    `;
  }

  private renderVersions(r: Recipe) {
    const { t } = this.ctx;
    if (r.versions.length < 2) return nothing;
    const current = r.versions.find((v) => v.id === r.version.id);
    return html`<div class="row section version">
      <label class="muted" for="version">${t("recipe.version")}</label>
      <select
        id="version"
        @change=${(e: Event) => {
          this._versionId = Number((e.target as HTMLSelectElement).value);
          void this.load();
        }}
      >
        ${r.versions.map(
          (v) =>
            html`<option value=${String(v.id)} ?selected=${v.id === r.version.id}>
              ${v.label}${v.is_default ? ` (${t("recipe.default")})` : ""}
            </option>`,
        )}
      </select>
      ${current && !current.is_default
        ? html`<button
            ?disabled=${this._busy}
            @click=${() =>
              this.run(async () => {
                await this.ctx.api.setDefaultVersion(r.id, current.id);
                await this.load();
              })}
          >
            ${t("recipe.set_default")}
          </button>`
        : nothing}
      ${!r.version.is_original
        ? html`<button
            @click=${async () => {
              this._showDiff = !this._showDiff;
              if (this._showDiff) await this.run(() => this.loadDiff());
            }}
          >
            ${this._showDiff ? t("recipe.hide_diff") : t("recipe.show_diff")}
          </button>`
        : nothing}
    </div>`;
  }

  private renderDiff() {
    return html`<div class="card section"><rb-diff .ctx=${this.ctx} .diff=${this._diff}></rb-diff></div>`;
  }

  private renderServings(r: Recipe) {
    const { t } = this.ctx;
    const servings = r.version.data.servings;
    if (!servings) return nothing;
    return html`<div class="row">
      <span class="stepper">
        <button class="icon" aria-label="−" @click=${() => this.changeServings(-1)}>
          <rb-icon .path=${mdiMinus}></rb-icon>
        </button>
        <input
          type="number"
          inputmode="decimal"
          min="0.5"
          step="0.5"
          aria-label=${t("recipe.servings")}
          .value=${formatNumber("en", servings, 2)}
          @change=${(e: Event) => this.setServings(Number((e.target as HTMLInputElement).value))}
        />
        <button class="icon" aria-label="+" @click=${() => this.changeServings(1)}>
          <rb-icon .path=${mdiPlus}></rb-icon>
        </button>
      </span>
      <span class="muted">${r.version.data.servings_unit ?? t("recipe.servings")}</span>
    </div>`;
  }

  private notesFor(r: Recipe, type: Annotation["target_type"], index: number) {
    return r.annotations
      .filter((a) => a.target_type === type && a.target_index === index)
      .map((a) => html`<div class="note">${a.text}${a.user_name ? html` – ${a.user_name}` : nothing}</div>`);
  }

  private renderIngredients(r: Recipe) {
    let group: string | null = null;
    return html`<ul class="ingredients">
      ${r.version.data.ingredients.map((ing, index) => {
        const header = ing.group && ing.group !== group ? html`<li class="group">${ing.group}</li>` : nothing;
        group = ing.group;
        const done = this._checked.has(index);
        return html`${header}
          <li class=${done ? "done" : ""} @click=${() => this.toggle(index)}>
            <input type="checkbox" .checked=${done} aria-label=${ing.name} tabindex="-1" />
            <span class="txt">
              ${ing.quantity ? html`<span class="qty">${ing.quantity}</span> ` : nothing}${ing.name}
              ${ing.note ? html`<span class="muted">(${ing.note})</span>` : nothing}
              ${this.notesFor(r, "ingredient", index)}
            </span>
          </li>`;
      })}
    </ul>`;
  }

  private renderSteps(r: Recipe) {
    const { t } = this.ctx;
    let group: string | null = null;
    return html`<ol class="steps">
      ${r.version.data.steps.map((step, index) => {
        const header = step.group && step.group !== group ? html`<h3 class="group">${step.group}</h3>` : nothing;
        group = step.group;
        return html`${header}
          <li>
            ${step.text}
            ${step.timer_seconds
              ? html`<div>
                  <button
                    @click=${() =>
                      timerStore.start(`${r.title} – ${t("timer.step", { n: index + 1 })}`, r.id, step.timer_seconds!)}
                  >
                    <rb-icon .path=${mdiTimerOutline}></rb-icon>
                    ${t("timer.start", { time: formatClock(step.timer_seconds * 1000) })}
                  </button>
                </div>`
              : nothing}
            ${this.notesFor(r, "step", index)}
          </li>`;
      })}
    </ol>`;
  }

  private renderNotes(r: Recipe) {
    const { t } = this.ctx;
    const notes = r.annotations.filter((a) => a.target_type === "recipe");
    return html`<h2>${t("recipe.notes")}</h2>
      ${notes.map(
        (a) =>
          html`<div class="note">
            ${a.text} <span class="muted">– ${a.user_name ?? ""}, ${formatDate(this.ctx.language, a.created)}</span>
          </div>`,
      )}
      <label for="note">${t("recipe.add_note")}</label>
      <div class="row">
        <input
          id="note"
          class="grow"
          .value=${this._note}
          placeholder=${t("recipe.note_placeholder")}
          @input=${(e: Event) => (this._note = (e.target as HTMLInputElement).value)}
        />
        <button
          class="primary"
          ?disabled=${!this._note.trim() || this._busy}
          @click=${() =>
            this.run(async () => {
              await this.ctx.api.annotate(r.id, this._note.trim());
              this._note = "";
              await this.load();
            })}
        >
          ${t("common.save")}
        </button>
      </div>`;
  }

  private renderRatings(r: Recipe) {
    const { t, language } = this.ctx;
    const s = r.stats;
    return html`<h2>${t("recipe.ratings")}</h2>
      ${s.avg_stars !== null
        ? html`<div class="row">
            <rb-stars .value=${s.avg_stars}></rb-stars>
            <span>${t("recipe.avg", { stars: formatNumber(language, s.avg_stars), n: s.rating_count })}</span>
          </div>`
        : html`<p class="muted">${t("recipe.no_ratings")}</p>`}
      <p class="muted">
        ${s.last_cooked
          ? t("recipe.last_cooked", { date: formatDate(language, s.last_cooked) })
          : t("recipe.never_cooked")}
        · ${t("list.cooked", { n: s.cooked_count })}
      </p>
      ${s.per_user.filter((u) => u.avg_stars !== null).map(
        (u) => html`<div class="row muted">
          <span>${u.user_name}</span><rb-stars .value=${u.avg_stars}></rb-stars>
        </div>`,
      )}
      <h3 class="section">${t("recipe.rate")}</h3>
      <rb-stars
        class="pick"
        editable
        .value=${this._stars}
        @change=${(e: CustomEvent<number>) => (this._stars = e.detail)}
      ></rb-stars>
      <label class="row">
        <input
          type="checkbox"
          style="width:22px"
          .checked=${this._cooked}
          @change=${(e: Event) => (this._cooked = (e.target as HTMLInputElement).checked)}
        />
        ${t("recipe.cooked")}
      </label>
      <label for="comment">${t("recipe.comment")}</label>
      <input
        id="comment"
        .value=${this._comment}
        @input=${(e: Event) => (this._comment = (e.target as HTMLInputElement).value)}
      />
      <div class="row section">
        <button class="primary" ?disabled=${this._busy} @click=${() => this.submitRating(r)}>
          ${t("common.save")}
        </button>
      </div>
      ${r.history.length
        ? html`<h3 class="section">${t("recipe.history")}</h3>
            <ul class="history">
              ${r.history.map(
                (h) =>
                  html`<li>
                    <span class="muted">${formatDate(language, h.cooked_at ?? h.created)} · ${h.user_name ?? ""}</span>
                    ${h.stars !== null ? html`<rb-stars .value=${h.stars}></rb-stars>` : nothing}
                    ${h.comment ? html`<div>${h.comment}</div>` : nothing}
                  </li>`,
              )}
            </ul>`
        : nothing}`;
  }

  private async submitRating(r: Recipe) {
    if (this._stars === null && !this._cooked && !this._comment.trim()) {
      this.ctx.toast(this.ctx.t("recipe.choose_stars"));
      return;
    }
    await this.run(async () => {
      await this.ctx.api.rate(r.id, this._stars, this._comment.trim(), this._cooked, r.version.id);
      this._stars = null;
      this._comment = "";
      await this.load();
    }, this.ctx.t("recipe.rated"));
  }

  private addToShopping = () => {
    const r = this._recipe;
    if (!r) return;
    void this.run(async () => {
      const result = await this.ctx.api.addToShoppingList(r.id, this._servings);
      this.ctx.toast(this.ctx.t("recipe.shopping_done", { n: result.items.length }));
    });
  };

  private deleteRecipe = () => {
    const r = this._recipe;
    if (!r) return;
    if (!this._confirmDelete) {
      this._confirmDelete = true;
      setTimeout(() => (this._confirmDelete = false), 4000);
      return;
    }
    void this.run(async () => {
      await this.ctx.api.deleteRecipe(r.id);
      this.ctx.go({ view: "list" });
    }, this.ctx.t("recipe.deleted"));
  };
}

if (!customElements.get("rb-recipe-view")) customElements.define("rb-recipe-view", RbRecipeView);
