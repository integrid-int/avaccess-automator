// AVAccess Matrix sidebar panel. Same charcoal keys as Sports Routing.
// Taps call the Matrix scripts and helpers; nothing here is a Lovelace card.

const PROGRAMS = [
  { key: "program_a", name: "Program A", detail: "ENC-01 · H25-01" },
  { key: "program_b", name: "Program B", detail: "ENC-02 · H25-02" },
  { key: "program_c", name: "Program C", detail: "ENC-03 · H25-03" },
  { key: "program_d", name: "Program D", detail: "ENC-04 · H25-04" },
  { key: "program_e", name: "Program E", detail: "ENC-05 · H25-05" },
  { key: "program_f", name: "Program F", detail: "ENC-06 · H25-06" },
  { key: "program_g", name: "Program G", detail: "ENC-07 · H25-07" },
  { key: "program_h", name: "Program H", detail: "ENC-08 · H25-08" },
  { key: "program_i", name: "Program I", detail: "ENC-09 · H25-09" },
];

const CHANNELS = [
  { option: "ESPN", detail: "206", pages: ["control", "favorites"] },
  { option: "ESPN2", detail: "209", pages: ["control", "favorites"] },
  { option: "FS1", detail: "219", pages: ["control", "favorites"] },
  { option: "TNT", detail: "245", pages: ["control", "favorites"] },
  { option: "WGHP FOX (Local)", detail: "8", pages: ["control", "favorites"] },
  { option: "WFMY CBS (Local)", detail: "2", pages: ["control", "favorites"] },
  { option: "WXII NBC (Local)", detail: "12", pages: ["control", "favorites"] },
  { option: "WXLV ABC (Local)", detail: "45", pages: ["control", "favorites"] },
  { option: "NFL A1", detail: "705", pages: ["control", "nfl"] },
  { option: "NFL A2", detail: "706", pages: ["control", "nfl"] },
  { option: "NFL A3", detail: "707", pages: ["control", "nfl"] },
  { option: "NFL A4", detail: "708", pages: ["control", "nfl"] },
  { option: "NFL S1", detail: "9554", pages: ["control", "nfl"] },
  { option: "NFL S2", detail: "9555", pages: ["control", "nfl"] },
  { option: "NFL S3", detail: "9556", pages: ["control", "nfl"] },
  { option: "NFL S4", detail: "9557", pages: ["control", "nfl"] },
  { option: "NFL S5", detail: "9558", pages: ["control", "nfl"] },
  { option: "NFL S6", detail: "9559", pages: ["control", "nfl"] },
  { option: "NFL S7", detail: "9560", pages: ["control", "nfl"] },
  { option: "NFL S8", detail: "9561", pages: ["control", "nfl"] },
  { option: "NFL S9", detail: "9562", pages: ["control", "nfl"] },
];

function tvRange(start, end) {
  const tvs = [];
  for (let tv = start; tv <= end; tv += 1) tvs.push(tv);
  return tvs;
}

// Same groups Apply sends (numeric blocks, not the Sports Routing stripe).
const PRESET_GROUPS = {
  ALL: [tvRange(1, 35)],
  "4 Programs": [tvRange(1, 9), tvRange(10, 18), tvRange(19, 27), tvRange(28, 35)],
  "9 Programs": [
    tvRange(1, 4),
    tvRange(5, 8),
    tvRange(9, 12),
    tvRange(13, 16),
    tvRange(17, 20),
    tvRange(21, 24),
    tvRange(25, 28),
    tvRange(29, 32),
    tvRange(33, 35),
  ],
};

function programLetter(tv, preset) {
  const groups = PRESET_GROUPS[preset];
  if (!groups) return "";
  const index = groups.findIndex((group) => group.includes(tv));
  return index < 0 ? "" : String.fromCharCode(65 + index);
}

const PRESETS = [
  { option: "ALL", detail: "TVs 1–35 on Program A" },
  { option: "4 Programs", detail: "TVs 1–9, 10–18, 19–27, 28–35" },
  { option: "9 Programs", detail: "Blocks of four, Programs A–I" },
];

