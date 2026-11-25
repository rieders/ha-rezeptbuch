import { LitElement, css, html, nothing } from "lit";
import type { PanelContext } from "../context";
import { shared } from "../styles";
import type { VersionDiff } from "../types";

/** Farbiger Versionsvergleich: neu (grün), gestrichen (rot, durchgestrichen), geändert (gelb). */
export class RbDiff extends LitElement {
  static override properties = { ctx: { attribute: false }, diff: { attribute: false } };
  declare ctx: PanelContext;
  declare diff: VersionDiff | null;

  static override styles = [
    shared,
    css`
      ul {
        list-style: none;
        padding: 0;
        margin: 0 0 12px;
      }
      li {
        padding: 6px 8px;
        border-radius: 6px;
        margin-bottom: 4px;
      }
      .added,
      ins {
        background: color-mix(in srgb, var(--success-color, #43a047) 20%, transparent);
        text-decoration: none;
      }
      .removed,
      del {
        background: color-mix(in srgb, var(--error-color, #db4437) 16%, transparent);
        text-decoration: line-through;
      }
      .changed {
        background: color-mix(in srgb, var(--warning-color, #ffa600) 20%, transparent);
      }
      .badge {
        font-size: 0.75rem;
        text-transform: uppercase;
        margin-right: 6px;
        opacity: 0.8;
      }
    `,
  ];

  override render() {
    const d = this.diff;
    const { t } = this.ctx;
    if (!d) return nothing;
    if (!d.has_changes) return html`<p class="muted">${t("recipe.no_diff")}</p>`;
    const badge = (status: string) =>
      status === "unchanged" ? nothing : html`<span class="badge">${t(`diff.${status as "added"}`)}</span>`;
    return html`
      ${d.meta.length
        ? html`<ul>
            ${d.meta.map((m) => html`<li class="changed">${m.label}: ${m.old ?? "–"} → ${m.new ?? "–"}</li>`)}
          </ul>`
        : nothing}
      <h3>${t("recipe.ingredients")}</h3>
      <ul>
        ${d.ingredients
          .filter((e) => e.status !== "unchanged")
          .map(
            (e) =>
              html`<li class=${e.status}>
                ${badge(e.status)}${e.summary || (e.new ?? e.old)?.name}
              </li>`,
          )}
      </ul>
      <h3>${t("recipe.steps")}</h3>
      <ul>
        ${d.steps
          .filter((e) => e.status !== "unchanged")
          .map(
            (e) =>
              html`<li class=${e.status}>
                ${badge(e.status)}
                ${e.words && e.words.length
                  ? e.words.map((w) =>
                      w.op === "insert" ? html`<ins>${w.text}</ins>` : w.op === "delete" ? html`<del>${w.text}</del>` : w.text,
                    )
                  : (e.new ?? e.old)?.text}
              </li>`,
          )}
      </ul>
    `;
  }
}

if (!customElements.get("rb-diff")) customElements.define("rb-diff", RbDiff);
