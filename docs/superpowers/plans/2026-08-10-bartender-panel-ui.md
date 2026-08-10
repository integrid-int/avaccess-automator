# Bartender Sports Routing Panel UI Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Rebuild the Home Assistant `panel-health` custom panel into the approved iPad bartender Sports Routing UI with dual entry paths, Spectrum ZIP 27403 guide, and contiguous Graphite + Cyan design.

**Architecture:** Keep a thin HA custom element entrypoint (`panel-health.js`) that imports pure data + assignment-store modules from `/local/panels/`. UI is a single-focus screen state machine (`browse-sport` | `browse-guide` | `browse-tvs` | `destination` | `content-picker`) with exclusive mode switches. Assignments persist in `localStorage`; no backend route wiring in this plan.

**Tech Stack:** Home Assistant `panel_custom` ES module, vanilla Custom Elements, Node built-in test runner (`node --test`) for pure store logic, existing Python `validate_panels.py` / pytest for registration checks.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-10-bartender-panel-ui-design.md`
- Accent color only: `#0e7490` (Graphite + Cyan system)
- Radii: `8px`–`10px`
- Sports chips: NFL, CFB, NBA, NHL, MLB, WNBA
- Guide ZIP: `27403` (Spectrum / Xumo)
- Presets: `1_all`, `2_four_programs`, `3_nine_programs`
- TVs: integers `1`–`35`
- Exclusive modes: never show Presets editor and TV grid together; never show Sports list and Guide list together on the TV-first content step
- Custom element name remains `panel-health` (HA `panel_custom.name`)
- Bump `module_url` cache query on each UI ship (current will become `?v=5` or higher)

## File map

| File | Responsibility |
|------|----------------|
| `homeassistant/config/www/panels/assignment-store.js` | Pure assignment create/conflict/query helpers + localStorage adapter API |
| `homeassistant/config/www/panels/panel-data.js` | Presets, sports/games seed data, Spectrum ZIP 27403 guide channels, tokens |
| `homeassistant/config/www/panels/panel-health.js` | Custom element UI state machine + rendering |
| `tests/js/assignment-store.test.js` | Node tests for store conflict/send rules |
| `homeassistant/config/configuration.yaml` | Cache-bust `module_url` |
| `README.md` | Operator notes for new UI paths |
| `docs/superpowers/specs/2026-08-10-bartender-panel-ui-design.md` | Already approved; do not rewrite unless behavior must change |

---

### Task 1: Assignment store (pure logic + tests)

**Files:**
- Create: `homeassistant/config/www/panels/assignment-store.js`
- Create: `tests/js/assignment-store.test.js`

**Interfaces:**
- Consumes: none
- Produces:
  - `export function createEmptyAssignments()`
  - `export function applyAssignment(assignments, { routeId, kind, sportId, label, channel, presetId, tvs })`
  - `export function getAssignmentForTv(assignments, tv)`
  - `export function loadAssignments(storage, key)`
  - `export function saveAssignments(storage, key, assignments)`

- [ ] **Step 1: Write the failing Node test**

```js
// tests/js/assignment-store.test.js
import test from "node:test";
import assert from "node:assert/strict";
import { applyAssignment, getAssignmentForTv } from "../../homeassistant/config/www/panels/assignment-store.js";

test("applyAssignment clears overlapping TVs from other routes", () => {
  let assignments = {};
  assignments = applyAssignment(assignments, {
    routeId: "game-a",
    kind: "game",
    sportId: "nfl",
    label: "Chiefs @ Bills",
    channel: "FOX",
    presetId: "1_all",
    tvs: [1, 2, 3],
  });
  assignments = applyAssignment(assignments, {
    routeId: "game-b",
    kind: "game",
    sportId: "nfl",
    label: "Eagles @ Cowboys",
    channel: "CBS",
    presetId: null,
    tvs: [3, 4],
  });

  assert.deepEqual(assignments["game-a"].tvs, [1, 2]);
  assert.deepEqual(assignments["game-b"].tvs, [3, 4]);
  assert.equal(getAssignmentForTv(assignments, 3).routeId, "game-b");
});
```

- [ ] **Step 2: Run test to verify it fails**

Run: `node --test tests/js/assignment-store.test.js`  
Expected: FAIL (module not found)

- [ ] **Step 3: Implement minimal store**

