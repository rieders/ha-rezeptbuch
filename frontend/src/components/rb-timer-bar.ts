import { mdiClose, mdiPause, mdiPlay, mdiTimerOutline, mdiVolumeOff } from "@mdi/js";
import { LitElement, css, html, nothing } from "lit";
import type { Translate } from "../i18n";
import { formatClock } from "../format";
import { shared } from "../styles";
import { timerStore } from "../timers";
import "./rb-icon";

/** Leiste mit allen laufenden/abgelaufenen Timern – unabhängig von der aktuellen Ansicht. */
export class RbTimerBar extends LitElement {
  static override properties = { t: { attribute: false } };
  declare t: Translate;
  private onChange = () => this.requestUpdate();
  private clock: ReturnType<typeof setInterval> | undefined;

  override connectedCallback(): void {
    super.connectedCallback();
    timerStore.addEventListener("change", this.onChange);
    this.clock = setInterval(() => timerStore.timers.length && this.requestUpdate(), 1000);
  }

  override disconnectedCallback(): void {
    super.disconnectedCallback();
    timerStore.removeEventListener("change", this.onChange);
    clearInterval(this.clock);
  }

  static override styles = [
    shared,
    css`
      :host {
        display: block;
      }
      .bar {
        display: flex;
        flex-wrap: wrap;
        gap: 8px;
        padding: 8px 12px;
        background: var(--card-background-color);
        border-top: 1px solid var(--divider-color);
        box-shadow: 0 -2px 6px rgba(0, 0, 0, 0.15);
      }
      .timer {
        display: flex;
        align-items: center;
        gap: 4px;
        padding: 0 4px 0 12px;
        border-radius: 24px;
        border: 1px solid var(--divider-color);
        min-height: 48px;
      }
      .time {
        font-size: 1.3rem;
        font-variant-numeric: tabular-nums;
        font-weight: 500;
      }
      .label {
        max-width: 220px;
        overflow: hidden;
        text-overflow: ellipsis;
        white-space: nowrap;
        font-size: 0.85rem;
      }
      .done {
        background: var(--warning-color, #ffa600);
        color: #000;
        animation: blink 1s steps(2, start) infinite;
      }
      @keyframes blink {
        to {
          opacity: 0.55;
        }
      }
      @media (prefers-reduced-motion: reduce) {
        .done {
          animation: none;
        }
      }
      .hint {
        width: 100%;
        --rb-icon-size: 18px;
      }
    `,
  ];

  override render() {
    const t = this.t;
    const timers = timerStore.timers;
    if (!timers.length) return nothing;
    const anyDone = timers.some((x) => x.state === "done");
    return html`<div class="bar" role="timer" aria-live="polite">
      ${timers.map(
        (x) => html`<div class="timer ${x.state === "done" ? "done" : ""}">
          <rb-icon .path=${mdiTimerOutline}></rb-icon>
          <span class="time">${formatClock(timerStore.remaining(x))}</span>
          <span class="label">${x.state === "done" ? t("timer.done", { label: x.label }) : x.label}</span>
          ${x.state === "running"
            ? html`<button class="icon" aria-label=${t("timer.pause")} @click=${() => timerStore.pause(x.id)}>
                <rb-icon .path=${mdiPause}></rb-icon>
              </button>`
            : x.state === "paused"
              ? html`<button class="icon" aria-label=${t("timer.resume")} @click=${() => timerStore.resume(x.id)}>
                  <rb-icon .path=${mdiPlay}></rb-icon>
                </button>`
              : nothing}
          <button
            class="icon"
            aria-label=${x.state === "done" ? t("timer.dismiss") : t("timer.stop")}
            @click=${() => timerStore.remove(x.id)}
          >
            <rb-icon .path=${mdiClose}></rb-icon>
          </button>
        </div>`,
      )}
      ${timerStore.soundBlocked && (anyDone || timers.length)
        ? html`<div class="hint warning row"><rb-icon .path=${mdiVolumeOff}></rb-icon>${t("timer.no_sound")}</div>`
        : nothing}
    </div>`;
  }
}

if (!customElements.get("rb-timer-bar")) customElements.define("rb-timer-bar", RbTimerBar);
