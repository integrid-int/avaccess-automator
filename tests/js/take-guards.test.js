import test from "node:test";
import assert from "node:assert/strict";
import {
  SPORTS,
  SPORTS_FALLBACK_BANNER,
  SPORTS_STALE_BANNER,
  SPORTS_STALE_MS,
  isSportsScheduleFresh,
  programHasTuneChannel,
  programsMissingTuneChannel,
  takeBlockReason,
} from "../../homeassistant/config/www/panels/panel-data.js";
import { buildRoutePlan } from "../../homeassistant/config/www/panels/route-planner.js";

const NO_CHANNEL_GAME = {
  kind: "game",
  id: "g-open",
  label: "Yankees @ Red Sox",
  channel: "No channel",
  channelNumber: null,
};
const TUNED_GAME = {
  kind: "game",
  id: "g-espn",
  label: "Chiefs @ Bills",
  channel: "ESPN",
  channelNumber: "206",
};

test("hardcoded SPORTS fallback games have no channelNumber", () => {
  const games = SPORTS.flatMap((sport) => sport.games);
  assert.ok(games.length > 0);
  for (const game of games) {
    assert.equal(game.channelNumber, undefined);
    assert.equal(programHasTuneChannel(game), false);
  }
});

test("programHasTuneChannel rejects empty, blank, and missing numbers", () => {
  assert.equal(programHasTuneChannel({ channelNumber: "206" }), true);
  assert.equal(programHasTuneChannel({ channelNumber: 208 }), true);
  assert.equal(programHasTuneChannel({ channelNumber: null }), false);
  assert.equal(programHasTuneChannel({ channelNumber: "" }), false);
  assert.equal(programHasTuneChannel({ channelNumber: "  " }), false);
  assert.equal(programHasTuneChannel({ channel: "FOX" }), false);
  assert.equal(programHasTuneChannel(null), false);
});

test("takeBlockReason blocks any Take when a selected program lacks a channel", () => {
  const reason = takeBlockReason({
    programs: [NO_CHANNEL_GAME],
    liveCommit: false,
    usingSportsFallback: false,
  });
  assert.match(reason, /no DirecTV channel/i);
  assert.match(reason, /Yankees @ Red Sox/);
});

test("takeBlockReason blocks Live Take on demo sports fallback even with a numbered game", () => {
  const reason = takeBlockReason({
    programs: [TUNED_GAME],
    liveCommit: true,
    usingSportsFallback: true,
  });
  assert.match(reason, /Live Take blocked/i);
  assert.match(reason, /demo/i);
});

test("takeBlockReason allows dry-run Take on fallback when the program has a channel", () => {
  const reason = takeBlockReason({
    programs: [TUNED_GAME],
    liveCommit: false,
    usingSportsFallback: true,
  });
  assert.equal(reason, "");
});

test("takeBlockReason allows Live Take when every program has a channel and schedule is real", () => {
  const reason = takeBlockReason({
    programs: [TUNED_GAME, { ...TUNED_GAME, id: "g2", channelNumber: "207" }],
    liveCommit: true,
    usingSportsFallback: false,
  });
  assert.equal(reason, "");
});

test("takeBlockReason lists multiple programs missing a channel", () => {
  const reason = takeBlockReason({
    programs: [NO_CHANNEL_GAME, { ...NO_CHANNEL_GAME, id: "g2", label: "Dodgers @ Giants" }],
    liveCommit: true,
    usingSportsFallback: false,
  });
  assert.match(reason, /2 selected programs have no DirecTV channel/i);
});

test("programsMissingTuneChannel returns only the unnumbered games", () => {
  const missing = programsMissingTuneChannel([TUNED_GAME, NO_CHANNEL_GAME]);
  assert.deepEqual(
    missing.map((item) => item.id),
    ["g-open"]
  );
});

test("buildRoutePlan errors instead of planning a Live slot with no tune", () => {
  const plan = buildRoutePlan({
    mode: "preset_1",
    programs: [NO_CHANNEL_GAME],
    selectedTvs: [],
    busyEncoderIds: [],
    commit: "live",
  });
  assert.equal(plan.slots.length, 0);
  assert.match(plan.error, /no DirecTV channel/i);
});

test("buildRoutePlan also blocks dry-run Take when a selected program has no channel", () => {
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [NO_CHANNEL_GAME],
    selectedTvs: [1, 2],
    busyEncoderIds: [],
    commit: "dry_run",
  });
  assert.equal(plan.slots.length, 0);
  assert.match(plan.error, /no DirecTV channel/i);
});

test("buildRoutePlan preset_2 errors if any chosen program lacks a channel", () => {
  const plan = buildRoutePlan({
    mode: "preset_2",
    programs: [TUNED_GAME, NO_CHANNEL_GAME],
    selectedTvs: [],
    busyEncoderIds: [],
    commit: "live",
  });
  assert.equal(plan.slots.length, 0);
  assert.match(plan.error, /Yankees @ Red Sox/i);
});

test("isSportsScheduleFresh is false after 24 hours and true before", () => {
  const nowMs = Date.parse("2026-10-21T12:00:00Z");
  assert.equal(SPORTS_STALE_MS, 24 * 60 * 60 * 1000);
  assert.equal(
    isSportsScheduleFresh({ generatedAt: "2026-10-20T12:00:01Z" }, nowMs),
    true
  );
  assert.equal(
    isSportsScheduleFresh({ generatedAt: "2026-10-20T11:59:59Z" }, nowMs),
    false
  );
  assert.equal(isSportsScheduleFresh({ generatedAt: "bogus" }, nowMs), false);
  assert.equal(isSportsScheduleFresh({}, nowMs), false);
});

test("sports fallback and stale banner copy name the demo list and the 24 hour limit", () => {
  assert.match(SPORTS_FALLBACK_BANNER, /demo/i);
  assert.match(SPORTS_STALE_BANNER, /24 hours/i);
});
