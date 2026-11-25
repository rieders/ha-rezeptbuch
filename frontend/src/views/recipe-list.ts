import { mdiClockOutline, mdiMagnify, mdiSilverwareForkKnife } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "../components/rb-icon";
import "../components/rb-stars";
import { type PanelContext, flattenCategories } from "../context";
import { formatMinutes } from "../format";
import { errorText } from "../i18n";
import { shared } from "../styles";
import type { CategoryTree, RecipeSummary } from "../types";

const PAGE = 60;
// Filter bleiben beim Wechsel zwischen Ansichten erhalten
const lastFilter = { query: "", category: "", tag: "", sort: "name" };

export class RbRecipeList extends LitElement {
  static override properties = {
    ctx: { attribute: false },
    _items: { state: true },
    _total: { state: true },
    _tree: { state: true },
    _tags: { state: true },
    _loading: { state: true },
    _error: { state: true },
  };
  declare ctx: PanelContext;
  declare _items: RecipeSummary[];
  declare _total: number;
  declare _tree: CategoryTree | null;
  declare _tags: { name: string; count: number }[];
  declare _loading: boolean;
  declare _error: string;
  private _timer: ReturnType<typeof setTimeout> | undefined;

  constructor() {
    super();
    this._items = [];
    this._total = 0;
    this._tree = null;
    this._tags = [];
    this._loading = false;
    this._error = "";
  }

  override connectedCallback(): void {
    super.connectedCallback();
    void this.loadMeta();
    void this.load(true);
  }

  private async loadMeta() {
    try {
      const [tree, tags] = await Promise.all([this.ctx.api.categories(), this.ctx.api.tags()]);
      this._tree = tree;
      this._tags = tags.tags;
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    }
  }

  private async load(reset: boolean) {
    this._loading = true;
    this._error = "";
    const category = lastFilter.category;
    try {
      const result = await this.ctx.api.list({
        query: lastFilter.query || undefined,
        category_id: category && category !== "none" ? Number(category) : undefined,
        uncategorized: category === "none",
        tags: lastFilter.tag ? [lastFilter.tag] : [],
        sort: lastFilter.query && lastFilter.sort === "name" ? "relevance" : lastFilter.sort,
        limit: PAGE,
        offset: reset ? 0 : this._items.length,
      });
      this._items = reset ? result.items : [...this._items, ...result.items];
      this._total = result.total;
    } catch (err) {
      this._error = errorText(this.ctx.t, this.ctx.fail(err));
    } finally {
      this._loading = false;
    }
  }

  private setFilter(key: keyof typeof lastFilter, value: string, debounce = false) {
    lastFilter[key] = value;
    clearTimeout(this._timer);
    if (debounce) this._timer = setTimeout(() => void this.load(true), 300);
    else void this.load(true);
  }

  static override styles = [
    shared,
    css`
      .filters {
        display: grid;
        grid-template-columns: 2fr 1.4fr 1fr 1fr;
        gap: 8px;
        margin-bottom: 16px;
      }
      @media (max-width: 800px) {
        .filters {
          grid-template-columns: 1fr 1fr;
        }
        .search {
          grid-column: 1 / -1;
        }
      }
      .search {
        position: relative;
      }
      .search rb-icon {
        position: absolute;
        left: 10px;
        top: 10px;
        color: var(--secondary-text-color);
      }
      .search input {
        padding-left: 40px;
      }
      .grid {
        display: grid;
        grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
        gap: 12px;
      }
      a.tile {
        display: flex;
        flex-direction: column;
        color: inherit;
        text-decoration: none;
        background: var(--card-background-color);
        border-radius: var(--ha-card-border-radius, 12px);
        box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.2));
        overflow: hidden;
        min-height: 44px;
      }
      .thumb {
        aspect-ratio: 4 / 3;
        background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
        display: flex;
        align-items: center;
        justify-content: center;
        color: var(--secondary-text-color);
        --rb-icon-size: 48px;
      }
      .thumb img {
        width: 100%;
        height: 100%;
        object-fit: cover;
      }
      .body {
        padding: 10px 12px 12px;
        display: flex;
        flex-direction: column;
        gap: 4px;
      }
      .title {
        font-weight: 500;
        line-height: 1.3;
      }
      .meta {
        font-size: 0.85rem;
        --rb-icon-size: 16px;
        --rb-star-size: 16px;
      }
      .more {
        display: flex;
        justify-content: center;
        margin: 16px 0;
      }
    `,
  ];

