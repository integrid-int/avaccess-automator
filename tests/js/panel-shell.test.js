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
  assert.match(src, /from\s+["']\.\/assignment-store\.js["']/);
  assert.match(src, /from\s+["']\.\/panel-data\.js["']/);
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

test("panel shell renders short sports chips and Spectrum ZIP guide label", () => {
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
  assert.match(src, /Spectrum · ZIP \$\{escapeHtml\(SPECTRUM_ZIP\)\} · Xumo/);
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
