import { css } from "lit";

// Nur HA-Theme-Variablen (hell/dunkel automatisch), Systemschrift, keine externen Ressourcen.
// Touch-Ziele mind. 44 px (Companion-App, Tablet).
export const shared = css`
  :host {
    color: var(--primary-text-color);
    font-family: var(--ha-font-family-body, var(--paper-font-body1_-_font-family, system-ui, sans-serif));
    -webkit-tap-highlight-color: transparent;
  }
  * {
    box-sizing: border-box;
  }
  .card {
    background: var(--card-background-color, #fff);
    border-radius: var(--ha-card-border-radius, 12px);
    box-shadow: var(--ha-card-box-shadow, 0 1px 3px rgba(0, 0, 0, 0.2));
    border: var(--ha-card-border-width, 0) solid var(--divider-color);
    padding: 16px;
  }
  h1,
  h2,
  h3 {
    margin: 0 0 8px;
    font-weight: 500;
  }
  h1 {
    font-size: 1.5rem;
  }
  h2 {
    font-size: 1.2rem;
  }
  h3 {
    font-size: 1rem;
  }
  button,
  .btn {
    font: inherit;
    min-height: 44px;
    min-width: 44px;
    padding: 0 14px;
    border-radius: 22px;
    border: 1px solid var(--divider-color);
    background: var(--card-background-color, transparent);
    color: var(--primary-text-color);
    cursor: pointer;
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 6px;
    text-decoration: none;
  }
  button.primary {
    background: var(--primary-color);
    border-color: var(--primary-color);
    color: var(--text-primary-color, #fff);
  }
  button.danger {
    color: var(--error-color, #db4437);
    border-color: var(--error-color, #db4437);
  }
  button.icon {
    padding: 0;
    border: none;
    background: transparent;
    border-radius: 50%;
  }
  button:disabled {
    opacity: 0.5;
    cursor: default;
  }
  button:focus-visible,
  input:focus-visible,
  select:focus-visible,
  textarea:focus-visible {
    outline: 2px solid var(--primary-color);
    outline-offset: 2px;
  }
  input,
  select,
  textarea {
    font: inherit;
    color: var(--primary-text-color);
    background: var(--secondary-background-color, var(--card-background-color));
    border: 1px solid var(--divider-color);
    border-radius: 8px;
    min-height: 44px;
    padding: 8px 12px;
    width: 100%;
  }
  textarea {
    min-height: 160px;
    resize: vertical;
    line-height: 1.5;
  }
  label {
    display: block;
    font-size: 0.85rem;
    color: var(--secondary-text-color);
    margin: 12px 0 4px;
  }
  .muted {
    color: var(--secondary-text-color);
  }
  .row {
    display: flex;
    gap: 8px;
    align-items: center;
    flex-wrap: wrap;
  }
  .grow {
    flex: 1 1 auto;
  }
  .warning {
    background: color-mix(in srgb, var(--warning-color, #ffa600) 18%, transparent);
    border-left: 4px solid var(--warning-color, #ffa600);
    padding: 8px 12px;
    border-radius: 6px;
  }
  .error {
    background: color-mix(in srgb, var(--error-color, #db4437) 15%, transparent);
    border-left: 4px solid var(--error-color, #db4437);
    padding: 8px 12px;
    border-radius: 6px;
  }
  .chip {
    display: inline-flex;
    align-items: center;
    min-height: 28px;
    padding: 0 10px;
    border-radius: 14px;
    background: var(--secondary-background-color, rgba(127, 127, 127, 0.15));
    font-size: 0.85rem;
  }
  img {
    max-width: 100%;
  }
`;