  override render() {
    const { t } = this.ctx;
    const categories = this._tree ? flattenCategories(this._tree.categories) : [];
    return html`
      <div class="filters">
        <div class="search">
          <rb-icon .path=${mdiMagnify}></rb-icon>
          <input
            type="search"
            .value=${lastFilter.query}
            placeholder=${t("list.search")}
            aria-label=${t("list.search")}
            @input=${(e: Event) => this.setFilter("query", (e.target as HTMLInputElement).value, true)}
          />
        </div>
        <select
          aria-label=${t("list.category")}
          @change=${(e: Event) => this.setFilter("category", (e.target as HTMLSelectElement).value)}
        >
          <option value="" ?selected=${!lastFilter.category}>${t("list.all_categories")}</option>
          ${categories.map(
            ({ category, depth }) =>
              html`<option value=${String(category.id)} ?selected=${lastFilter.category === String(category.id)}>
                ${" ".repeat(depth)}${category.name} (${category.count_total})
              </option>`,
          )}
          <option value="none" ?selected=${lastFilter.category === "none"}>
            ${t("list.uncategorized")} (${this._tree?.uncategorized ?? 0})
          </option>
        </select>
        <select
          aria-label=${t("list.tag")}
          @change=${(e: Event) => this.setFilter("tag", (e.target as HTMLSelectElement).value)}
        >
          <option value="" ?selected=${!lastFilter.tag}>${t("list.all_tags")}</option>
          ${this._tags.map(
            (tag) => html`<option value=${tag.name} ?selected=${lastFilter.tag === tag.name}>${tag.name}</option>`,
          )}
        </select>
        <select
          aria-label=${t("list.sort")}
          @change=${(e: Event) => this.setFilter("sort", (e.target as HTMLSelectElement).value)}
        >
          ${(["name", "rating", "last_cooked", "least_recently_cooked", "new"] as const).map(
            (s) => html`<option value=${s} ?selected=${lastFilter.sort === s}>${t(`sort.${s}`)}</option>`,
          )}
        </select>
      </div>
      ${this._error ? html`<p class="error">${this._error}</p>` : nothing}
      <p class="muted">${t("list.count", { n: this._total })}</p>
      ${!this._loading && !this._items.length ? html`<p class="muted">${t("list.empty")}</p>` : nothing}
      <div class="grid">${this._items.map((r) => this.renderTile(r))}</div>
      ${this._items.length < this._total
        ? html`<div class="more">
            <button ?disabled=${this._loading} @click=${() => this.load(false)}>${t("common.load_more")}</button>
          </div>`
        : nothing}
      ${this._loading ? html`<p class="muted">${t("common.loading")}</p>` : nothing}
    `;
  }

  private renderTile(r: RecipeSummary) {
    const { t } = this.ctx;
    const time = formatMinutes(t, r.total_time);
    return html`<a
      class="tile"
      href=${`${this.ctx.prefix}/rezept/${r.recipe_id}`}
      @click=${(e: MouseEvent) => {
        if (e.ctrlKey || e.metaKey || e.button !== 0) return;
        e.preventDefault();
        this.ctx.go({ view: "recipe", recipeId: r.recipe_id });
      }}
    >
      <div class="thumb">
        ${r.image_url
          ? html`<img src=${r.image_url} alt="" loading="lazy" />`
          : html`<rb-icon .path=${mdiSilverwareForkKnife}></rb-icon>`}
      </div>
      <div class="body">
        <span class="title">${r.title}</span>
        <span class="meta row muted">
          ${r.avg_stars !== null ? html`<rb-stars .value=${r.avg_stars}></rb-stars>` : nothing}
          ${time ? html`<span class="row"><rb-icon .path=${mdiClockOutline}></rb-icon>${time}</span>` : nothing}
          ${r.cooked_count ? html`<span>${t("list.cooked", { n: r.cooked_count })}</span>` : nothing}
        </span>
      </div>
    </a>`;
  }
}

if (!customElements.get("rb-recipe-list")) customElements.define("rb-recipe-list", RbRecipeList);
