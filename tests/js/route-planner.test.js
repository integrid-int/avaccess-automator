import test from "node:test";
import assert from "node:assert/strict";
import {
  stripedTvs,
  buildRoutePlan,
  listFreeEncoders,
  listReplaceChoices,
} from "../../homeassistant/config/www/panels/route-planner.js";
import { applyRoutePlan, createEmptyAssignments, getAssignmentForTv } from "../../homeassistant/config/www/panels/assignment-store.js";

test("stripedTvs preset 2 maps ENC-01 and ENC-04", () => {
  assert.deepEqual(stripedTvs(4, 1), [1, 5, 9, 13, 17, 21, 25, 29, 33]);
  assert.deepEqual(stripedTvs(4, 4), [4, 8, 12, 16, 20, 24, 28, 32]);
});

test("buildRoutePlan preset_2 assigns up to N programs and omits unused slots", () => {
  const plan = buildRoutePlan({
    mode: "preset_2",
    programs: [
      { kind: "game", id: "g1", label: "Chiefs @ Bills", channel: "FOX", channelNumber: "206" },
      { kind: "game", id: "g2", label: "Eagles @ Cowboys", channel: "CBS", channelNumber: "207" },
    ],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.mode, "preset_2");
  assert.equal(plan.commit, "dry_run");
  assert.equal(plan.slots.length, 2);
  assert.equal(plan.slots[0].encoderId, "ENC-01");
  assert.deepEqual(plan.slots[0].tvs, stripedTvs(4, 1));
  assert.equal(plan.slots[1].encoderId, "ENC-02");
  assert.equal(plan.error, undefined);
});

test("buildRoutePlan preset_2 caps at 4 programs", () => {
  const programs = Array.from({ length: 5 }, (_, i) => ({
    kind: "game",
    id: `g${i}`,
    label: `Game ${i}`,
    channel: "FOX",
  }));
  const plan = buildRoutePlan({
    mode: "preset_2",
    programs,
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.slots.length, 4);
  assert.match(plan.warnings.join(" "), /ignored/i);
});

test("buildRoutePlan adhoc claims lowest free encoder including spare", () => {
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "channel", id: "ch-espn", label: "ESPN", channel: "ESPN", channelNumber: "206" }],
    selectedTvs: [3, 7],
    busyEncoderIds: ["ENC-01", "ENC-02", "ENC-03", "ENC-04", "ENC-05", "ENC-06", "ENC-07", "ENC-08", "ENC-09"],
  });
  assert.equal(plan.slots.length, 1);
  assert.equal(plan.slots[0].encoderId, "ENC-10");
  assert.deepEqual(plan.slots[0].tvs, [3, 7]);
});

test("buildRoutePlan adhoc errors when no free encoders", () => {
  const busy = listFreeEncoders([]);
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX" }],
    selectedTvs: [1],
    busyEncoderIds: busy,
  });
  assert.equal(plan.slots.length, 0);
  assert.match(plan.error, /No free encoders/i);
});

test("buildRoutePlan tunes a guide channel and skips a game without a number", () => {
  const channel = buildRoutePlan({
    mode: "preset_1",
    programs: [{ kind: "channel", id: "ch-espn", label: "206 ESPN", channel: "206", channelNumber: "206" }],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.deepEqual(channel.slots[0].tune, { channelNumber: "206" });
  const game = buildRoutePlan({
    mode: "preset_1",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX", channelNumber: null }],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(game.slots[0].tune, null);
});

function busyRoom() {
  const assignments = {
    "ENC-03": {
      encoderId: "ENC-03",
      label: "49ers @ Falcons",
      channel: "9558",
      tvs: [1, 2, 3, 4, 5, 6],
    },
  };
  const rest = [7, 8, 9, 10, 11, 12, 13, 14, 15];
  let n = 0;
  for (let i = 1; i <= 10; i += 1) {
    if (i === 3) continue;
    const encoderId = `ENC-${String(i).padStart(2, "0")}`;
    assignments[encoderId] = {
      encoderId,
      label: `Program ${i}`,
      channel: String(200 + i),
      tvs: [rest[n]],
    };
    n += 1;
  }
  return assignments;
}

test("buildRoutePlan reuses the box when every selected TV is already on it", () => {
  const assignments = busyRoom();
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "duke", label: "Tennessee @ Duke", channel: "612", channelNumber: "612" }],
    selectedTvs: [1, 3, 5],
    busyEncoderIds: listFreeEncoders([]),
    assignments,
  });
  assert.equal(plan.error, undefined);
  assert.equal(plan.slots[0].encoderId, "ENC-03");
  assert.deepEqual(plan.slots[0].tvs, [1, 3, 5]);
  assert.deepEqual(plan.replaced.offTvs, [2, 4, 6]);
  assert.equal(plan.replaced.label, "49ers @ Falcons");
});

test("buildRoutePlan does not reuse a box when the TVs span two programs", () => {
  const assignments = busyRoom();
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "duke", label: "Tennessee @ Duke", channel: "612", channelNumber: "612" }],
    selectedTvs: [1, 7],
    busyEncoderIds: Object.keys(assignments),
    assignments,
  });
  assert.match(plan.error, /No free encoders/i);
  assert.equal(plan.slots.length, 0);
  assert.equal(plan.replaceChoices.length, 10);
});

test("buildRoutePlan replace uses the chosen box and reports TVs that turn off", () => {
  const assignments = busyRoom();
  assignments["ENC-01"].tvs = [7, 8];
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "duke", label: "Tennessee @ Duke", channel: "612", channelNumber: "612" }],
    selectedTvs: [8, 9, 10],
    busyEncoderIds: listFreeEncoders([]),
    assignments,
    replaceEncoderId: "ENC-03",
  });
  assert.equal(plan.error, undefined);
  assert.equal(plan.slots[0].encoderId, "ENC-03");
  assert.deepEqual(plan.slots[0].tvs, [8, 9, 10]);
  assert.deepEqual(plan.replaced.offTvs, [1, 2, 3, 4, 5, 6]);

  let next = createEmptyAssignments();
  next = { ...assignments };
  next = applyRoutePlan(next, plan);
  assert.deepEqual(next["ENC-03"].tvs, [8, 9, 10]);
  assert.deepEqual(next["ENC-01"].tvs, [7]);
  assert.equal(getAssignmentForTv(next, 1), null);
  assert.equal(getAssignmentForTv(next, 8).encoderId, "ENC-03");
});

test("buildRoutePlan rejects a replace target that is not on", () => {
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX", channelNumber: "8" }],
    selectedTvs: [8],
    busyEncoderIds: [],
    assignments: {},
    replaceEncoderId: "ENC-04",
  });
  assert.match(plan.error, /Choose a program to replace/i);
});

test("listReplaceChoices skips encoders with no TVs", () => {
  const choices = listReplaceChoices({
    "ENC-01": { encoderId: "ENC-01", label: "CBS", channel: "2", tvs: [2] },
    "ENC-02": { encoderId: "ENC-02", label: "Empty", channel: "", tvs: [] },
  });
  assert.deepEqual(choices.map((choice) => choice.encoderId), ["ENC-01"]);
});

test("buildRoutePlan preset_1 uses ENC-01 and all TVs", () => {
  const plan = buildRoutePlan({
    mode: "preset_1",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX" }],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.slots.length, 1);
  assert.equal(plan.slots[0].encoderId, "ENC-01");
  assert.equal(plan.slots[0].tvs.length, 35);
});
