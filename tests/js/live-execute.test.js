import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { applyRoutePlan, createEmptyAssignments } from "../../homeassistant/config/www/panels/assignment-store.js";
import {
  createInFlightLock,
  guardedSend,
  interpretLiveServiceResponse,
  isTakeArmed,
  liveExecuteCallServiceArgs,
  occupancyPlanFromLiveResult,
  runDryRunSend,
  runLiveSend,
  runLiveSendSafe,
} from "../../homeassistant/config/www/panels/live-execute.js";

function samplePlan(overrides = {}) {
  return {
    mode: "adhoc",
    commit: "live",
    slots: [
      {
        index: 1,
        encoderId: "ENC-01",
        program: { kind: "game", id: "g1", label: "A @ B", channel: "FOX" },
        tvs: [1, 2],
        tune: { channelNumber: "212" },
        udp: null,
        status: "planned",
      },
      {
        index: 2,
        encoderId: "ENC-02",
        program: { kind: "game", id: "g2", label: "C @ D", channel: "CBS" },
        tvs: [3, 4],
        tune: { channelNumber: "206" },
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
    ...overrides,
  };
}

function haResponse({ returncode, stdout }) {
  return { response: { returncode, stdout } };
}

test("liveExecuteCallServiceArgs requests returnResponse as the 6th HA frontend arg", () => {
  const args = liveExecuteCallServiceArgs("dGVzdA==");
  assert.equal(args.length, 6);
  assert.equal(args[0], "shell_command");
  assert.equal(args[1], "avaccess_execute_route_plan");
  assert.equal(args[2].live, true);
  assert.equal(args[2].plan_b64, "dGVzdA==");
  assert.equal(args[3], undefined);
  assert.equal(args[4], true);
  assert.equal(args[5], true);
});

test("context-only HA response is a missing report failure", () => {
  const outcome = interpretLiveServiceResponse({ context: { id: "abc" } });
  assert.equal(outcome.failed, true);
  assert.equal(outcome.missingReport, true);
  assert.equal(outcome.returncode, null);
});

test("exit 2 with empty slots sets lastPlan error and leaves occupancy unchanged", async () => {
  const assignments = createEmptyAssignments();
  const plan = samplePlan();
  const events = [];
  const result = await runLiveSend({
    plan,
    assignments,
    applyPlan: (current, nextPlan) => {
      events.push("applyPlan");
      return applyRoutePlan(current, nextPlan);
    },
    callService: async (...args) => {
      events.push("callService");
      assert.equal(args[5], true);
      return haResponse({
        returncode: 2,
        stdout: JSON.stringify({ ok: false, slots: [], errors: ["X"] }),
      });
    },
  });

  assert.deepEqual(events, ["callService"]);
  assert.equal(result.outcome.failed, true);
  assert.equal(result.lastPlan.error, "X");
  assert.ok(result.lastPlan.warnings.includes("X"));
  assert.ok(result.lastPlan.slots.length > 0);
  assert.ok(result.lastPlan.slots.every((slot) => slot.status === "error"));
  assert.deepEqual(result.assignments, assignments);
  assert.equal(Object.keys(result.assignments).length, 0);
});

test("returncode 1 occupancy contains only slots that reported ok", async () => {
  const assignments = createEmptyAssignments();
  const result = await runLiveSend({
    plan: samplePlan(),
    assignments,
    callService: async () =>
      haResponse({
        returncode: 1,
        stdout: JSON.stringify({
          ok: false,
          slots: [
            { encoderId: "ENC-01", status: "error", error: "SHEF failed" },
            { encoderId: "ENC-02", status: "ok" },
          ],
          errors: ["SHEF failed"],
        }),
      }),
  });

  assert.equal(result.outcome.failed, true);
  assert.ok(result.lastPlan.error);
  assert.equal(result.lastPlan.slots.find((slot) => slot.encoderId === "ENC-01").status, "error");
  assert.equal(result.lastPlan.slots.find((slot) => slot.encoderId === "ENC-02").status, "ok");
  assert.equal(result.assignments["ENC-01"], undefined);
  assert.ok(result.assignments["ENC-02"]);
  assert.deepEqual(result.assignments["ENC-02"].tvs, [3, 4]);
});

test("empty stdout with nonzero returncode is an error and does not save occupancy", async () => {
  const assignments = createEmptyAssignments();
  const result = await runLiveSend({
    plan: samplePlan(),
    assignments,
    callService: async () => haResponse({ returncode: 1, stdout: "" }),
  });

  assert.equal(result.outcome.failed, true);
  assert.match(result.lastPlan.error, /no report/i);
  assert.ok(result.lastPlan.warnings.some((warning) => /no report/i.test(warning)));
  assert.ok(result.lastPlan.slots.every((slot) => slot.status === "error"));
  assert.deepEqual(result.assignments, assignments);
});

test("unparsable stdout with nonzero returncode is an error banner, occupancy unchanged", async () => {
  const assignments = createEmptyAssignments();
  const result = await runLiveSend({
    plan: samplePlan(),
    assignments,
    callService: async () => haResponse({ returncode: 2, stdout: "Traceback (most recent call last):" }),
  });

  assert.equal(result.outcome.failed, true);
  assert.match(result.lastPlan.error, /no report \(exit 2\)/);
  assert.deepEqual(result.assignments, assignments);
});

test("live occupancy is applied only after callService returns ok slots", async () => {
  const assignments = createEmptyAssignments();
  const events = [];
  const result = await runLiveSend({
    plan: samplePlan(),
    assignments,
    applyPlan: (current, nextPlan) => {
      events.push("applyPlan");
      assert.ok(nextPlan.slots.every((slot) => slot.status === "ok"));
      assert.equal(nextPlan.error, undefined);
      return applyRoutePlan(current, nextPlan);
    },
    callService: async (...args) => {
      events.push("callService");
      assert.equal(args.length, 6);
      assert.equal(args[5], true);
      return haResponse({
        returncode: 0,
        stdout: JSON.stringify({
          ok: true,
          slots: [
            { encoderId: "ENC-01", status: "ok" },
            { encoderId: "ENC-02", status: "ok" },
          ],
        }),
      });
    },
  });

  assert.deepEqual(events, ["callService", "applyPlan"]);
  assert.equal(result.outcome.failed, false);
  assert.equal(result.lastPlan.error, undefined);
  assert.ok(result.assignments["ENC-01"]);
  assert.ok(result.assignments["ENC-02"]);
});

test("thrown live call does not save occupancy", async () => {
  const assignments = createEmptyAssignments();
  const result = await runLiveSendSafe({
    plan: samplePlan(),
    assignments,
    callService: async () => {
      throw new Error("connection lost");
    },
  });

  assert.equal(result.outcome.failed, true);
  assert.match(result.lastPlan.error, /connection lost/);
  assert.ok(result.lastPlan.warnings.some((warning) => /connection lost/.test(warning)));
  assert.deepEqual(result.assignments, assignments);
});

test("occupancyPlanFromLiveResult drops non-ok slots so applyRoutePlan cannot save them", () => {
  const occupancy = occupancyPlanFromLiveResult({
    ...samplePlan(),
    error: "partial",
    slots: [
      { encoderId: "ENC-01", status: "error", tvs: [1], program: { id: "g1", kind: "game", label: "A", channel: "FOX" } },
      { encoderId: "ENC-02", status: "ok", tvs: [3], program: { id: "g2", kind: "game", label: "B", channel: "CBS" } },
      { encoderId: "ENC-03", status: "planned", tvs: [5], program: { id: "g3", kind: "game", label: "C", channel: "NBC" } },
    ],
  });
  assert.deepEqual(
    occupancy.slots.map((slot) => slot.encoderId),
    ["ENC-02"]
  );
  assert.equal(occupancy.error, undefined);
});

test("dry-run applies occupancy for training and labels PRACTICE", () => {
  const result = runDryRunSend({
    plan: { ...samplePlan(), commit: "dry_run" },
    assignments: createEmptyAssignments(),
  });
  assert.equal(result.lastPlan.practice, true);
  assert.ok(result.assignments["ENC-01"]);
  assert.ok(result.assignments["ENC-02"]);
});

test("in-flight lock ignores a second send while the first await is pending", async () => {
  const lock = createInFlightLock();
  let calls = 0;
  let release;
  const pending = new Promise((resolve) => {
    release = resolve;
  });
  const send = async () => {
    calls += 1;
    await pending;
    return { ok: true };
  };

  const first = guardedSend(lock, send);
  const second = guardedSend(lock, send);
  assert.equal(lock.isSending(), true);
  assert.equal(isTakeArmed({ ready: true, sending: lock.isSending() }), false);
  release();
  const [a, b] = await Promise.all([first, second]);
  assert.equal(calls, 1);
  assert.equal(a.ignored, false);
  assert.equal(b.ignored, true);
  assert.equal(lock.isSending(), false);
  assert.equal(isTakeArmed({ ready: true, sending: false }), true);
});

test("panel _sendPlan wires returnResponse, occupancy-after-live, and _sending Take lock", () => {
  const src = readFileSync(
    new URL("../../homeassistant/config/www/panels/panel-health.js", import.meta.url),
    "utf8"
  );
  assert.match(src, /from\s+["']\.\/live-execute\.js/);
  assert.match(src, /liveExecuteCallServiceArgs|runLiveSendSafe/);
  assert.match(src, /this\._sending/);
  assert.match(src, /if \(this\._sending\) return/);
  assert.match(src, /Sending…|Sending\.\.\./);
  assert.match(src, /PRACTICE summary/);
  assert.match(src, /isTakeArmed/);

  const sendPlan = src.match(/async _sendPlan\(\) \{[\s\S]*?\n  \}/);
  assert.ok(sendPlan, "_sendPlan method should exist");
  const liveIdx = sendPlan[0].search(/runLiveSendSafe|runLiveSend/);
  const saveIdx = sendPlan[0].indexOf("_saveAssignments");
  assert.ok(liveIdx >= 0, "_sendPlan must call runLiveSendSafe/runLiveSend");
  assert.ok(saveIdx > liveIdx, "occupancy must be saved after the live call, not before");
  assert.doesNotMatch(
    sendPlan[0].slice(0, liveIdx),
    /_saveAssignments/,
    "must not save occupancy before the live call"
  );
});
