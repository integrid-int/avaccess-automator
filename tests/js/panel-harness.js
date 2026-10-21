// Minimal DOM stand-ins so the real <panel-health> element can be built,
// rendered to an HTML string, and driven through _sendPlan under node --test.
import assert from "node:assert/strict";
import { LIVE_COMMIT_ENTITY } from "../../homeassistant/config/www/panels/live-execute.js";
import { STORAGE_KEY } from "../../homeassistant/config/www/panels/panel-data.js";

const registry = new Map();

class FakeElement {
  constructor() {
    this.isConnected = false;
    this._html = "";
  }
  addEventListener() {}
  removeEventListener() {}
  get innerHTML() {
    return this._html;
  }
  set innerHTML(html) {
    this._html = html;
  }
  get firstElementChild() {
    return this._html ? {} : null;
  }
  querySelector() {
    return null;
  }
  querySelectorAll() {
    return [];
  }
}

export class MemoryStorage {
  constructor() {
    this.items = new Map();
    this.writes = [];
  }
  getItem(key) {
    return this.items.has(key) ? this.items.get(key) : null;
  }
  setItem(key, value) {
    this.writes.push(key);
    this.items.set(key, String(value));
  }
  removeItem(key) {
    this.items.delete(key);
  }
  savedAssignments() {
    const raw = this.getItem(STORAGE_KEY);
    return raw ? JSON.parse(raw) : null;
  }
}

globalThis.HTMLElement ??= FakeElement;
globalThis.document ??= { activeElement: null };
globalThis.customElements ??= {
  get: (name) => registry.get(name),
  define: (name, cls) => registry.set(name, cls),
};
export const storage = new MemoryStorage();
Object.defineProperty(globalThis, "localStorage", {
  configurable: true,
  get: () => storage,
});

await import("../../homeassistant/config/www/panels/panel-health.js");
export const PanelHealth = customElements.get("panel-health");

export function resetStorage() {
  storage.items.clear();
  storage.writes.length = 0;
}

/**
 * A connected panel with a Live-ready inventory, a fresh real sports schedule,
 * and HA reporting the Live commit boolean as `liveState`.
 */
export function makePanel({ liveState = "on", callService = async () => undefined } = {}) {
  const panel = new PanelHealth();
  panel.isConnected = true;
  panel._tvSets = [];
  panel._inventoryLoaded = true;
  panel._inventoryLiveReady = true;
  panel.sportsStatus = "ok";
  panel.sportsGeneratedAt = new Date().toISOString();
  const calls = [];
  panel.hass = {
    states: { [LIVE_COMMIT_ENTITY]: { entity_id: LIVE_COMMIT_ENTITY, state: liveState } },
    callService: async (...args) => {
      calls.push(args);
      return callService(...args);
    },
  };
  return { panel, calls };
}

export function scriptCalls(calls) {
  return calls.filter((args) => args[0] === "script");
}

export function decodePlanB64(planB64) {
  return JSON.parse(Buffer.from(planB64, "base64").toString("utf8"));
}

export function scriptReport(returncode, report) {
  return { response: { returncode, stdout: JSON.stringify(report), stderr: "" } };
}

export function channel(number, name) {
  return { kind: "channel", id: `ch-${number}`, number, name };
}

export function game(id, { away = "Away", home = "Home", channelNumber = "206" } = {}) {
  return { kind: "game", id, away, home, channel: "FOX", channelNumber, sportId: "nfl" };
}

/** Pick TVs and one source the way a TV-first Take does. */
export function selectAdhoc(panel, content, tvs) {
  panel._state = {
    ...panel._state,
    destMode: "tvs",
    groupMode: "adhoc",
    selectedTvs: tvs,
    selectedContent: content,
    selectedPrograms: [],
  };
}

export function selectPreset(panel, mode, programs) {
  panel._state = {
    ...panel._state,
    destMode: "presets",
    groupMode: mode,
    selectedTvs: [],
    selectedContent: null,
    selectedPrograms: programs,
  };
}

/** assert.match without dumping ~30 KB of rendered CSS on failure. */
export function assertRendered(panel, pattern, { present = true } = {}) {
  const found = pattern.test(panel.innerHTML);
  assert.equal(found, present, `rendered panel ${present ? "should" : "should not"} match ${pattern}`);
}

/** The rendered Take button: { tag, label, disabled, busy }. */
export function takeButton(panel) {
  const match = panel.innerHTML.match(/<button([^>]*data-action="send-destination"[^>]*)>([^<]*)</);
  assert.ok(match, "Take button should render");
  const [, attrs, label] = match;
  return {
    label: label.trim(),
    disabled: /\sdisabled(\s|$)/.test(attrs),
    busy: /aria-busy="true"/.test(attrs),
  };
}

export function renderedHeader(panel) {
  panel.render();
  const header = panel.innerHTML.match(/<header class="routing-top">[\s\S]*?<\/header>/);
  return header ? header[0] : "";
}