```js
// homeassistant/config/www/panels/assignment-store.js
export function createEmptyAssignments() {
  return {};
}

export function applyAssignment(assignments, route) {
  const next = { ...assignments };
  const selected = new Set(route.tvs);
  for (const [routeId, existing] of Object.entries(next)) {
    if (routeId === route.routeId) continue;
    const remaining = existing.tvs.filter((tv) => !selected.has(tv));
    if (remaining.length === 0) delete next[routeId];
    else next[routeId] = { ...existing, tvs: remaining };
  }
  if (!route.tvs.length) {
    delete next[route.routeId];
    return next;
  }
  next[route.routeId] = {
    kind: route.kind,
    sportId: route.sportId ?? null,
    label: route.label,
    channel: route.channel,
    presetId: route.presetId ?? null,
    tvs: [...route.tvs].sort((a, b) => a - b),
    updatedAt: new Date().toISOString(),
  };
  return next;
}

export function getAssignmentForTv(assignments, tv) {
  for (const [routeId, assignment] of Object.entries(assignments)) {
    if (assignment.tvs.includes(tv)) return { routeId, ...assignment };
  }
  return null;
}

export function loadAssignments(storage, key) {
  try {
    const raw = storage.getItem(key);
    return raw ? JSON.parse(raw) : createEmptyAssignments();
  } catch {
    return createEmptyAssignments();
  }
}

export function saveAssignments(storage, key, assignments) {
  storage.setItem(key, JSON.stringify(assignments));
}
```

- [ ] **Step 4: Re-run tests**

Run: `node --test tests/js/assignment-store.test.js`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/assignment-store.js tests/js/assignment-store.test.js
git commit -m "feat: add assignment store with TV conflict clearing"
```

---

### Task 2: Panel data module (sports + Spectrum ZIP 27403 guide)

**Files:**
- Create: `homeassistant/config/www/panels/panel-data.js`
- Create: `tests/js/panel-data.test.js`

**Interfaces:**
- Consumes: none
- Produces:
  - `export const SPECTRUM_ZIP`
  - `export const STORAGE_KEY`
  - `export const TOKENS`
  - `export const PRESETS`
  - `export const SPORTS`
  - `export const GUIDE_CHANNELS`
  - `export function range(start, end)`
  - `export function filterGuideChannels(channels, query)`

- [ ] **Step 1: Write failing data tests**

```js
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
```

- [ ] **Step 2: Run to verify fail**

Run: `node --test tests/js/panel-data.test.js`  
Expected: FAIL module not found

- [ ] **Step 3: Implement `panel-data.js`**

Include at minimum:
- `SPECTRUM_ZIP = "27403"`
- `STORAGE_KEY = "avaccess-bartender-panel-v2"`
- `TOKENS` object with canvas/stage/accent values from the spec
- `PRESETS` with TV lists/blocks matching inventory numeric splits (ALL 1–35; 4 blocks 1–9/10–18/19–27/28–35; 9 blocks of 4/4/4/4/4/4/4/4/3)
- `SPORTS` array with demo games for nfl/cfb/nba/nhl/mlb/wnba (logos via ESPN CDN paths used today)
- `GUIDE_CHANNELS` seeded with Spectrum/Xumo-relevant Greensboro lineup rows used by the project catalog, including locals + sports nets, for example:

```js
export const GUIDE_CHANNELS = [
  { id: "ch-fox", number: "4", name: "WGHP FOX", category: "Local" },
  { id: "ch-cbs", number: "2", name: "WFMY CBS", category: "Local" },
  { id: "ch-nbc", number: "12", name: "WXII NBC", category: "Local" },
  { id: "ch-abc", number: "45", name: "WXLV ABC", category: "Local" },
  { id: "ch-espn", number: "206", name: "ESPN", category: "Sports" },
  { id: "ch-espn2", number: "207", name: "ESPN2", category: "Sports" },
  { id: "ch-fs1", number: "400", name: "FS1", category: "Sports" },
  { id: "ch-tnt", number: "245", name: "TNT", category: "Sports" },
  { id: "ch-nfl-a1", number: "705", name: "NFL Sunday Ticket 1", category: "Sports" },
];
```

```js
export function filterGuideChannels(channels, query) {
  const q = String(query || "").trim().toLowerCase();
  if (!q) return channels;
  return channels.filter(
    (c) => c.number.includes(q) || c.name.toLowerCase().includes(q) || c.category.toLowerCase().includes(q)
  );
}
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/panel-data.test.js`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-data.js tests/js/panel-data.test.js
git commit -m "feat: add bartender panel sports and Spectrum guide data"
```

