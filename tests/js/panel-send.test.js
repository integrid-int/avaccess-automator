import test from "node:test";
import assert from "node:assert/strict";
import { applyRoutePlan, createEmptyAssignments } from "../../homeassistant/config/www/panels/assignment-store.js";
import { LIVE_COMMIT_ENTITY } from "../../homeassistant/config/www/panels/live-execute.js";
import { PRACTICE_STORAGE_KEY, STORAGE_KEY } from "../../homeassistant/config/www/panels/panel-data.js";
import { buildRoutePlan, stripedTvs } from "../../homeassistant/config/www/panels/route-planner.js";
import {
  assertRendered,
  channel,
  decodePlanB64,
  game,
  makePanel,
  renderedHeader,
  resetStorage,
  scriptCalls,
  scriptReport,
  selectAdhoc,
  selectPreset,
  setLiveState,
  storage,
  takeButton,
} from "./panel-harness.js";

function program(id, channelNumber) {
  return { kind: "game", id, label: `Game ${id}`, channel: "FOX", channelNumber };
}

function okFor(...encoderIds) {
  return scriptReport(0, { ok: true, slots: encoderIds.map((encoderId) => ({ encoderId, status: "ok" })) });
}

async function okForEverySlot(domain, _service, data) {
  if (domain !== "script") return undefined;
  return okFor(...decodePlanB64(data.plan_b64).slots.map((slot) => slot.encoderId));
}

test("Live Take saves only slots the server reported ok, and only after the script returns", async () => {
  resetStorage();
  let savedDuringCall = "not called";
  const { panel, calls } = makePanel({
    callService: async (domain) => {
      if (domain !== "script") return undefined;
      savedDuringCall = storage.savedAssignments();
      return scriptReport(1, {
        ok: false,
        slots: [
          { encoderId: "ENC-01", status: "error", error: "SHEF failed" },
          { encoderId: "ENC-02", status: "ok" },
        ],
        errors: ["SHEF failed"],
      });
    },
  });
  selectPreset(panel, "preset_2", [program("g1", "206"), program("g2", "212")]);

  await panel._sendPlan();

  assert.equal(scriptCalls(calls).length, 1);
  assert.equal(savedDuringCall, null, "occupancy must not be written before Home Assistant answers");
  assert.equal(panel._assignments["ENC-01"], undefined);
  assert.deepEqual(panel._assignments["ENC-02"].tvs, stripedTvs(4, 2));
  assert.deepEqual(Object.keys(storage.savedAssignments()), ["ENC-02"]);
  assert.equal(panel._state.lastPlan.error, "SHEF failed");
  assertRendered(panel, /Live summary/);
  assertRendered(panel, /<p class="plan-error">SHEF failed<\/p>/);
  assertRendered(panel, /error: SHEF failed/);
});

test("Live Take with no report from Home Assistant saves nothing and shows an error", async () => {
  resetStorage();
  const { panel, calls } = makePanel({ callService: async () => ({ context: { id: "abc" } }) });
  selectAdhoc(panel, channel("206", "ESPN"), [1, 2]);

  await panel._sendPlan();

  assert.equal(scriptCalls(calls).length, 1);
  assert.deepEqual(panel._assignments, createEmptyAssignments());
  assert.deepEqual(storage.writes, []);
  assert.match(panel._state.lastPlan.error, /no report/i);
  assert.ok(panel._state.lastPlan.slots.every((slot) => slot.status === "error"));
  assertRendered(panel, /class="plan-error">Live execute failed/);
});

test("a second Take while Live is in flight sends nothing and the button shows Sending…", async () => {
  resetStorage();
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const { panel, calls } = makePanel({
    callService: async (domain) => {
      if (domain !== "script") return undefined;
      await gate;
      return okFor("ENC-01");
    },
  });
  selectAdhoc(panel, channel("206", "ESPN"), [1, 2]);

  const first = panel._sendPlan();
  assert.equal(scriptCalls(calls).length, 1);
  panel.render();
  assert.deepEqual(takeButton(panel), { label: "Sending…", disabled: true, busy: true });

  panel._sendDestination();
  panel._sendTvFirst();
  const again = panel._sendPlan();
  const sentWhileBusy = scriptCalls(calls).length;
  release();
  await Promise.all([first, again]);
  assert.equal(sentWhileBusy, 1, "double tap must not start a second Live send");
  assert.equal(scriptCalls(calls).length, 1);
  assert.equal(panel._sending, false);
  assert.deepEqual(panel._assignments["ENC-01"].tvs, [1, 2]);
  assert.equal(takeButton(panel).busy, false);
  assertRendered(panel, /Sending…/, { present: false });
});

