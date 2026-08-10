// tests/js/assignment-store.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { applyAssignment, getAssignmentForTv, resolveSendPresetId } from "../../homeassistant/config/www/panels/assignment-store.js";
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
