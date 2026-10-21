// Lovelace cards for the AVAccess Matrix dashboard.
// Same graphite field, charcoal keys, and blue latch as Sports Routing.
// Loaded from frontend.extra_module_url so Lovelace can use custom:avaccess-key.

const VIEW_STYLE_ID = "avaccess-matrix-view-style";

const VIEW_CSS = `
.avaccess-matrix {
  background: #101010 !important;
  color: #f3f3f3;
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
}
.avaccess-matrix ha-card {
  background: #1a1a1a;
  border: 0;
  border-radius: 3px;
  box-shadow: none;
  color: #f3f3f3;
}
.avaccess-matrix hui-markdown-card ha-card,
.avaccess-matrix ha-card.type-markdown {
  background: transparent;
  box-shadow: none;
}
.avaccess-matrix ha-markdown,
.avaccess-matrix ha-markdown p,
.avaccess-matrix ha-markdown a {
  color: #c8c8c8;
}
.avaccess-matrix ha-markdown h1,
.avaccess-matrix ha-markdown h2,
.avaccess-matrix ha-markdown h3 {
  color: #8d8d8d;
  font-size: 14px;
  font-weight: 500;
  letter-spacing: 0;
  margin: 10px 0 0;
}
.avaccess-matrix hui-entities-card .card-header {
  color: #8d8d8d;
  font-size: 14px;
  font-weight: 500;
}
`;

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function markMatrixView(element) {
  const view = element.closest("hui-panel-view, hui-view, hui-root");
  if (view) view.classList.add("avaccess-matrix");
  if (document.getElementById(VIEW_STYLE_ID)) return;
  const style = document.createElement("style");
  style.id = VIEW_STYLE_ID;
  style.textContent = VIEW_CSS;
  document.head.appendChild(style);
}

class AvaccessLabel extends HTMLElement {
  setConfig(config) {
    this._config = config || {};
  }

  set hass(_hass) {}

  connectedCallback() {
    markMatrixView(this);
    this._paint();
  }

  getCardSize() {
    return this._config?.variant === "room" ? 1 : 0;
  }

  _paint() {
    const text = escapeHtml(this._config?.text || "");
    const room = this._config?.variant === "room";
    this.innerHTML = `
      <style>
        :host { display: block; }
        p { margin: 0; }
        .room {
          color: #f3f3f3;
          font-size: 22px;
          font-weight: 650;
          letter-spacing: -0.02em;
          padding: 8px 4px 0;
        }
        .section {
          color: #8d8d8d;
          font-size: 14px;
          font-weight: 500;
          padding: 14px 4px 0;
        }
      </style>
      <p class="${room ? "room" : "section"}">${text}</p>
    `;
  }
}

class AvaccessKey extends HTMLElement {
  setConfig(config) {
    if (!config || !config.name || !config.tap_action) {
      throw new Error("avaccess-key needs name and tap_action");
    }
    this._config = config;
  }

  set hass(hass) {
    this._hass = hass;
    const on = this._isOn();
    if (this._painted && on === this._on) return;
    this._on = on;
    this._painted = true;
    this._paint();
  }

  connectedCallback() {
    markMatrixView(this);
    if (!this._painted) this._paint();
  }

  getCardSize() {
    return 1;
  }

  _isOn() {
    const variant = this._config?.variant || "choice";
    if (variant === "action") return true;
    if (variant === "favorite") return false;
    const entity = this._config.selected_entity;
    const expected = this._config.selected_state;
    if (!entity || expected == null || !this._hass?.states?.[entity]) return false;
    return this._hass.states[entity].state === expected;
  }

  _paint() {
    const name = escapeHtml(this._config?.name || "");
    const detail = this._config?.detail ? escapeHtml(this._config.detail) : "";
    const on = this._isOn();
    this.innerHTML = `
      <style>
        :host { display: block; }
        button {
          align-items: center;
          background: linear-gradient(#323232, #2a2a2a);
          border: 0;
          border-radius: 3px;
          box-shadow: inset 0 1px 0 rgba(255, 255, 255, 0.07);
          color: #f3f3f3;
          cursor: pointer;
          display: flex;
          font: inherit;
          min-height: 68px;
          padding: 10px 14px;
          text-align: left;
          width: 100%;
        }
        button.on {
          background: linear-gradient(#1470d4, #0b5cab);
        }
        b {
          display: block;
          font-size: 17px;
          font-weight: 650;
        }
        small {
          color: #bdbdbd;
          display: block;
          font-size: 13px;
          margin-top: 2px;
        }
        button.on small { color: #d7e7f8; }
      </style>
      <button type="button" class="key${on ? " on" : ""}">
        <span><b>${name}</b>${detail ? `<small>${detail}</small>` : ""}</span>
      </button>
    `;
    this.querySelector("button").addEventListener("click", () => this._run());
  }

  _run() {
    const tap = this._config.tap_action || {};
    const service = String(tap.service || "");
    const dot = service.indexOf(".");
    if (!this._hass || dot < 1) return;
    this._hass.callService(service.slice(0, dot), service.slice(dot + 1), tap.data || {});
  }
}

if (!customElements.get("avaccess-label")) {
  customElements.define("avaccess-label", AvaccessLabel);
}
if (!customElements.get("avaccess-key")) {
  customElements.define("avaccess-key", AvaccessKey);
}