test("Live Take of a game with no DirecTV channel never reaches Home Assistant", async () => {
  resetStorage();
  const { panel, calls } = makePanel();
  selectAdhoc(panel, game("g-open", { away: "Yankees", home: "Red Sox", channelNumber: null }), [1]);

  await panel._sendPlan();

  assert.deepEqual(calls, []);
  assert.match(panel._state.lastPlan.error, /Yankees @ Red Sox has no DirecTV channel/);
  assert.deepEqual(panel._assignments, createEmptyAssignments());
  assert.deepEqual(storage.writes, []);
  assertRendered(panel, /class="plan-error">Cannot Take: Yankees @ Red Sox has no DirecTV channel/);
});

test("demo sports fallback blocks Live Take but still allows a PRACTICE Take", async () => {
  resetStorage();
  const live = makePanel();
  live.panel.sportsStatus = "fallback";
  selectAdhoc(live.panel, game("g1", { channelNumber: "206" }), [1]);
  await live.panel._sendPlan();
  assert.deepEqual(live.calls, []);
  assert.match(live.panel._state.lastPlan.error, /Live Take blocked/i);
  assert.deepEqual(storage.writes, []);

  const practice = makePanel({ liveState: "off" });
  practice.panel.sportsStatus = "fallback";
  selectAdhoc(practice.panel, game("g1", { channelNumber: "206" }), [1]);
  await practice.panel._sendPlan();
  assert.deepEqual(practice.calls, []);
  assert.equal(practice.panel._state.lastPlan.error, undefined);
  assert.equal(practice.panel._state.lastPlan.practice, true);
  assertRendered(practice.panel, /PRACTICE summary/);
});

test("Take re-reads the HA boolean: switched off after arming, it runs PRACTICE and calls nothing", async () => {
  resetStorage();
  const { panel, calls } = makePanel({ liveState: "on" });
  assert.equal(panel._state.liveCommit, true);
  panel.hass.states[LIVE_COMMIT_ENTITY].state = "off";
  selectAdhoc(panel, channel("206", "ESPN"), [1]);

  await panel._sendPlan();

  assert.deepEqual(calls, []);
  assert.equal(panel._state.liveCommit, false);
  assert.equal(panel._state.lastPlan.commit, "dry_run");
  assert.equal(panel._state.lastPlan.practice, true);
  assert.match(renderedHeader(panel), /data-commit-mode="practice"/);
});

