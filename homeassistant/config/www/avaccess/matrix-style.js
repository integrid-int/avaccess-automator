// Lovelace cards for the AVAccess Matrix dashboard.
// Loaded from frontend.extra_module_url / lovelace resources.

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
  const view = element?.closest?.("hui-panel-view, hui-view, hui-root");
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
    if (this.isConnected) this._paint();
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
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const text = escapeHtml(this._config?.text || "");
    const room = this._config?.variant === "room";
    this.shadowRoot.innerHTML = `
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
    // Never throw — Lovelace turns setConfig exceptions into "Configuration error".
    this._config = config && typeof config === "object" ? config : {};
    this._painted = false;
    if (this.isConnected) {
      this._on = this._isOn();
      this._painted = true;
      this._paint();
    }
  }

  set hass(hass) {
    this._hass = hass;
    if (!this._config) return;
    const on = this._isOn();
    if (this._painted && on === this._on) return;
    this._on = on;
    this._painted = true;
    this._paint();
  }

  connectedCallback() {
    markMatrixView(this);
    if (!this._painted && this._config) {
      this._on = this._isOn();
      this._painted = true;
      this._paint();
    }
  }

  getCardSize() {
    return 1;
  }

  _isOn() {
    const cfg = this._config || {};
    const variant = cfg.variant || "choice";
    if (variant === "action") return true;
    if (variant === "favorite") return false;
    const entity = cfg.selected_entity;
    const expected = cfg.selected_state;
    if (!entity || expected == null || !this._hass?.states?.[entity]) return false;
    return this._hass.states[entity].state === expected;
  }

  _paint() {
    if (!this.shadowRoot) this.attachShadow({ mode: "open" });
    const cfg = this._config || {};
    const name = escapeHtml(cfg.name || "—");
    const detail = cfg.detail ? escapeHtml(cfg.detail) : "";
    const on = this._isOn();
    this.shadowRoot.innerHTML = `
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
    const button = this.shadowRoot.querySelector("button");
    if (button) button.addEventListener("click", () => this._run());
  }

  _run() {
    const tap = this._config?.tap_action || {};
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

window.customCards = window.customCards || [];
for (const card of [
  { type: "avaccess-label", name: "AVAccess Label", description: "Matrix section/room label" },
  { type: "avaccess-key", name: "AVAccess Key", description: "Matrix charcoal action key" },
]) {
  if (!window.customCards.some((c) => c.type === card.type)) {
    window.customCards.push(card);
  }
}

// Rebuild any Lovelace error cards that rendered before this module finished loading.
window.dispatchEvent(new Event("ll-rebuild", { bubbles: true }));
