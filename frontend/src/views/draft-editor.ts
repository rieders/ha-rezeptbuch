import { mdiArrowLeft, mdiCheck, mdiDelete } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "../components/rb-icon";
import { type PanelContext, flattenCategories } from "../context";
import { splitLines, splitSteps, splitTags } from "../format";
import { errorText } from "../i18n";
import { shared } from "../styles";
import type { CategoryTree, Draft } from "../types";

interface Form {
  title: string;
  description: string;
  servings: string;
  servings_unit: string;
  prep_time: string;
  cook_time: string;
  total_time: string;
  ingredients: string;
  steps: string;
  tags: string;
  category_ids: number[];
  image: string | null;
}

function toForm(d: Draft): Form {
  const v = d.version;
  return {
    title: d.title,
    description: d.description,
    servings: v.servings ? String(v.servings) : "",
    servings_unit: v.servings_unit ?? "",
    prep_time: v.prep_time ? String(v.prep_time) : "",
    cook_time: v.cook_time ? String(v.cook_time) : "",
    total_time: v.total_time ? String(v.total_time) : "",
    ingredients: d.ingredient_lines.join("\n"),
    steps: d.step_lines.join("\n\n"),
    tags: d.tags.join(", "),
    category_ids: [...d.category_ids],
    image: d.image,
  };
}

const num = (v: string) => (v.trim() ? Number(v.replace(",", ".")) : null);

export class RbDraftEditor extends LitElement {
  static override properties = {
    ctx: { attribute: false },
    draftId: { type: Number },
    _draft: { state: true },
    _form: { state: true },
    _tree: { state: true },
    _error: { state: true },
    _busy: { state: true },
    _duplicate: { state: true },
    _confirmDiscard: { state: true },
  };
  declare ctx: PanelContext;
  declare draftId: number;
  declare _draft: Draft | null;
  declare _form: Form | null;
  declare _tree: CategoryTree | null;
  declare _error: string;
  declare _busy: boolean;
  declare _duplicate: boolean;
  declare _confirmDiscard: boolean;

  constructor() {
    super();
    this._draft = null;
    this._form = null;
    this._tree = null;
    this._error = "";
    this._busy = false;
    this._duplicate = false;
    this._confirmDiscard = false;
  }

  override updated(changed: Map<string, unknown>): void {
    if (changed.has("draftId")) void this.load();
  }

  private async load() {
    this._error = "";
    try {
      const [draft, tree] = await Promise.all([this.ctx.api.draft(this.draftId), this.ctx.api.categories()]);
      this._draft = draft;
      this._form = toForm(draft);
      this._tree = tree;
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    }
  }

  private set<K extends keyof Form>(key: K, value: Form[K]) {
    if (this._form) this._form = { ...this._form, [key]: value };
  }

  private async save(): Promise<boolean> {
    const f = this._form;
    if (!f) return false;
    try {
      const draft = await this.ctx.api.updateDraft(this.draftId, {
        title: f.title.trim(),
        description: f.description.trim(),
        servings: num(f.servings),
        servings_unit: f.servings_unit.trim() || null,
        prep_time: num(f.prep_time),
        cook_time: num(f.cook_time),
        total_time: num(f.total_time),
        ingredient_lines: splitLines(f.ingredients),
        step_lines: splitSteps(f.steps),
        tags: splitTags(f.tags),
        category_ids: f.category_ids,
        image: f.image,
      });
      this._draft = draft;
      this._form = toForm(draft);
      return true;
    } catch (err) {
      this.ctx.toast(errorText(this.ctx.t, this.ctx.fail(err)));
      return false;
    }
  }

  private async onSave() {
    this._busy = true;
    if (await this.save()) this.ctx.toast(this.ctx.t("draft.saved"));
    this._busy = false;
  }

