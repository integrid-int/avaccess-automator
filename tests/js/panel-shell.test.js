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
  assert.match(src, /from\s+["']\.\/assignment-store\.js(\?v=\d+)?["']/);
  assert.match(src, /from\s+["']\.\/panel-data\.js(\?v=\d+)?["']/);
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
  assert.match(src, /DirecTV · ZIP 27403/);
});

test("panel shell exposes TV-first content picker actions and summary", () => {
  const src = readPanelSource();
  assert.match(src, /data-action="next-choose-content"/);
  assert.match(src, /data-action="send-tv-first"/);
  assert.match(src, /Sending to TVs:/);
});

test("panel shell renders short sports chips and DirecTV ZIP guide label", () => {
  const src = readPanelSource();
  const chipLabels = Object.fromEntries(SPORTS.map((sport) => [sport.id, sport.chipTitle]));

  assert.deepEqual(chipLabels, {
    nfl: "NFL",
    cfb: "CFB",
    nba: "NBA",
    nhl: "NHL",
    mlb: "MLB",
    wnba: "WNBA",
  });
  assert.equal(SPECTRUM_ZIP, "27403");
  assert.match(src, /item\.chipTitle\s*\?\?\s*item\.title/);
  assert.match(src, /DirecTV · ZIP \$\{escapeHtml\(SPECTRUM_ZIP\)\}/);
});

test("panel shell tunes a sports game from the DirecTV major", () => {
  const src = readPanelSource();
  assert.match(src, /\/local\/avaccess\/sports_schedule\.json/);
  assert.match(src, /directv-sports-info/);
  assert.match(src, /payload\.source === SPORTS_SOURCE/);
  assert.match(src, /channelNumber: content\.channelNumber \? String\(content\.channelNumber\) : null/);
  assert.match(
    src,
    /setInterval\(\(\) => \{\s*this\._loadGuideEpg\(\);\s*this\._loadSportsSchedule\(\);/
  );
  assert.match(src, /data-action="select-league"/);
  assert.match(src, /game\.leagueId === leagueId/);
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

test("panel shell brands the routing board and drops stub content picker", () => {
  const src = readPanelSource();
  assert.match(src, /class="routing(?:"|\$\{)/);
  assert.match(src, /class="room">Bar</);
  assert.match(src, /<h2>Sources<\/h2>/);
  assert.match(src, /<h2>Displays<\/h2>/);
  assert.match(src, /data-action="send-destination"/);
  assert.match(src, />Take</);
  assert.match(src, /#0b5cab/);
  assert.match(src, /height: calc\(100dvh - 64px\)/);
  assert.match(src, /takes one program/);
  assert.match(src, /Ready · /);
  assert.match(src, /_formatTvList/);
  assert.match(src, /_tvOccupancy/);
  assert.match(src, /Live commit is off until the room inventory is set up/);
  assert.match(src, /Tune \$\{/);
  assert.match(src, /Now: /);
  assert.match(src, /GUIDE_SEARCH_DELAY_MS/);
  assert.match(src, /open-now/);
  assert.match(src, /Now playing/);
  assert.match(src, /_deepActiveElement/);
  assert.doesNotMatch(src, /open-content-picker/);
  assert.doesNotMatch(src, /Graphite routing shell/);
  assert.doesNotMatch(src, /fonts\.googleapis\.com\/css2\?family=Sora/);
});

test("panel shell renders logos, route badges, and restores guide search focus", () => {
  const src = readPanelSource();
  assert.match(src, /awayLogo/);
  assert.match(src, /homeLogo/);
  assert.match(src, /team-logo/);
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
  // A guide channel must not become a hidden 4-program pick after the rail moves to sports.
  assert.match(src, /_programsForMultiPreset/);
  assert.match(src, /onGuide \? content\.kind === "channel" : content\.kind === "game"/);
});

test("panel shell exposes live commit toggle and gated script execute path", () => {
  const src = readPanelSource();
  const liveSrc = readFileSync(
    new URL("../../homeassistant/config/www/panels/live-execute.js", import.meta.url),
    "utf8"
  );
  assert.match(src, /liveCommit/);
  assert.match(src, /runLiveSendSafe|live-execute/);
  assert.match(liveSrc, /avaccess_live_execute/);
  assert.doesNotMatch(liveSrc, /avaccess_execute_route_plan/);
  // The toggle writes the HA boolean; the panel never flips a local-only flag.
  assert.match(src, /callService\(\.\.\.liveCommitToggleArgs\(/);
  assert.doesNotMatch(src, /_setState\(\{\s*liveCommit:/);
  assert.doesNotMatch(src, /_liveCommitSynced/);
  assert.match(src, /render\(\)\s*\{\s*if \(!this\.isConnected\) return;\s*this\._syncLiveCommitFromHass\(\);/);
  assert.match(liveSrc, /returnResponse|true,\s*true/);
  assert.match(src, /Live Send|live commit/i);
  assert.match(src, /inventory\.json/);
  assert.match(src, /networkIssues|udp_switch_port/);
  assert.match(src, /parseLiveExecuteReport|mergeLiveReportIntoPlan|runLiveSendSafe|live-execute/);
  assert.match(src, /Live summary/);
  assert.match(src, /plan\.commit\s*===\s*["']live["']/);
});

test("panel shell blocks Take without a channel and banners demo sports fallback", () => {
  const src = readPanelSource();
  assert.match(src, /takeBlockReason/);
  assert.match(src, /_usingSportsFallback/);
  assert.match(src, /sports-schedule-banner/);
  assert.match(src, /SPORTS_FALLBACK_BANNER/);
  assert.match(src, /SPORTS_STALE_BANNER/);
  assert.match(src, /isSportsScheduleFresh/);
  assert.match(src, /sportsStatus/);
  assert.match(src, /sportsGeneratedAt/);
  // Live Take must not callService when the Take guard fires.
  assert.match(
    src,
    /_sendPlan\(\)[\s\S]*takeBlockReason\([\s\S]*callService/
  );
});

test("panel shell prefers free encoders and confirms leftover TVs keep the retuned box", () => {
  const src = readPanelSource();
  assert.match(src, /data-action=["']clear-room-state["']/);
  assert.match(src, /Clear room state/);
  assert.match(src, /_clearRoomState/);
  assert.match(src, /_gateReuseConfirm/);
  assert.match(src, /reuseConfirmKey/);
  assert.match(src, /leftoverTvsKeepShowingCopy/);
  assert.match(src, /keep showing the retuned program until reassigned/);
  assert.match(src, /still on retuned box/);
  assert.match(src, /Unassigned/);
  assert.match(src, /Still showing last box until reassigned/);
  assert.match(src, /STORAGE_KEY/);
  assert.match(src, /removeItem\(STORAGE_KEY\)/);
  assert.doesNotMatch(src, /turn off/);
  assert.doesNotMatch(src, />Off</);
  assert.doesNotMatch(src, /goes off/);
});

function methodSource(src, name, nextName) {
  const start = src.indexOf(`  ${name}(`);
  const end = src.indexOf(`  ${nextName}(`, start + 1);
  assert.ok(start >= 0 && end > start, `${name} method should exist before ${nextName}`);
  return src.slice(start, end);
}

test("panel shell resolves CSS tokens outside a shadow root", () => {
  const src = readPanelSource();
  // The panel renders into light DOM, so :host never matches and its vars never resolve.
  assert.doesNotMatch(src, /:host\b/);
  assert.doesNotMatch(src, /attachShadow/);
  assert.match(src, /\n\s*panel-health \{(?:\s*--[\w-]+: [^;]+;)*?\s*--cyan: \$\{TOKENS\.accent\}/);
  assert.match(src, /\.routing\s*\{[^}]*--cyan:[^}]*--muted:[^}]*--live:/);
  assert.match(src, /\.routing \.chip\.is-active\s*\{[^}]*background:\s*var\(--cyan\)/);
  assert.match(src, /\.live-commit-toggle\.is-active\s*\{[^}]*background:\s*var\(--live\)/);
  assert.match(src, /Live commit: \$\{active \? "ON" : "OFF"\}/);
});

test("panel shell shows a persistent PRACTICE vs LIVE banner in the header", () => {
  const src = readPanelSource();
  assert.match(src, /from\s+["']\.\/panel-view\.js(\?v=\d+)?["']/);
  assert.match(src, /commitModeBanner\(\{/);
  const header = src.match(/<header class="routing-top">[\s\S]*?<\/header>/);
  assert.ok(header, "routing header should exist");
  assert.match(header[0], /mode-banner is-\$\{banner\.mode\}/);
  assert.match(header[0], /escapeHtml\(banner\.text\)/);
  assert.match(src, /class="routing\$\{banner\.mode === "live" \? " is-live" : ""\}"/);
  assert.match(src, /\.routing \.mode-banner\.is-live\s*\{[^}]*background:\s*var\(--live\)/);
  assert.match(src, /\.routing \.mode-banner\.is-practice\s*\{/);
});

test("panel shell pins Guide, Now, and Sets above the sports rail", () => {
  const src = readPanelSource();
  const rail = methodSource(src, "_renderRail", "_renderReplaceChoices");
  const order = ["rail-pinned", "open-guide", "open-now", "open-sets", "rail-sports", "select-sport"].map(
    (marker) => rail.indexOf(marker)
  );
  for (const index of order) assert.ok(index >= 0, "rail marker missing");
  assert.deepEqual([...order].sort((a, b) => a - b), order, "Guide/Now/Sets must render before sports");
  assert.match(src, /\.rail-sports\s*\{[^}]*overflow-y:\s*auto/);
  assert.match(src, /\.rail-pinned\s*\{[^}]*flex:\s*0 0 auto/);
});

test("panel shell falls back to team initials when a logo is missing or fails", () => {
  const src = readPanelSource();
  assert.match(src, /teamInitials/);
  assert.match(src, /_teamLogoHtml\(/);
  assert.equal(
    (src.match(/<img class="team-logo"/g) || []).length,
    1,
    "every team logo goes through _teamLogoHtml"
  );
  assert.match(src, /data-initials="\$\{escapeAttr\(initials\)\}"/);
  assert.match(src, /addEventListener\("error", this\._boundLogoError, true\)/);
  assert.match(src, /removeEventListener\("error", this\._boundLogoError, true\)/);
  assert.match(src, /_failedLogos\.add\(/);
  assert.match(src, /_failedLogos\.has\(/);
  assert.match(src, /team-initials/);
  assert.match(src, /img\.replaceWith\(tile\)/);
});

test("panel shell preserves scroll positions across hass-driven re-renders", () => {
  const src = readPanelSource();
  const render = src.match(/\n  render\(\) \{[\s\S]*?\n  \}\n/);
  assert.ok(render, "render method should exist");
  const body = render[0];
  const skip = body.indexOf("this._renderedHtml");
  const capture = body.indexOf("captureScrollPositions(this)");
  const write = body.indexOf("this.innerHTML = html");
  const restore = body.indexOf("restoreScrollPositions(this, scroll)");
  assert.ok(skip >= 0 && skip < write, "identical HTML must skip the innerHTML wipe");
  assert.ok(capture >= 0 && capture < write, "scroll must be captured before innerHTML");
  assert.ok(restore > write, "scroll must be restored after innerHTML");
  for (const key of ["rail-sports", "displays:", "summary", "league-chips:"]) {
    assert.ok(src.includes(`data-scroll-key="${key}`), `missing scroll key ${key}`);
  }
  assert.match(src, /data-scroll-key="\$\{escapeAttr\(this\._sourcesScrollKey\(\)\)\}"/);
});

test("panel shell loads guide EPG feed and renders now/next columns", () => {
  const src = readPanelSource();
  assert.match(src, /guide_epg\.json/);
  assert.match(src, /guide_channels\.json/);
  assert.match(src, /tvpassport:5960D/);
  assert.match(src, /mergeGuideWithEpg/);
  assert.match(src, /guide unavailable|Guide listings unavailable/i);
  assert.match(src, /nowTitle|Now/);
  assert.match(src, /nextTitle|Next/);
});
