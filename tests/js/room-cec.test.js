import test from "node:test";
import assert from "node:assert/strict";
import { cecCallArgs, parseCecReport, roomScreenHtml } from "../../homeassistant/config/www/panels/room-cec.js";

test("cec service args name the script and the selected TV", () => {
  assert.deepEqual(cecCallArgs("up", 12), [
    "script",
    "avaccess_cec",
    { action: "volume-up", tv: "12" },
    undefined,
    true,
    true,
  ]);
  assert.equal(cecCallArgs("power-on", 0)[2].action, "power-on");
});

test("report parser reads the last JSON line from the shell response", () => {
  const report = parseCecReport({
    response: { stdout: 'noise\n{"ok": true, "accepted": 35, "results": []}\n' },
  });
  assert.equal(report.accepted, 35);
});

test("room screen fits 35 TVs and keeps volume on the selected set", () => {
  const html = roomScreenHtml({
    live: true,
    selectedTv: 12,
    marks: { 4: { steps: -1, mute: false }, 12: { steps: 2, mute: false }, 18: { steps: 0, mute: true } },
    bannerText: "LIVE",
    bannerMode: "live",
  });
  assert.equal(html.match(/data-action="room-tv"/g).length, 35);
  assert.match(html, /TV 12/);
  assert.match(html, /\+2 this session/);
  assert.match(html, /data-value="12"[^>]*aria-pressed="true"/);
  assert.match(html, /class="room-tv is-muted"/);
  assert.doesNotMatch(html, /disabled/);
});

test("room controls stay disabled until Live commit is on", () => {
  const html = roomScreenHtml({ live: false, selectedTv: 1 });
  assert.match(html, /Live commit is off/);
  assert.match(html, /data-action="room-power-on"[^>]*disabled/);
  assert.match(html, /data-action="room-vol"[^>]*disabled/);
});
