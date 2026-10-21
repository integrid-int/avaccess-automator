import test from "node:test";
import assert from "node:assert/strict";
import {
  LIVE_BANNER,
  PRACTICE_BANNER,
  captureScrollPositions,
  commitModeBanner,
  restoreScrollPositions,
  teamInitials,
} from "../../homeassistant/config/www/panels/panel-view.js";

test("commitModeBanner says PRACTICE unless live commit is on with a ready inventory", () => {
  assert.equal(PRACTICE_BANNER, "PRACTICE – TVs will not change");
  assert.equal(LIVE_BANNER, "LIVE – TVs WILL change");
  assert.deepEqual(commitModeBanner({ liveCommit: false, inventoryLiveReady: true }), {
    mode: "practice",
    text: PRACTICE_BANNER,
  });
  assert.deepEqual(commitModeBanner({ liveCommit: true, inventoryLiveReady: false }), {
    mode: "practice",
    text: PRACTICE_BANNER,
  });
  assert.deepEqual(commitModeBanner({ liveCommit: true, inventoryLiveReady: true }), {
    mode: "live",
    text: LIVE_BANNER,
  });
  assert.equal(commitModeBanner().mode, "practice");
});

test("teamInitials builds a short tile label from team names", () => {
  assert.equal(teamInitials("Missouri State"), "MS");
  assert.equal(teamInitials("Middle Tenn. State"), "MTS");
  assert.equal(teamInitials("FIU"), "FIU");
  assert.equal(teamInitials("Delaware"), "DEL");
  assert.equal(teamInitials("Texas A&M"), "TA");
  assert.equal(teamInitials("San Francisco 49ers"), "SF4");
  assert.equal(teamInitials("  "), "?");
  assert.equal(teamInitials(null), "?");
});

function fakeScroller(key, top = 0, left = 0) {
  return {
    scrollTop: top,
    scrollLeft: left,
    getAttribute(name) {
      return name === "data-scroll-key" ? key : null;
    },
  };
}

function fakeRoot(elements) {
  return {
    querySelectorAll(selector) {
      assert.equal(selector, "[data-scroll-key]");
      return elements;
    },
  };
}

test("scroll positions survive a full re-render for matching keys only", () => {
  const before = fakeRoot([
    fakeScroller("sources:browse-sport:football:all", 640),
    fakeScroller("displays:routing", 220),
    fakeScroller("league-chips:football", 0, 90),
    fakeScroller("rail-sports", 0),
  ]);
  const snapshot = captureScrollPositions(before);
  assert.equal(snapshot.size, 3);

  const sources = fakeScroller("sources:browse-sport:football:all");
  const displays = fakeScroller("displays:routing");
  const chips = fakeScroller("league-chips:football");
  const otherSport = fakeScroller("sources:browse-sport:hockey:all");
  restoreScrollPositions(fakeRoot([sources, displays, chips, otherSport]), snapshot);

  assert.equal(sources.scrollTop, 640);
  assert.equal(displays.scrollTop, 220);
  assert.equal(chips.scrollLeft, 90);
  assert.equal(otherSport.scrollTop, 0, "a new list starts at the top");
});

test("scroll helpers tolerate a missing root or empty snapshot", () => {
  assert.equal(captureScrollPositions(null).size, 0);
  restoreScrollPositions(null, new Map([["x", { top: 1, left: 0 }]]));
  restoreScrollPositions(fakeRoot([fakeScroller("x")]), null);
});
