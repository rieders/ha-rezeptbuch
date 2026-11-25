import { LitElement, css, html, svg } from "lit";

/** SVG-Icon aus einem MDI-Pfad (@mdi/js, im Bundle – keine Icon-Fonts von außen). */
export class RbIcon extends LitElement {
  static override properties = { path: { type: String } };
  declare path: string;

  static override styles = css`
    :host {
      display: inline-flex;
      width: var(--rb-icon-size, 24px);
      height: var(--rb-icon-size, 24px);
      flex: none;
    }
    svg {
      width: 100%;
      height: 100%;
      fill: currentColor;
    }
  `;

  override render() {
    return html`<svg viewBox="0 0 24 24" aria-hidden="true">${svg`<path d=${this.path ?? ""}></path>`}</svg>`;
  }
}

if (!customElements.get("rb-icon")) customElements.define("rb-icon", RbIcon);