  private async onConfirm(allowDuplicate = false) {
    this._busy = true;
    try {
      if (!(await this.save())) return;
      const result = await this.ctx.api.confirmDraft(this.draftId, allowDuplicate);
      this.ctx.go({ view: "recipe", recipeId: result.recipe_id });
    } catch (err) {
      const e = this.ctx.fail(err);
      if (e.code === "duplicate_recipe") this._duplicate = true;
      else this.ctx.toast(errorText(this.ctx.t, e));
    } finally {
      this._busy = false;
    }
  }

  private async onDiscard() {
    if (!this._confirmDiscard) {
      this._confirmDiscard = true;
      setTimeout(() => (this._confirmDiscard = false), 4000);
      return;
    }
    this._busy = true;
    try {
      await this.ctx.api.discardDraft(this.draftId);
      this.ctx.toast(this.ctx.t("draft.discarded"));
      this.ctx.go({ view: "drafts" });
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
        flex: 1;
        margin: 0;
      }
      .layout {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 16px;
        align-items: start;
      }
      @media (max-width: 860px) {
        .layout {
          grid-template-columns: 1fr;
        }
      }
      .nums {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(130px, 1fr));
        gap: 0 8px;
      }
      textarea.ing {
        min-height: 260px;
      }
      textarea.steps {
        min-height: 320px;
      }
      .cats {
        max-height: 260px;
        overflow: auto;
        border: 1px solid var(--divider-color);
        border-radius: 8px;
        padding: 4px 8px;
      }
      .cats label {
        display: flex;
        align-items: center;
        gap: 8px;
        min-height: 40px;
        margin: 0;
        color: var(--primary-text-color);
        font-size: 1rem;
      }
      .cats input,
      .images input {
        width: 22px;
        min-height: 22px;
      }
      .images {
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
      }
      .images label {
        display: flex;
        flex-direction: column;
        align-items: center;
        gap: 4px;
        margin: 0;
      }
      .images img {
        width: 110px;
        height: 110px;
        object-fit: cover;
        border-radius: 8px;
      }
      .actions {
        position: sticky;
        bottom: 0;
        padding: 12px 0;
        background: var(--primary-background-color);
        display: flex;
        gap: 8px;
        flex-wrap: wrap;
        justify-content: flex-end;
      }
      .warning ul {
        margin: 4px 0 0;
        padding-left: 1.2em;
      }
    `,
  ];

  override render() {
    const { t } = this.ctx;
    if (this._error) return html`<p class="error">${this._error}</p>`;
    const d = this._draft;
    const f = this._form;
    if (!d || !f) return html`<p class="muted">${t("common.loading")}</p>`;
    const value = (e: Event) => (e.target as HTMLInputElement | HTMLTextAreaElement).value;
    return html`
      <div class="top">
        <button class="icon" aria-label=${t("common.back")} @click=${() => this.ctx.go({ view: "drafts" })}>
          <rb-icon .path=${mdiArrowLeft}></rb-icon>
        </button>
        <h1>${f.title || "–"}</h1>
      </div>
      ${d.warnings.length
        ? html`<div class="warning">
            <strong>${t("draft.warnings")}</strong>
            <ul>
              ${d.warnings.map((w) => html`<li>${w}</li>`)}
            </ul>
          </div>`
        : nothing}
      ${d.similar_recipes.length
        ? html`<p class="row">
            ${t("draft.similar")}:
            ${d.similar_recipes.map(
              (s) => html`<button @click=${() => this.ctx.go({ view: "recipe", recipeId: s.id })}>${s.title}</button>`,
            )}
          </p>`
        : nothing}
      <div class="layout">
        <div class="card">
          <label for="title">${t("draft.title")}</label>
          <input id="title" .value=${f.title} @input=${(e: Event) => this.set("title", value(e))} />
          <label for="desc">${t("draft.description")}</label>
          <input id="desc" .value=${f.description} @input=${(e: Event) => this.set("description", value(e))} />
          <div class="nums">
            ${(
              [
                ["servings", "draft.servings"],
                ["prep_time", "draft.prep"],
                ["cook_time", "draft.cook"],
                ["total_time", "draft.total"],
              ] as const
            ).map(
              ([key, label]) =>
                html`<div>
                  <label for=${key}>${t(label)}</label>
                  <input
                    id=${key}
                    inputmode="decimal"
                    .value=${f[key]}
                    @input=${(e: Event) => this.set(key, value(e))}
                  />
                </div>`,
            )}
            <div>
              <label for="unit">${t("draft.servings_unit")}</label>
              <input id="unit" .value=${f.servings_unit} @input=${(e: Event) => this.set("servings_unit", value(e))} />
            </div>
          </div>
          <label for="ing">${t("draft.ingredients")}</label>
          <textarea
            id="ing"
            class="ing"
            .value=${f.ingredients}
            @input=${(e: Event) => this.set("ingredients", value(e))}
          ></textarea>
        </div>
        <div class="card">
          <label for="steps">${t("draft.steps")}</label>
          <textarea
            id="steps"
            class="steps"
            .value=${f.steps}
            @input=${(e: Event) => this.set("steps", value(e))}
          ></textarea>
          ${this.renderCategories(f)}
          <label for="tags">${t("draft.tags")}</label>
          <input id="tags" .value=${f.tags} @input=${(e: Event) => this.set("tags", value(e))} />
          ${this.renderImages(d, f)}
        </div>
      </div>
      <div class="actions">
        ${this._duplicate
          ? html`<span class="warning grow">${t("draft.duplicate")}</span>
              <button ?disabled=${this._busy} @click=${() => this.onConfirm(true)}>${t("draft.save_anyway")}</button>`
          : nothing}
        <button class="danger" ?disabled=${this._busy} @click=${this.onDiscard}>
          <rb-icon .path=${mdiDelete}></rb-icon>${this._confirmDiscard ? t("draft.confirm_discard") : t("draft.discard")}
        </button>
        <button ?disabled=${this._busy} @click=${this.onSave}>${t("draft.save")}</button>
        <button class="primary" ?disabled=${this._busy || !f.title.trim()} @click=${() => this.onConfirm()}>
          <rb-icon .path=${mdiCheck}></rb-icon>${t("draft.confirm")}
        </button>
      </div>
    `;
  }

  private renderCategories(f: Form) {
    const { t } = this.ctx;
    const items = this._tree ? flattenCategories(this._tree.categories) : [];
    return html`<label>${t("draft.categories")}</label>
      <div class="cats">
        ${items.map(
          ({ category, depth }) =>
            html`<label style=${`padding-left:${depth * 20}px`}>
              <input
                type="checkbox"
                .checked=${f.category_ids.includes(category.id)}
                @change=${(e: Event) => {
                  const on = (e.target as HTMLInputElement).checked;
                  const ids = f.category_ids.filter((id) => id !== category.id);
                  this.set("category_ids", on ? [...ids, category.id] : ids);
                }}
              />
              ${category.name}
            </label>`,
        )}
      </div>`;
  }

  private renderImages(d: Draft, f: Form) {
    const { t } = this.ctx;
    if (!d.images.length) return nothing;
    return html`<label>${t("draft.image")}</label>
      <div class="images">
        <label>
          <span style="width:110px;height:110px;display:flex;align-items:center;justify-content:center" class="muted"
            >${t("draft.no_image")}</span
          >
          <input type="radio" name="img" .checked=${!f.image} @change=${() => this.set("image", null)} />
        </label>
        ${d.images.map(
          (img) =>
            html`<label>
              ${img.url ? html`<img src=${img.url} alt="" />` : nothing}
              <input
                type="radio"
                name="img"
                .checked=${f.image === img.path}
                @change=${() => this.set("image", img.path)}
              />
            </label>`,
        )}
      </div>`;
  }
}

if (!customElements.get("rb-draft-editor")) customElements.define("rb-draft-editor", RbDraftEditor);
