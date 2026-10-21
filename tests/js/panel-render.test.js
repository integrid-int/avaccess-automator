import test from "node:test";
import assert from "node:assert/strict";
import { LIVE_COMMIT_ENTITY } from "../../homeassistant/config/www/panels/live-execute.js";
import { SPORTS_FALLBACK_BANNER, SPORTS_STALE_BANNER } from "../../homeassistant/config/www/panels/panel-data.js";
import { LIVE_BANNER, PRACTICE_BANNER } from "../../homeassistant/config/www/panels/panel-view.js";
import { assertRendered, makePanel, renderedHeader } from "./panel-harness.js";

function hassWith(panel, state) {
  return { ...panel.hass, states: { [LIVE_COMMIT_ENTITY]: { entity_id: LIVE_COMMIT_ENTITY, state } } };
}

function bannerOf(panel) {
  const header = renderedHeader(panel);
  const banner = header.match(/<div class="mode-banner is-(\w+)"[^>]*data-commit-mode="(\w+)"[^>]*>([^<]*)</);
  assert.ok(banner, "header should carry the PRACTICE/LIVE banner");
  const routing = panel.innerHTML.match(/<div class="routing( is-live)?">/);
  assert.ok(routing, "routing board should render");
  return { mode: banner[2], cssMode: banner[1], text: banner[3], boardLive: Boolean(routing[1]) };
}

test("header banner says PRACTICE while Live commit is off", () => {
  const { panel } = makePanel({ liveState: "off" });
  assert.deepEqual(bannerOf(panel), {
    mode: "practice",
    cssMode: "practice",
    text: PRACTICE_BANNER,
    boardLive: false,
  });
});

test("header banner says LIVE and the board turns live when HA reports the boolean on", () => {
  const { panel } = makePanel({ liveState: "on" });
  assert.deepEqual(bannerOf(panel), { mode: "live", cssMode: "live", text: LIVE_BANNER, boardLive: true });
});

test("banner stays PRACTICE when the boolean is on but inventory is not Live-ready", () => {
  const { panel } = makePanel({ liveState: "on" });
  panel._inventoryLiveReady = false;
  panel.hass = hassWith(panel, "on");
  assert.equal(bannerOf(panel).mode, "practice");
});

test("render() re-reads the HA boolean, so the banner follows state without a new hass object", () => {
  const { panel } = makePanel({ liveState: "on" });
  panel.hass.states[LIVE_COMMIT_ENTITY].state = "off";
  assert.equal(bannerOf(panel).mode, "practice");
  panel.hass.states[LIVE_COMMIT_ENTITY].state = "on";
  assert.equal(bannerOf(panel).mode, "live");
});

test("rail renders Guide, Now, Sets pinned above the sports list", () => {
  const { panel } = makePanel({ liveState: "off" });
  const rail = panel.innerHTML.match(/<nav class="rail"[\s\S]*?<\/nav>/);
  assert.ok(rail, "rail should render");
  const pinned = rail[0].match(/<div class="rail-pinned">([\s\S]*?)<\/div>/);
  const sports = rail[0].match(/<div class="rail-sports"[^>]*>([\s\S]*?)<\/div>/);
  assert.ok(pinned && sports, "rail should have a pinned group and a sports group");
  assert.ok(rail[0].indexOf(pinned[0]) < rail[0].indexOf(sports[0]), "pinned group comes first");

  const pinnedActions = [...pinned[1].matchAll(/data-action="([\w-]+)"/g)].map((m) => m[1]);
  assert.deepEqual(pinnedActions, ["open-guide", "open-now", "open-sets"]);
  const sportIds = [...sports[1].matchAll(/data-action="select-sport"\s+data-value="([\w-]+)"/g)].map((m) => m[1]);
  assert.deepEqual(sportIds, panel._sports().map((sport) => sport.id));
});

function fakeScroller(key, top = 0) {
  return {
    scrollTop: top,
    scrollLeft: 0,
    getAttribute: (name) => (name === "data-scroll-key" ? key : null),
  };
}

test("hass pushes keep list scroll: unchanged HTML skips the redraw, changed HTML restores scroll", () => {
  const { panel } = makePanel({ liveState: "off" });
  let html = panel.innerHTML;
  let writes = 0;
  let scrollers = [fakeScroller("rail-sports", 120), fakeScroller("displays:routing", 300)];
  Object.defineProperty(panel, "innerHTML", {
    configurable: true,
    get: () => html,
    set: (next) => {
      html = next;
      writes += 1;
      scrollers = [fakeScroller("rail-sports"), fakeScroller("displays:routing")];
    },
  });
  panel.querySelectorAll = () => scrollers;

  panel.hass = hassWith(panel, "off");
  assert.equal(writes, 0, "an unchanged hass push must not rebuild the DOM");
  assert.equal(scrollers[0].scrollTop, 120);

  panel.hass = hassWith(panel, "on");
  assert.equal(writes, 1);
  assert.deepEqual(
    scrollers.map((item) => item.scrollTop),
    [120, 300],
    "new DOM must get the old scroll positions back"
  );
});

test("sports banner warns on the demo fallback and on a stale schedule", () => {
  const { panel } = makePanel({ liveState: "off" });
  assertRendered(panel, /class="sports-schedule-banner"/, { present: false });

  panel.sportsStatus = "fallback";
  panel.render();
  assert.ok(panel.innerHTML.includes(SPORTS_FALLBACK_BANNER), "fallback banner should render");

  panel.sportsStatus = "ok";
  panel.sportsGeneratedAt = new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString();
  panel.render();
  assert.ok(panel.innerHTML.includes(SPORTS_STALE_BANNER), "stale banner should render");
});
