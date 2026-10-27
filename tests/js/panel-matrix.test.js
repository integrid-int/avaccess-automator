// Matrix tune status: a thrown service call stays an error, a finished tune
// names the labels already selected and does not claim the receiver confirmed it.
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import test from "node:test";

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
  attachShadow() {
    this.shadowRoot = this;
    return this;
  }
}

globalThis.HTMLElement ??= FakeElement;
globalThis.document ??= { activeElement: null };
globalThis.customElements ??= {
  get: (name) => registry.get(name),
  define: (name, cls) => registry.set(name, cls),
};

await import("../../homeassistant/config/www/panels/panel-matrix.js");
const PanelMatrix = customElements.get("panel-matrix");

function makePanel(callService, states) {
  const panel = new PanelMatrix();
  panel.isConnected = true;
  panel.hass = { states, callService };
  return panel;
}

const selected = {
  "input_select.avaccess_program": { state: "Program I" },
  "input_select.avaccess_channel": { state: "NFL S9" },
};

test("a failed tune keeps the service error on the status line", async () => {
  const panel = makePanel(async () => {
    throw new Error("Channel does not exist.");
  }, selected);
  await panel._call("script", "avaccess_tune_selected_channel", {}, "Tuned NFL S9 on Program I.");
  assert.equal(panel._status, "Channel does not exist.");
  assert.equal(panel._statusError, true);
  assert.match(panel.shadowRoot.innerHTML, /class="status error"/);
  assert.match(panel.shadowRoot.innerHTML, /Channel does not exist\./);
  assert.doesNotMatch(panel._status, /confirm/i);
});

test("a successful tune names the selected channel and program", async () => {
  const calls = [];
  const panel = makePanel(async (...args) => {
    calls.push(args);
  }, {
    "input_select.avaccess_program": { state: "Program A" },
    "input_select.avaccess_channel": { state: "ESPN" },
  });
  panel._onClick({
    target: {
      closest() {
        return { disabled: false, dataset: { action: "tune" } };
      },
    },
  });
  await new Promise((resolve) => setTimeout(resolve, 0));
  assert.deepEqual(calls, [["script", "avaccess_tune_selected_channel", {}]]);
  assert.equal(panel._status, "Tuned ESPN on Program A.");
  assert.equal(panel._statusError, false);
  assert.doesNotMatch(panel._status, /confirm/i);
  assert.doesNotMatch(panel._status, /Now Playing/i);
});

test("Sunday Ticket details are 9554-9562 and afternoon stays 705-708", () => {
  const src = readFileSync(
    new URL("../../homeassistant/config/www/panels/panel-matrix.js", import.meta.url),
    "utf8",
  );
  assert.match(src, /option: "NFL S1", detail: "9554"/);
  assert.match(src, /option: "NFL S9", detail: "9562"/);
  assert.match(src, /option: "NFL A1", detail: "705"/);
  assert.match(src, /option: "NFL A4", detail: "708"/);
  assert.doesNotMatch(src, /option: "NFL S9", detail: "713"/);
});
