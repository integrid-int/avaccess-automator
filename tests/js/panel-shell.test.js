import test from "node:test";
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";

test("panel shell imports store/data and defines panel-health once", () => {
  const src = readFileSync(
    new URL("../../homeassistant/config/www/panels/panel-health.js", import.meta.url),
    "utf8"
  );
  assert.match(src, /from\s+["']\.\/assignment-store\.js["']/);
  assert.match(src, /from\s+["']\.\/panel-data\.js["']/);
  assert.match(src, /customElements\.get\(["']panel-health["']\)/);
  assert.match(src, /#0e7490/);
  assert.match(src, /browse-tvs/);
  assert.match(src, /content-picker/);
});

test("panel shell exposes chip actions for sports guide and TVs", () => {
  const src = readFileSync(
    new URL("../../homeassistant/config/www/panels/panel-health.js", import.meta.url),
    "utf8"
  );
  assert.match(src, /data-action=["']open-sport["']/);
  assert.match(src, /data-action=["']open-guide["']/);
  assert.match(src, /data-action=["']open-tvs["']/);
});
