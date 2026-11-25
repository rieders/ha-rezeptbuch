import { mdiStar, mdiStarHalfFull, mdiStarOutline } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import "./rb-icon";

/** Sterne anzeigen oder wählen (0,5–5 in halben Schritten). Linke Hälfte = halber Stern. */
export class RbStars extends LitElement {
  static override properties = {
    value: { type: Number },
    editable: { type: Boolean },
    label: { type: String },
  };
  declare value: number | null;
  declare editable: boolean;
  declare label: string;

  constructor() {
    super();
    this.value = null;
    this.editable = false;
    this.label = "";
  }

  static override styles = css`
    :host {
      display: inline-flex;
      color: var(--rb-star-color, #f5a623);
      --rb-icon-size: var(--rb-star-size, 20px);
    }
    .star {
      position: relative;
      display: inline-flex;
    }
    button {
      all: unset;
      position: absolute;
      top: -10px;
      bottom: -10px;
      width: 50%;
      cursor: pointer;
    }
    button.left {
      left: 0;
    }
    button.right {
      right: 0;
    }
    button:focus-visible {
      outline: 2px solid var(--primary-color);
    }
  `;

  private pick(value: number) {
    this.value = value;
    this.dispatchEvent(new CustomEvent("change", { detail: value, bubbles: true, composed: true }));
  }

  override render() {
    const v = this.value ?? 0;
    return html`${[1, 2, 3, 4, 5].map((n) => {
      const icon = v >= n ? mdiStar : v >= n - 0.5 ? mdiStarHalfFull : mdiStarOutline;
      return html`<span class="star"
        ><rb-icon .path=${icon}></rb-icon>
        ${this.editable
          ? html`<button class="left" aria-label=${`${n - 0.5}`} @click=${() => this.pick(n - 0.5)}></button
              ><button class="right" aria-label=${`${n}`} @click=${() => this.pick(n)}></button>`
          : nothing}</span
      >`;
    })}`;
  }
}

if (!customElements.get("rb-stars")) customElements.define("rb-stars", RbStars);
