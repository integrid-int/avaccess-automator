import test from "node:test";
import assert from "node:assert/strict";

const registry = new Map();
globalThis.HTMLElement ??= class {
  addEventListener() {}
  removeEventListener() {}
};
globalThis.document ??= { activeElement: null };
globalThis.customElements ??= {
  get: (name) => registry.get(name),
  define: (name, cls) => registry.set(name, cls),
};

await import("../../homeassistant/config/www/panels/panel-health.js");
const PanelHealth = customElements.get("panel-health");

const ENTITY = "input_boolean.avaccess_live_commit";

function hassWith(state, calls = []) {
  return {
    states: { [ENTITY]: { entity_id: ENTITY, state } },
    callService: async (...args) => {
      calls.push(args);
    },
  };
}

function readyPanel() {
  const panel = new PanelHealth();
  panel._inventoryLoaded = true;
  panel._inventoryLiveReady = true;
  return panel;
}

test("panel resyncs Live commit from the HA boolean on every hass update", () => {
  const panel = readyPanel();
  panel.hass = hassWith("on");
  assert.equal(panel._state.liveCommit, true);
  panel.hass = hassWith("off");
  assert.equal(panel._state.liveCommit, false);
  panel.hass = hassWith("on");
  assert.equal(panel._state.liveCommit, true);
});

test("panel never arms Live when inventory is not ready, even if the boolean is on", () => {
  const panel = readyPanel();
  panel._inventoryLiveReady = false;
  panel.hass = hassWith("on");
  assert.equal(panel._state.liveCommit, false);
});

test("Live commit toggle writes input_boolean and does not flip local state", async () => {
  const panel = readyPanel();
  const calls = [];
  panel.hass = hassWith("off", calls);
  await panel._toggleLiveCommit();
  assert.deepEqual(calls, [["input_boolean", "turn_on", { entity_id: ENTITY }]]);
  assert.equal(panel._state.liveCommit, false, "UI waits for HA to report the boolean on");

  panel.hass = hassWith("on", calls);
  assert.equal(panel._state.liveCommit, true);
  await panel._toggleLiveCommit();
  assert.deepEqual(calls.at(-1), ["input_boolean", "turn_off", { entity_id: ENTITY }]);
});

test("Live commit toggle failure surfaces an error and leaves Live off", async () => {
  const panel = readyPanel();
  panel.hass = {
    states: { [ENTITY]: { state: "off" } },
    callService: async () => {
      throw new Error("unauthorized");
    },
  };
  await panel._toggleLiveCommit();
  assert.equal(panel._state.liveCommit, false);
  assert.match(panel._liveCommitError, /Could not change Live commit/);
});

test("Live Take calls the gated script, not the raw shell_command", async () => {
  const panel = readyPanel();
  const calls = [];
  panel.hass = hassWith("on", calls);
  panel.sportsStatus = "ok";
  panel._state = {
    ...panel._state,
    destMode: "tvs",
    selectedTvs: [1],
    selectedContent: { kind: "channel", id: "ch-206", number: "206", name: "ESPN" },
  };
  await panel._sendPlan();
  const live = calls.find((args) => args[0] === "script");
  assert.ok(live, `expected a script call, got ${JSON.stringify(calls.map((c) => c.slice(0, 2)))}`);
  assert.equal(live[1], "avaccess_live_execute");
  assert.equal(typeof live[2].plan_b64, "string");
  assert.equal(live[5], true);
  assert.ok(!calls.some((args) => args[0] === "shell_command"));
});