---

### Task 3: Rebuild panel shell (Graphite + Cyan screen state machine)

**Files:**
- Modify: `homeassistant/config/www/panels/panel-health.js` (replace UI)
- Modify: `homeassistant/config/configuration.yaml` (`module_url` → `?v=5`)

**Interfaces:**
- Consumes: `panel-data.js`, `assignment-store.js`
- Produces: custom element `panel-health` with internal state:
  - `screen`: `browse-sport` | `browse-guide` | `browse-tvs` | `destination` | `content-picker`
  - `sportId`, `guideQuery`, `selectedContent`, `selectedTvs`, `destMode` (`presets`|`tvs`), `contentMode` (`sports`|`guide`), `entryPath` (`content`|`tv`)

- [ ] **Step 1: Write a registration/style smoke assertion via existing validator + a tiny DOM-less render contract test**

Add `tests/js/panel-shell.test.js`:

```js
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
```

- [ ] **Step 2: Run shell test expecting FAIL on missing markers (if old file still present)**

Run: `node --test tests/js/panel-shell.test.js`  
Expected: FAIL until rewrite includes imports/screens/token

- [ ] **Step 3: Rewrite `panel-health.js` shell**

Minimum required behaviors in this task (can stub path handlers with no-ops until Tasks 4–5 fill them):
- Import data/store modules
- Render chip row: sports + Guide + TVs
- Render Graphite + Cyan CSS tokens from `TOKENS`
- Switch `screen` on chip clicks
- Guard `customElements.define`
- Keep `hass` / `panel` setters

Bump config:

```yaml
module_url: /local/panels/panel-health.js?v=5
```

- [ ] **Step 4: Run JS + Python validation**

```bash
node --test tests/js/*.test.js
.venv/bin/python scripts/validate_panels.py --config-dir homeassistant/config
.venv/bin/python -m pytest tests/test_validate_panels.py -q
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-health.js homeassistant/config/configuration.yaml tests/js/panel-shell.test.js
git commit -m "feat: rebuild bartender panel shell with screen state machine"
```

---

### Task 4: Content-first path (sport/guide → destination → send)

**Files:**
- Modify: `homeassistant/config/www/panels/panel-health.js`
- Modify: `tests/js/panel-shell.test.js` (assert key action hooks exist)

**Interfaces:**
- Consumes: `applyAssignment`, `saveAssignments`, `PRESETS`, `SPORTS`, `GUIDE_CHANNELS`, `filterGuideChannels`
- Produces: UI actions
  - `select-sport`, `open-guide`, `select-game`, `select-channel`
  - `set-dest-mode`, `apply-preset`, `toggle-tv`, `send-destination`, `back-browse`

- [ ] **Step 1: Extend shell contract test for content-first markers**

```js
assert.match(src, /data-action=\"send-destination\"/);
assert.match(src, /Presets/);
assert.match(src, /Pick TVs/);
assert.match(src, /Spectrum · ZIP 27403/);
```

- [ ] **Step 2: Run contract test (FAIL until wired)**

Run: `node --test tests/js/panel-shell.test.js`

- [ ] **Step 3: Implement content-first screens**

In `panel-health.js`:
- Sport browse renders games for `sportId`
- Guide browse renders filtered `GUIDE_CHANNELS` with search input bound to `guideQuery`
- Selecting game/channel sets `entryPath = "content"`, `screen = "destination"`, seeds `selectedTvs` from existing assignment if any
- Destination exclusive mode:
  - presets view OR tv grid
  - Send calls `applyAssignment` + `saveAssignments`, then returns to prior browse screen
- Ensure presets and TV grid markup are not both present in the destination body at once

- [ ] **Step 4: Re-run tests + validator**

```bash
node --test tests/js/*.test.js
.venv/bin/python scripts/validate_panels.py --config-dir homeassistant/config
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-health.js tests/js/panel-shell.test.js
git commit -m "feat: implement content-first sport and guide routing flow"
```