test("patio Take after All 35 claims a free encoder instead of retuning the whole bar", async () => {
  resetStorage();
  const { panel, calls } = makePanel({
    callService: async (domain) => (domain === "script" ? okFor("ENC-02") : undefined),
  });
  const all35 = buildRoutePlan({
    mode: "preset_1",
    programs: [program("g-all", "206")],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  panel._assignments = applyRoutePlan(createEmptyAssignments(), all35);
  selectAdhoc(panel, channel("212", "NFL"), [8, 9, 10]);

  await panel._sendPlan();

  const sent = scriptCalls(calls);
  assert.equal(sent.length, 1, "no reuse Confirm step when a free encoder exists");
  const plan = decodePlanB64(sent[0][2].plan_b64);
  assert.deepEqual(
    plan.slots.map((slot) => [slot.encoderId, slot.tvs]),
    [["ENC-02", [8, 9, 10]]]
  );
  assert.equal(plan.replaced ?? null, null);
  assert.deepEqual(panel._assignments["ENC-02"].tvs, [8, 9, 10]);
  assert.equal(panel._assignments["ENC-01"].tvs.length, 32);
  assert.ok(!panel._assignments["ENC-01"].tvs.includes(8));
});

function busyRoom() {
  const assignments = {
    "ENC-03": { encoderId: "ENC-03", label: "49ers @ Falcons", channel: "9558", tvs: [1, 2, 3, 4, 5, 6] },
  };
  const rest = [7, 8, 9, 10, 11, 12, 13, 14, 15];
  let n = 0;
  for (let i = 1; i <= 10; i += 1) {
    if (i === 3) continue;
    const encoderId = `ENC-${String(i).padStart(2, "0")}`;
    assignments[encoderId] = { encoderId, label: `Program ${i}`, channel: String(200 + i), tvs: [rest[n]] };
    n += 1;
  }
  return assignments;
}

test("reusing a shared box with no free encoders needs Confirm before Live is sent", async () => {
  resetStorage();
  const { panel, calls } = makePanel({
    callService: async (domain) => (domain === "script" ? okFor("ENC-03") : undefined),
  });
  panel._assignments = busyRoom();
  selectAdhoc(panel, channel("612", "ESPN2"), [1, 3, 5]);

  await panel._sendPlan();
  assert.deepEqual(calls, [], "first Take only asks for Confirm");
  assert.equal(panel._state.reuseConfirmKey, "ENC-03:2,4,6");
  assertRendered(panel, /3 TVs will keep showing the retuned program until reassigned\. Tap Confirm to continue\./);
  assert.deepEqual(takeButton(panel), { label: "Confirm", disabled: false, busy: false });

  await panel._sendPlan();
  const sent = scriptCalls(calls);
  assert.equal(sent.length, 1);
  const plan = decodePlanB64(sent[0][2].plan_b64);
  assert.deepEqual(plan.slots.map((slot) => [slot.encoderId, slot.tvs]), [["ENC-03", [1, 3, 5]]]);
  assert.deepEqual(plan.replaced.offTvs, [2, 4, 6]);
  assert.equal(panel._state.reuseConfirmKey, null);
});

test("a PRACTICE Take writes only the practice occupancy store, never the Live key", async () => {
  resetStorage();
  const { panel, calls } = makePanel({ liveState: "off" });
  selectAdhoc(panel, channel("206", "ESPN"), [1, 2]);

  await panel._sendPlan();

  assert.deepEqual(calls, []);
  assert.equal(panel._state.lastPlan.practice, true);
  assert.equal(storage.getItem(STORAGE_KEY), null);
  assert.ok(!storage.writes.includes(STORAGE_KEY), "practice must not write the Live key");
  assert.deepEqual(storage.writes, [PRACTICE_STORAGE_KEY]);
  assert.deepEqual(storage.savedPracticeAssignments()["ENC-01"].tvs, [1, 2]);
  assert.deepEqual(panel._assignments["ENC-01"].tvs, [1, 2]);
});

test("Live Take after PRACTICE Takes sees only Live occupancy: claims ENC-01 with no Confirm", async () => {
  resetStorage();
  const { panel, calls } = makePanel({ liveState: "off", callService: okForEverySlot });
  selectPreset(panel, "preset_1", [program("g-all", "206")]);
  await panel._sendPlan();
  selectAdhoc(panel, channel("212", "NFL"), [8, 9, 10]);
  await panel._sendPlan();
  assert.deepEqual(calls, []);
  const practiceAfter = storage.getItem(PRACTICE_STORAGE_KEY);
  assert.deepEqual(Object.keys(JSON.parse(practiceAfter)).sort(), ["ENC-01", "ENC-02"]);

  setLiveState(panel, "on");
  assert.equal(panel._state.liveCommit, true);
  assert.deepEqual(panel._assignments, createEmptyAssignments(), "switching to Live loads the Live store, not a merge");

  selectAdhoc(panel, channel("612", "ESPN2"), [1, 3, 5]);
  await panel._sendPlan();

  const sent = scriptCalls(calls);
  assert.equal(sent.length, 1, "practice routes must not trigger a reuse Confirm");
  const plan = decodePlanB64(sent[0][2].plan_b64);
  assert.deepEqual(plan.slots.map((slot) => [slot.encoderId, slot.tvs]), [["ENC-01", [1, 3, 5]]]);
  assert.equal(plan.replaced ?? null, null);
  assert.deepEqual(Object.keys(storage.savedAssignments()), ["ENC-01"]);
  assert.deepEqual(storage.savedAssignments()["ENC-01"].tvs, [1, 3, 5]);
  assert.equal(storage.getItem(PRACTICE_STORAGE_KEY), practiceAfter);
});

test("a full PRACTICE room asks for Confirm in PRACTICE but not once Live is on", async () => {
  resetStorage();
  storage.setItem(PRACTICE_STORAGE_KEY, JSON.stringify(busyRoom()));
  storage.writes.length = 0;
  const { panel, calls } = makePanel({ liveState: "off", callService: okForEverySlot });

  selectAdhoc(panel, channel("612", "ESPN2"), [1, 3, 5]);
  await panel._sendPlan();
  assert.equal(panel._state.reuseConfirmKey, "ENC-03:2,4,6", "practice occupancy is still used in PRACTICE");
  assert.deepEqual(takeButton(panel).label, "Confirm");

  setLiveState(panel, "on");
  assert.equal(panel._state.reuseConfirmKey, null, "a Confirm from PRACTICE does not carry into Live");
  selectAdhoc(panel, channel("612", "ESPN2"), [1, 3, 5]);
  await panel._sendPlan();

  const sent = scriptCalls(calls);
  assert.equal(sent.length, 1);
  assert.deepEqual(
    decodePlanB64(sent[0][2].plan_b64).slots.map((slot) => [slot.encoderId, slot.tvs]),
    [["ENC-01", [1, 3, 5]]]
  );
  assert.ok(!storage.writes.includes(PRACTICE_STORAGE_KEY));
});

test("a PRACTICE Take after a Live Take leaves Live occupancy untouched", async () => {
  resetStorage();
  const { panel, calls } = makePanel({ liveState: "on", callService: okForEverySlot });
  selectAdhoc(panel, channel("206", "ESPN"), [1, 2]);
  await panel._sendPlan();
  assert.equal(scriptCalls(calls).length, 1);
  const liveAfter = storage.getItem(STORAGE_KEY);
  assert.deepEqual(JSON.parse(liveAfter)["ENC-01"].tvs, [1, 2]);

  setLiveState(panel, "off");
  assert.deepEqual(panel._assignments, createEmptyAssignments());
  selectAdhoc(panel, channel("212", "NFL"), [1, 2, 3]);
  await panel._sendPlan();

  assert.equal(scriptCalls(calls).length, 1, "PRACTICE calls nothing");
  assert.equal(storage.getItem(STORAGE_KEY), liveAfter);
  assert.equal(storage.savedPracticeAssignments()["ENC-01"].channel, "212");
  assert.deepEqual(storage.savedPracticeAssignments()["ENC-01"].tvs, [1, 2, 3]);

  setLiveState(panel, "on");
  assert.deepEqual(panel._assignments, JSON.parse(liveAfter), "back in Live, the panel reloads the Live store");
});

test("a Live send that finishes after Live is turned off saves to the Live store only", async () => {
  resetStorage();
  let release;
  const gate = new Promise((resolve) => {
    release = resolve;
  });
  const { panel } = makePanel({
    liveState: "on",
    callService: async (...args) => {
      await gate;
      return okForEverySlot(...args);
    },
  });
  selectAdhoc(panel, channel("206", "ESPN"), [4, 5]);
  const pending = panel._sendPlan();
  setLiveState(panel, "off");
  release();
  await pending;

  assert.deepEqual(storage.savedAssignments()["ENC-01"].tvs, [4, 5]);
  assert.equal(storage.getItem(PRACTICE_STORAGE_KEY), null);
  assert.deepEqual(panel._assignments, createEmptyAssignments(), "the panel stays on the PRACTICE store");
});

test("Clear room state removes both the Live and the practice occupancy keys", async () => {
  resetStorage();
  const { panel } = makePanel({ liveState: "on", callService: okForEverySlot });
  selectAdhoc(panel, channel("206", "ESPN"), [1, 2]);
  await panel._sendPlan();
  setLiveState(panel, "off");
  selectAdhoc(panel, channel("212", "NFL"), [3, 4]);
  await panel._sendPlan();
  storage.setItem("avaccess-tv-sets-v1", JSON.stringify({ source: "tv-sets", sets: [] }));
  assert.ok(storage.getItem(STORAGE_KEY));
  assert.ok(storage.getItem(PRACTICE_STORAGE_KEY));

  panel._clearRoomState();

  assert.equal(storage.getItem(STORAGE_KEY), null);
  assert.equal(storage.getItem(PRACTICE_STORAGE_KEY), null);
  assert.ok(storage.getItem("avaccess-tv-sets-v1"), "TV sets survive Clear room state");
  assert.deepEqual(panel._assignments, createEmptyAssignments());
  setLiveState(panel, "on");
  assert.deepEqual(panel._assignments, createEmptyAssignments());
});