const PAGES = [
  { id: "control", title: "Control" },
  { id: "nfl", title: "NFL" },
  { id: "favorites", title: "Favorites" },
];

const ACTIONS = [
  { action: "tune", name: "Tune Selected Program", detail: "Changes the DirecTV box only" },
  { action: "route", name: "Route Program → TVs", detail: "Points the TVs at that box" },
  { action: "apply", name: "Apply Preset", detail: "Sends the letters on the TV grid" },
];

function escapeHtml(value) {
  return String(value ?? "")
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function keyButton(name, detail, action, value, on) {
  const extra = value == null ? "" : ` data-value="${escapeHtml(value)}"`;
  return `
    <button type="button" class="key${on ? " on" : ""}" data-action="${escapeHtml(action)}"${extra}>
      <span class="key-copy">
        <b>${escapeHtml(name)}</b>
        ${detail ? `<small>${escapeHtml(detail)}</small>` : ""}
      </span>
    </button>
  `;
}

class PanelMatrix extends HTMLElement {
  constructor() {
    super();
    this._hass = null;
    this._page = "control";
    this._status = "";
    this._statusError = false;
    this._busy = false;
    this._picked = null;
    this._signature = "";
    this.attachShadow({ mode: "open" });
  }

  set panel(_config) {
    this._render();
  }

  set hass(hass) {
    this._hass = hass;
    if (this.shadowRoot?.activeElement?.tagName === "INPUT") return;
    this._render();
  }

  connectedCallback() {
    if (!this._clickBound) {
      this.shadowRoot.addEventListener("click", (event) => this._onClick(event));
      this._clickBound = true;
    }
    this._render();
  }

  _entityState(entityId) {
    const state = this._hass?.states?.[entityId]?.state;
    if (!state || state === "unknown" || state === "unavailable") return "";
    return state;
  }

  async _call(domain, service, data, done) {
    if (this._busy) return;
    if (typeof this._hass?.callService !== "function") {
      this._status = "Home Assistant is not connected.";
      this._statusError = true;
      this._render();
      return;
    }
    this._busy = true;
    this._signature = "";
    try {
      await this._hass.callService(domain, service, data || {});
      this._status = done || "";
      this._statusError = false;
    } catch (error) {
      this._status = error?.message || "That action failed.";
      this._statusError = true;
    } finally {
      this._busy = false;
      this._signature = "";
      this._render();
    }
  }

  _onClick(event) {
    const button = event.target.closest("[data-action]");
    if (!button || button.disabled) return;
    const action = button.dataset.action;
    const value = button.dataset.value;
    if (action === "page") {
      this._page = value || "control";
      this._signature = "";
      this._render();
      return;
    }
    if (action === "preset") {
      this._call("input_select", "select_option", {
        entity_id: "input_select.avaccess_active_preset",
        option: value,
      });
      return;
    }
    if (action === "program") {
      this._call("script", "avaccess_set_program", { program: value });
      return;
    }
    if (action === "channel") {
      this._call("input_select", "select_option", {
        entity_id: "input_select.avaccess_channel",
        option: value,
      });
      return;
    }
    if (action === "tune") {
      this._status = "Sending tune…";
      this._statusError = false;
      this._signature = "";
      const program = this._entityState("input_select.avaccess_program") || "Program A";
      const channel = this._entityState("input_select.avaccess_channel") || "ESPN";
      this._call(
        "script",
        "avaccess_tune_selected_channel",
        {},
        `Tuned ${channel} on ${program}.`,
      );
      return;
    }
    if (action === "route") {
      if (!this._currentTvs().length) {
        this._status = "Pick at least one TV.";
        this._statusError = true;
        this._render();
        return;
      }
      this._call("script", "avaccess_route_selected_program_to_tvs", {});
      return;
    }
    if (action === "apply") {
      const preset = this._entityState("input_select.avaccess_active_preset");
      if (!preset || preset === "None") {
        this._status = "Pick a display first.";
        this._statusError = true;
        this._signature = "";
        this._render();
        return;
      }
      this._call("script", "avaccess_apply_selected_preset", {}, `Sent ${preset} to the wall.`);
      return;
    }
    if (action === "toggle-tv") {
      const tv = Number(value);
      if (!tv) return;
      const current = this._currentTvs();
      const next = current.includes(tv) ? current.filter((item) => item !== tv) : [...current, tv].sort((a, b) => a - b);
      this._writeTvs(next);
      return;
    }
    if (action === "clear-tvs") {
      this._writeTvs([]);
    }
  }

  _tvsFromState() {
    const raw = this._entityState("input_text.avaccess_target_rxs");
    const nums = [];
    for (const part of raw.split(/[\s,]+/)) {
      const match = /^RX-(\d+)$/i.exec(part);
      if (!match) continue;
      const tv = Number(match[1]);
      if (tv >= 1 && tv <= 35 && !nums.includes(tv)) nums.push(tv);
    }
    return nums.sort((a, b) => a - b);
  }

  _currentTvs() {
    if (Array.isArray(this._picked)) return this._picked;
    return this._tvsFromState();
  }

  _writeTvs(tvs) {
    this._picked = tvs;
    this._signature = "";
    this._render();
    const value = tvs.map((tv) => `RX-${String(tv).padStart(2, "0")}`).join(", ");
    this._call("input_text", "set_value", {
      entity_id: "input_text.avaccess_target_rxs",
      value,
    });
  }

  _render() {
    const scroller = this.shadowRoot.querySelector(".bank");
    const scrollTop = scroller ? scroller.scrollTop : 0;
    const program = this._entityState("input_select.avaccess_program") || "Program A";
    const channel = this._entityState("input_select.avaccess_channel") || "ESPN";
    const preset = this._entityState("input_select.avaccess_active_preset");
    const picked = this._currentTvs();
    if (this._picked && this._picked.join() === this._tvsFromState().join()) this._picked = null;
    const pageChannels = CHANNELS.filter((item) => item.pages.includes(this._page));
    const showPrograms = this._page === "control";
    const showPresets = this._page === "control";

    const chips = PAGES.map(
      (page) =>
        `<button type="button" class="chip${page.id === this._page ? " on" : ""}" data-action="page" data-value="${page.id}">${escapeHtml(page.title)}</button>`,
    ).join("");

    const actions = ACTIONS.map((item) => keyButton(item.name, item.detail, item.action, null, false)).join("");
    const presets = PRESETS.map((item) =>
      keyButton(item.option, item.detail, "preset", item.option, preset === item.option),
    ).join("");
    const programs = PROGRAMS.map((item) =>
      keyButton(item.name, item.detail, "program", item.key, program === item.name),
    ).join("");
    const channels = pageChannels
      .map((item) => keyButton(item.option, item.detail, "channel", item.option, channel === item.option))
      .join("");

    const status = this._status
      ? `<p class="status${this._statusError ? " error" : ""}" role="status">${escapeHtml(this._status)}</p>`
      : `<p class="status" role="status">${escapeHtml(program)} · ${escapeHtml(channel)}</p>`;

    const signature = [this._page, program, channel, preset, picked.join(","), this._status, this._statusError].join("|");
    if (signature === this._signature && this.shadowRoot.querySelector(".bank")) return;
    this._signature = signature;

    this.shadowRoot.innerHTML = `
      <style>
        :host { display: block; }
        .routing {
          background: #101010;
          box-sizing: border-box;
          color: #f3f3f3;
          display: flex;
          flex-direction: column;
          font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", sans-serif;
          height: calc(100dvh - 64px);
          max-height: calc(100dvh - 64px);
          min-height: 0;
        }
        .routing-top {
          align-items: baseline;
          display: flex;
          gap: 16px;
          justify-content: space-between;
          padding: 22px 28px 8px;
        }
        .room { font-size: 22px; font-weight: 650; letter-spacing: -0.02em; }
        .status { color: #c8c8c8; font-size: 16px; margin: 0; text-align: right; }
        .status.error { color: #f0a8a8; }
        .chips { display: flex; gap: 8px; padding: 0 28px 12px; }
        .chip {
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #c8c8c8;
          cursor: pointer;
          font: inherit;
          font-size: 14px;
          padding: 8px 14px;
        }
        .chip.on { background: #0b5cab; color: #f3f3f3; }
        .bank {
          flex: 1 1 auto;
          min-height: 0;
          overflow: auto;
          padding: 4px 28px 28px;
        }
        h2 {
          color: #8d8d8d;
          font-size: 14px;
          font-weight: 500;
          margin: 16px 0 10px;
        }
        .keys { display: flex; flex-direction: column; gap: 8px; }
        .keys.grid { display: grid; gap: 8px; grid-template-columns: 1fr 1fr; }
        .key {
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
        .key.on { background: linear-gradient(#1470d4, #0b5cab); }
        .key-copy { min-width: 0; }
        .key-copy b { display: block; font-size: 17px; font-weight: 650; }
        .key-copy small {
          color: #bdbdbd;
          display: block;
          font-size: 13px;
          margin-top: 2px;
          overflow: hidden;
          text-overflow: ellipsis;
          white-space: nowrap;
        }
        .key.on small { color: #d7e7f8; }
        .tv-toolbar {
          align-items: center;
          color: #8d8d8d;
          display: flex;
          font-size: 14px;
          justify-content: space-between;
          margin-bottom: 8px;
        }
        .tv-toolbar button {
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #f3f3f3;
          cursor: pointer;
          font: inherit;
          padding: 8px 12px;
        }
        .tv-grid {
          display: grid;
          gap: 8px;
          grid-template-columns: repeat(7, minmax(0, 1fr));
        }
        .tv {
          align-items: center;
          background: #2a2a2a;
          border: 0;
          border-radius: 3px;
          color: #f3f3f3;
          cursor: pointer;
          display: flex;
          flex-direction: column;
          font: inherit;
          font-size: 16px;
          font-weight: 650;
          height: 52px;
          justify-content: center;
          line-height: 1.05;
        }
        .tv small {
          color: #bdbdbd;
          font-size: 11px;
          font-weight: 650;
        }
        .tv.is-selected { background: #0b5cab; color: #ffffff; }
        .tv.is-selected small { color: #d7e7f8; }
        @media (max-width: 720px) {
          .keys.grid { grid-template-columns: 1fr; }
          .routing-top, .chips, .bank { padding-left: 16px; padding-right: 16px; }
        }
      </style>
      <section class="routing">
        <div class="routing-top">
          <div class="room">Bar</div>
          ${status}
        </div>
        <nav class="chips" aria-label="Matrix pages">${chips}</nav>
        <div class="bank">
          <h2>TVs</h2>
          <div class="tv-toolbar">
            <span>${picked.length} picked${PRESET_GROUPS[preset] ? ` · ${escapeHtml(preset)}` : ""}</span>
            <button type="button" data-action="clear-tvs">Clear TVs</button>
          </div>
          <div class="tv-grid" aria-label="TV picker">
            ${Array.from({ length: 35 }, (_, index) => {
              const tv = index + 1;
              const on = picked.includes(tv) ? " is-selected" : "";
              const letter = programLetter(tv, preset);
              const mark = letter ? `<small>${letter}</small>` : "";
              return `<button type="button" class="tv${on}" data-action="toggle-tv" data-value="${tv}">${tv}${mark}</button>`;
            }).join("")}
          </div>
          <h2>Actions</h2>
          <div class="keys">${actions}</div>
          ${
            showPresets
              ? `<h2>Displays</h2><div class="keys grid">${presets}</div>`
              : ""
          }
          <h2>Sources</h2>
          ${showPrograms ? `<div class="keys grid">${programs}</div>` : ""}
          <div class="keys grid">${channels}</div>
        </div>
      </section>
    `;
    const nextScroller = this.shadowRoot.querySelector(".bank");
    if (nextScroller) nextScroller.scrollTop = scrollTop;
  }
}

if (!customElements.get("panel-matrix")) {
  customElements.define("panel-matrix", PanelMatrix);
}
