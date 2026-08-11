import test from "node:test";
import assert from "node:assert/strict";
import {
  SPECTRUM_ZIP,
  SPORTS,
  GUIDE_CHANNELS,
  PRESETS,
  filterGuideChannels,
  filterGuideByCategory,
  guideCategories,
  mergeGuideWithEpg,
  isGuideEpgFresh,
  sportsFromEpg,
  filterSportsByTab,
} from "../../homeassistant/config/www/panels/panel-data.js";

test("spectrum zip is 27403 and sports tabs are EPG filters", () => {
  assert.equal(SPECTRUM_ZIP, "27403");
  const ids = SPORTS.map((s) => s.id);
  assert.deepEqual(ids, ["all", "nfl", "cfb", "nba", "nhl", "mlb", "wnba", "other"]);
  assert.ok(GUIDE_CHANNELS.length >= 100);
  assert.ok(GUIDE_CHANNELS.some((c) => c.number === "17" && c.name === "ESPN"));
  assert.ok(!GUIDE_CHANNELS.some((c) => /music choice/i.test(c.name)));
});

test("guide filter matches channel number or name", () => {
  const hits = filterGuideChannels(GUIDE_CHANNELS, "espn");
  assert.ok(hits.some((c) => c.number === "17"));
});

test("guide category filter and categories list", () => {
  const cats = guideCategories(GUIDE_CHANNELS);
  assert.ok(cats.includes("Sports"));
  assert.ok(cats.includes("Local"));
  const sports = filterGuideByCategory(GUIDE_CHANNELS, "Sports");
  assert.ok(sports.length > 0);
  assert.ok(sports.every((c) => c.category === "Sports"));
  assert.equal(filterGuideByCategory(GUIDE_CHANNELS, "All").length, GUIDE_CHANNELS.length);
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

test("mergeGuideWithEpg attaches now/next when feed fresh", () => {
  const nowMs = Date.parse("2026-08-10T18:30:00Z");
  const feed = {
    zip: "27403",
    generatedAt: "2026-08-10T18:00:00Z",
    channels: {
      "17": {
        number: "17",
        now: { title: "SportsCenter" },
        next: { title: "NFL Live" },
      },
    },
  };
  const { channels, epgAvailable } = mergeGuideWithEpg(GUIDE_CHANNELS, feed, nowMs);
  assert.equal(epgAvailable, true);
  const espn = channels.find((c) => c.number === "17");
  assert.equal(espn.nowTitle, "SportsCenter");
  assert.equal(espn.nextTitle, "NFL Live");
});

test("mergeGuideWithEpg marks unavailable when stale", () => {
  const nowMs = Date.parse("2026-08-11T12:00:00Z");
  const feed = { zip: "27403", generatedAt: "2026-08-10T18:00:00Z", channels: {} };
  const { epgAvailable } = mergeGuideWithEpg(GUIDE_CHANNELS, feed, nowMs);
  assert.equal(epgAvailable, false);
  assert.equal(isGuideEpgFresh(feed, nowMs), false);
});

test("sportsFromEpg reads now/upcoming and filters by tab", () => {
  const nowMs = Date.parse("2026-08-10T18:30:00Z");
  const feed = {
    generatedAt: "2026-08-10T18:00:00Z",
    sports: {
      windowHours: 12,
      now: [
        {
          id: "sport-17-a",
          channelNumber: "17",
          channelName: "ESPN",
          title: "SportsCenter",
          start: "2026-08-10T18:00:00+00:00",
          end: "2026-08-10T19:00:00+00:00",
          sportKey: "other",
        },
      ],
      upcoming: [
        {
          id: "sport-17-b",
          channelNumber: "17",
          channelName: "ESPN",
          title: "College Football: Georgia vs Alabama",
          start: "2026-08-10T19:00:00+00:00",
          end: "2026-08-10T21:00:00+00:00",
          sportKey: "cfb",
        },
      ],
    },
  };
  const { available, now, upcoming } = sportsFromEpg(feed, nowMs);
  assert.equal(available, true);
  assert.equal(now.length, 1);
  assert.equal(upcoming.length, 1);
  assert.equal(filterSportsByTab([...now, ...upcoming], "cfb").length, 1);
  assert.equal(filterSportsByTab([...now, ...upcoming], "nfl").length, 0);
  assert.equal(sportsFromEpg(null, nowMs).available, false);
});

test("filterGuideChannels matches now/next titles", () => {
  const rows = [
    {
      number: "17",
      name: "ESPN",
      category: "Sports",
      nowTitle: "SportsCenter",
      nextTitle: "NFL Live",
    },
  ];
  assert.equal(filterGuideChannels(rows, "sportscenter").length, 1);
});
