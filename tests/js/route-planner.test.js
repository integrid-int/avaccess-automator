import test from "node:test";
import assert from "node:assert/strict";
import {
  stripedTvs,
  buildRoutePlan,
  listFreeEncoders,
} from "../../homeassistant/config/www/panels/route-planner.js";

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
