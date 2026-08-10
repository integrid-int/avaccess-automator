import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { SPORTS, SPECTRUM_ZIP } from "../../homeassistant/config/www/panels/panel-data.js";

function readPanelSource() {
  return readFileSync(
    new URL("../../homeassistant/config/www/panels/panel-health.js", import.meta.url),
    "utf8"
  );
}

test("panel shell imports store/data and defines panel-health once", () => {
  const src = readPanelSource();
  assert.match(src, /from\s+["']\.\/assignment-store\.js(?:\?v=\d+)?["']/);
  assert.match(src, /from\s+["']\.\/panel-data\.js(?:\?v=\d+)?["']/);
  assert.match(src, /customElements\.get\(["']panel-health["']\)/);
  assert.match(src, /#0e7490/);
  assert.match(src, /browse-tvs/);
  assert.match(src, /content-picker/);
});

test("panel shell exposes chip actions for sports guide and TVs", () => {
  const src = readPanelSource();
  assert.match(src, /data-action=["']open-sport["']/);
  assert.match(src, /data-action=["']open-guide["']/);
  assert.match(src, /data-action=["']open-tvs["']/);
});

test("panel shell exposes content-first destination actions and labels", () => {
  const src = readPanelSource();
  assert.match(src, /data-action=["']select-sport["']/);
  assert.match(src, /data-action=["']select-game["']/);
  assert.match(src, /data-action=["']select-channel["']/);
  assert.match(src, /data-action=["']set-dest-mode["']/);
  assert.match(src, /data-action=["']select-group["']/);
  assert.match(src, /data-action=["']toggle-tv["']/);
  assert.match(src, /data-action=["']send-destination["']/);
  assert.match(src, /data-action=["']back-browse["']/);
  assert.match(src, /Presets/);
  assert.match(src, /Pick TVs/);
  assert.match(src, /Spectrum · ZIP 27403/);
});

test("panel shell exposes TV-first content picker actions and summary", () => {
  const src = readPanelSource();
  assert.match(src, /data-action="next-choose-content"/);
  assert.match(src, /data-action="send-tv-first"/);
  assert.match(src, /Sending to TVs:/);
});

test("panel shell renders short sports chips and Spectrum ZIP guide label", () => {
  const src = readPanelSource();
  const chipLabels = Object.fromEntries(SPORTS.map((sport) => [sport.id, sport.chipTitle]));

  assert.deepEqual(chipLabels, {
    all: "All",
    nfl: "NFL",
    cfb: "CFB",
    nba: "NBA",
    nhl: "NHL",
    other: "Other",
  });
  assert.equal(SPECTRUM_ZIP, "27403");
  assert.match(src, /item\.chipTitle\s*\?\?\s*item\.title/);
  assert.match(src, /Spectrum · ZIP \$\{escapeHtml\(SPECTRUM_ZIP\)\} · Xumo/);
  assert.match(src, /set-guide-category/);
  assert.match(src, /sportsFromEpg/);
});

test("panel shell tracks selectedPresetId for TV-first preset send", () => {
  const src = readPanelSource();
  assert.match(src, /selectedPresetId/);
  assert.match(src, /resolveSendPresetId/);
});

test("panel shell keeps radii at token scale and avoids amber assignment accents", () => {
  const src = readPanelSource();
  const radiusValues = [...src.matchAll(/border-radius:\s*([^;]+);/g)].map((match) => match[1]);

  for (const value of radiusValues) {
    for (const pixel of value.matchAll(/(\d+)px/g)) {
      assert.ok(Number(pixel[1]) <= 10, `border-radius exceeds 10px: ${value}`);
    }
  }
  assert.doesNotMatch(src, /999px/);
  assert.doesNotMatch(src, /#fef3c7/i);
});

test("panel shell brands AVAccess Sports Routing and drops stub content picker", () => {
  const src = readPanelSource();
  assert.match(src, /AVAccess · iPad/);
  assert.match(src, /Sports Routing/);
  assert.doesNotMatch(src, /open-content-picker/);
  assert.doesNotMatch(src, /Graphite routing shell/);
});

test("panel shell renders EPG sport cards, route badges, and restores guide search focus", () => {
  const src = readPanelSource();
  assert.match(src, /epg-title/);
  assert.match(src, /route-badge/);
  assert.match(src, /_captureGuideSearchCaret/);
  assert.match(src, /_restoreGuideSearchCaret/);
  assert.match(src, /setSelectionRange/);
});

test("panel shell exposes group-first multi-program and dry-run plan actions", () => {
  const src = readPanelSource();
  assert.match(src, /buildRoutePlan/);
  assert.match(src, /applyRoutePlan/);
  assert.match(src, /program-picker/);
  assert.match(src, /data-action=\"select-group\"/);
  assert.match(src, /data-action=\"toggle-program\"/);
  assert.match(src, /data-action=\"send-plan\"/);
  assert.match(src, /Dry-run/);
  assert.match(src, /No free encoders/);
  assert.doesNotMatch(src, /Split across 4 encoder groups/);
});

test("panel shell clears stale groupMode and routes adhoc destination through planner", () => {
  const src = readPanelSource();
  assert.match(src, /_setDestMode/);
  assert.match(src, /_shouldSendViaPlan/);
  assert.match(src, /groupMode:\s*["']adhoc["']/);
  assert.match(src, /groupMode:\s*null/);
  assert.match(src, /destMode === ["']tvs["']\s*\?\s*["']adhoc["']/);
  assert.match(src, /mode:\s*["']adhoc["']/);
  assert.match(src, /plan-error-banner/);
  // Preset 2/3 select-group must not seed the full 1–35 TV list into selectedTvs.
  assert.match(
    src,
    /programCapacity\s*>\s*1[\s\S]*?selectedTvs:\s*\[\s*\]/
  );
});

test("panel shell exposes live commit toggle and shell_command execute path", () => {
  const src = readPanelSource();
  assert.match(src, /liveCommit/);
  assert.match(src, /avaccess_execute_route_plan/);
  assert.match(src, /Live Send|live commit/i);
  assert.match(src, /inventory\.json/);
  assert.match(src, /networkIssues|udp_switch_port/);
  assert.match(src, /parseLiveExecuteReport|mergeLiveReportIntoPlan/);
  assert.match(src, /Live summary/);
  assert.match(src, /plan\.commit\s*===\s*["']live["']/);
});

test("panel shell loads guide EPG feed and renders now/next columns", () => {
  const src = readPanelSource();
  assert.match(src, /guide_epg\.json/);
  assert.match(src, /mergeGuideWithEpg/);
  assert.match(src, /guide unavailable|Guide listings unavailable/i);
  assert.match(src, /nowTitle|Now/);
  assert.match(src, /nextTitle|Next/);
});
