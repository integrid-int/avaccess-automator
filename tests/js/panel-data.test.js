import test from "node:test";
import assert from "node:assert/strict";
import {
  SPECTRUM_ZIP,
  SPORTS,
  GUIDE_CHANNELS,
  PRESETS,
  filterGuideChannels,
} from "../../homeassistant/config/www/panels/panel-data.js";

test("spectrum zip is 27403 and sports include nhl/mlb/wnba", () => {
  assert.equal(SPECTRUM_ZIP, "27403");
  const ids = SPORTS.map((s) => s.id);
  for (const id of ["nfl", "cfb", "nba", "nhl", "mlb", "wnba"]) {
    assert.ok(ids.includes(id));
  }
});

test("guide filter matches channel number or name", () => {
  const hits = filterGuideChannels(GUIDE_CHANNELS, "espn");
  assert.ok(hits.some((c) => c.number === "206"));
});

test("presets expose 1_all / 2_four_programs / 3_nine_programs", () => {
  assert.deepEqual(
    PRESETS.map((p) => p.id),
    ["1_all", "2_four_programs", "3_nine_programs"]
  );
});

test("presets expose programCapacity and stripeCount for groups", () => {
  const byId = Object.fromEntries(PRESETS.map((p) => [p.id, p]));
  assert.equal(byId["1_all"].programCapacity, 1);
  assert.equal(byId["1_all"].stripeCount, null);
  assert.equal(byId["2_four_programs"].programCapacity, 4);
  assert.equal(byId["2_four_programs"].stripeCount, 4);
  assert.equal(byId["3_nine_programs"].programCapacity, 9);
  assert.equal(byId["3_nine_programs"].stripeCount, 9);
  assert.equal(byId["2_four_programs"].blocks, undefined);
});