---

### Task 5: TV-first path (TVs → content picker → send)

**Files:**
- Modify: `homeassistant/config/www/panels/panel-health.js`
- Modify: `tests/js/panel-shell.test.js`

**Interfaces:**
- Produces actions:
  - `open-tvs`, `set-tv-browse-mode`, `next-choose-content`
  - `set-content-mode`, `select-game`, `select-channel`, `send-tv-first`

- [ ] **Step 1: Add contract assertions**

```js
assert.match(src, /data-action=\"next-choose-content\"/);
assert.match(src, /data-action=\"send-tv-first\"/);
assert.match(src, /Sending to TVs:/);
```

- [ ] **Step 2: Run to FAIL if missing**

Run: `node --test tests/js/panel-shell.test.js`

- [ ] **Step 3: Implement TV-first screens**

- `browse-tvs`:
  - mode switch Presets | Pick TVs
  - occupied TVs indicated without a second brand accent (graphite label/occupancy)
  - selected TVs cyan
  - **Next: Choose content** disabled when `selectedTvs.length === 0`
- `content-picker`:
  - locked summary `Sending to TVs: …`
  - exclusive Sports | Guide mode
  - selecting content + **Send to N TVs** applies assignment with preselected TVs
  - no second TV grid on this screen

- [ ] **Step 4: Run full automated checks**

```bash
node --test tests/js/*.test.js
.venv/bin/python -m pytest tests/test_validate_panels.py -q
bash scripts/run_ha_panel_validation.sh
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-health.js tests/js/panel-shell.test.js
git commit -m "feat: implement TV-first bartender routing path"
```

---

### Task 6: Docs + cache + GUI validation demo

**Files:**
- Modify: `README.md`
- Modify: `homeassistant/config/configuration.yaml` (bump to `?v=6` if Task 3 already shipped `v=5` and later edits need refresh)
- Artifacts: record GUI demo to `/opt/cursor/artifacts/`

- [ ] **Step 1: Update README operator section**

Document:
- Chip row sports + Guide + TVs
- Content-first and TV-first flows
- Spectrum ZIP 27403 guide
- Hard refresh / cache query note

- [ ] **Step 2: Restart HA (or rely on static file serve) and hard-refresh panel**

```bash
# if HA already running against homeassistant/config, bump module_url and restart
.venv/bin/python -m homeassistant --script check_config --config homeassistant/config
```

- [ ] **Step 3: Manual GUI validation checklist (computer-use)**

1. Sport chips NFL…WNBA switch lists  
2. Guide shows ZIP 27403 + search  
3. Content-first Send via Preset 1  
4. Content-first adhoc multi-TV  
5. TV-first: select TVs → pick Guide/Sport → Send  
6. Confirm presets and TV grid never appear together  
7. Confirm Graphite + Cyan tokens on all screens  

- [ ] **Step 4: Save walkthrough artifact**

Save recording/screenshots under `/opt/cursor/artifacts/` with names:
- `bartender_ui_redesign_demo.mp4` (or screenshot set if recorder fails)

- [ ] **Step 5: Commit docs**

```bash
git add README.md homeassistant/config/configuration.yaml
git commit -m "docs: document dual-path bartender panel operator flows"
git push -u origin cursor/homeassistant-test-env-2956
```

---

## Spec coverage check

| Spec requirement | Task |
|------------------|------|
| Full-screen focus / Option B family | 3, 4, 5 |
| Graphite + Cyan contiguous tokens | 2, 3 |
| Exclusive Presets vs Pick TVs | 4, 5 |
| Sports NFL/CFB/NBA/NHL/MLB/WNBA | 2, 4 |
| Spectrum Guide ZIP 27403 | 2, 4, 5 |
| Content-first path | 4 |
| TV-first path | 5 |
| TV conflict clearing | 1, 4, 5 |
| localStorage persistence | 1, 4, 5 |
| Validator/tests + GUI demo | 3, 6 |

## Placeholder scan

No TBD/TODO steps; all commands and interfaces specified.

## Type consistency

- `applyAssignment(assignments, route)` shape reused by both Send actions
- Route IDs: game ids from `SPORTS[*].games[*].id`, channel ids from `GUIDE_CHANNELS[*].id`
- Screen names and action names referenced consistently across Tasks 3–5
