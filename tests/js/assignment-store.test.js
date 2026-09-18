// tests/js/assignment-store.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  applyAssignment,
  applyRoutePlan,
  listBusyEncoderIds,
  getAssignmentForProgram,
  getAssignmentForTv,
  resolveSendPresetId,
  createEmptyAssignments,
} from "../../homeassistant/config/www/panels/assignment-store.js";
import { PRESETS, range } from "../../homeassistant/config/www/panels/panel-data.js";

test("applyAssignment clears overlapping TVs from other routes", () => {
  let assignments = {};
  assignments = applyAssignment(assignments, {
    routeId: "game-a",
    kind: "game",
    sportId: "nfl",
    label: "Chiefs @ Bills",
    channel: "FOX",
    presetId: "1_all",
    tvs: [1, 2, 3],
  });
  assignments = applyAssignment(assignments, {
    routeId: "game-b",
    kind: "game",
    sportId: "nfl",
    label: "Eagles @ Cowboys",
    channel: "CBS",
    presetId: null,
    tvs: [3, 4],
  });

  assert.deepEqual(assignments["game-a"].tvs, [1, 2]);
  assert.deepEqual(assignments["game-b"].tvs, [3, 4]);
  assert.equal(getAssignmentForTv(assignments, 3).routeId, "game-b");
});

test("resolveSendPresetId keeps explicit preset when TV lists overlap", () => {
  const allTvs = range(1, 35);
  assert.equal(
    resolveSendPresetId({
      destMode: "presets",
      selectedPresetId: "2_four_programs",
      selectedTvs: allTvs,
      presets: PRESETS,
    }),
    "2_four_programs"
  );
  assert.equal(
    resolveSendPresetId({
      destMode: "presets",
      selectedPresetId: "3_nine_programs",
      selectedTvs: allTvs,
      presets: PRESETS,
    }),
    "3_nine_programs"
  );
});

test("resolveSendPresetId returns null for adhoc TV picks", () => {
  assert.equal(
    resolveSendPresetId({
      destMode: "tvs",
      selectedPresetId: "2_four_programs",
      selectedTvs: [1, 2, 3],
      presets: PRESETS,
    }),
    null
  );
});

test("applyRoutePlan stores encoder slots and clears overlapping TVs", () => {
  let assignments = createEmptyAssignments();
  assignments = applyRoutePlan(assignments, {
    mode: "preset_2",
    commit: "dry_run",
    slots: [
      {
        index: 1,
        encoderId: "ENC-01",
        program: { kind: "game", id: "g1", label: "A @ B", channel: "FOX" },
        tvs: [1, 5, 9],
        tune: null,
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
  });
  assert.deepEqual(assignments["ENC-01"].tvs, [1, 5, 9]);
  assert.equal(listBusyEncoderIds(assignments).includes("ENC-01"), true);

  assignments = applyRoutePlan(assignments, {
    mode: "adhoc",
    commit: "dry_run",
    slots: [
      {
        index: 1,
        encoderId: "ENC-02",
        program: { kind: "game", id: "g2", label: "C @ D", channel: "CBS" },
        tvs: [5, 6],
        tune: null,
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
  });
  assert.deepEqual(assignments["ENC-01"].tvs, [1, 9]);
  assert.deepEqual(assignments["ENC-02"].tvs, [5, 6]);
  assert.equal(getAssignmentForTv(assignments, 5).encoderId ?? getAssignmentForTv(assignments, 5).routeId, "ENC-02");
});

test("applyRoutePlan no-ops when plan has error", () => {
  const before = createEmptyAssignments();
  const after = applyRoutePlan(before, {
    mode: "adhoc",
    commit: "dry_run",
    slots: [],
    warnings: [],
    error: "No free encoders",
  });
  assert.deepEqual(after, before);
});

test("getAssignmentForProgram finds ENC-XX slots by programId after applyRoutePlan", () => {
  let assignments = createEmptyAssignments();
  assignments = applyRoutePlan(assignments, {
    mode: "adhoc",
    commit: "dry_run",
    slots: [
      {
        index: 1,
        encoderId: "ENC-01",
        program: { kind: "game", id: "g1", label: "A @ B", channel: "FOX" },
        tvs: [1, 5, 9],
        tune: null,
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
  });

  const byProgram = getAssignmentForProgram(assignments, "g1");
  assert.ok(byProgram);
  assert.equal(byProgram.routeId, "ENC-01");
  assert.equal(byProgram.programId, "g1");
  assert.deepEqual(byProgram.tvs, [1, 5, 9]);
  assert.equal(getAssignmentForProgram(assignments, "ENC-01")?.programId, "g1");
  assert.equal(getAssignmentForProgram(assignments, "missing"), null);
});
