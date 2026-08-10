# AVAccess Route Planner Track A Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace whole-TV-set Preset 2/3 behavior with striped multi-program group planning, free-encoder adhoc allocation, slot-aware occupancy, and dry-run `RoutePlan` summary in the bartender panel (no live UDP/IR).

**Architecture:** Add a pure `route-planner.js` that builds `RoutePlan` objects from group mode + selected programs + busy encoders. Extend `assignment-store.js` to persist slot/encoder occupancy from applied plans. Reshape `panel-health.js` so Preset 2/3 is group-first → multi-program picker → dry-run Send. Track B/C are out of scope.

**Tech Stack:** Home Assistant `panel_custom` ES modules, vanilla Custom Elements, Node `node:test`, existing `validate_panels.py` / pytest.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-10-avaccess-route-planner-design.md` (Track A only)
- Accent color only: `#0e7490`
- Radii: `8px`–`10px`
- TVs: integers `1`–`35`
- Encoders: `ENC-01` … `ENC-10` (ENC-10 spare eligible for adhoc)
- Preset 1: one program → `ENC-01` → all 35 TVs
- Preset 2: up to 4 programs; striped with `N=4`; unused slots omitted
- Preset 3: up to 9 programs; striped with `N=9`; unused slots omitted
- Adhoc: claim lowest-index free encoder; error if none free
- Commit mode for Track A: always `dry_run` (`tune`/`udp` may be null)
- Custom element name remains `panel-health`
- Bump `module_url` on UI ship (currently `?v=7` → `?v=8`)
- Do not implement live UDP/IR or EPG now/next in this plan

## File map

| File | Responsibility |
|------|----------------|
| `homeassistant/config/www/panels/route-planner.js` | Striped maps + `buildRoutePlan` |
| `tests/js/route-planner.test.js` | Planner unit tests |
| `homeassistant/config/www/panels/assignment-store.js` | Slot-aware apply/query helpers |
| `tests/js/assignment-store.test.js` | Occupancy / conflict tests |
| `homeassistant/config/www/panels/panel-data.js` | Preset metadata (`programCapacity`, stripe `N`) |
| `tests/js/panel-data.test.js` | Preset metadata assertions |
| `homeassistant/config/www/panels/panel-health.js` | Group-first multi-program UX + dry-run summary |
| `tests/js/panel-shell.test.js` | Source contracts for new actions/copy |
| `homeassistant/config/configuration.yaml` | `module_url` cache bump |
| `README.md` | Operator guide for Groups/Programs |

---

### Task 1: Route planner (striped maps + RoutePlan)

**Files:**
- Create: `homeassistant/config/www/panels/route-planner.js`
- Create: `tests/js/route-planner.test.js`

**Interfaces:**
- Consumes: none
- Produces:
  - `export function stripedTvs(stripeCount, encoderOrdinal)` → `number[]`  
    (`encoderOrdinal` 1-based; TVs `t` where `(t-1) % stripeCount === (encoderOrdinal-1)`)
  - `export function encoderIdForOrdinal(ordinal)` → `"ENC-01"` … `"ENC-10"` (zero-pad to 2)
  - `export function listFreeEncoders(busyEncoderIds, { includeSpare = true } = {})` → `string[]` lowest-first from ENC-01..ENC-09 plus ENC-10 if `includeSpare`
  - `export function buildRoutePlan({ mode, programs, selectedTvs, busyEncoderIds, commit = "dry_run" })` → `RoutePlan`
    - `mode`: `"preset_1" | "preset_2" | "preset_3" | "adhoc"`
    - `programs`: array of `{ kind, id, label, channel, channelNumber? }`
    - `RoutePlan`: `{ mode, commit, slots: Slot[], warnings: string[], error?: string }`
    - `Slot`: `{ index, encoderId, program, tvs, tune, udp, status }` with `tune`/`udp` null in Track A, `status: "planned"`

- [ ] **Step 1: Write the failing Node tests**

```js
// tests/js/route-planner.test.js
import test from "node:test";
import assert from "node:assert/strict";
import {
  stripedTvs,
  buildRoutePlan,
  listFreeEncoders,
} from "../../homeassistant/config/www/panels/route-planner.js";

test("stripedTvs preset 2 maps ENC-01 and ENC-04", () => {
  assert.deepEqual(stripedTvs(4, 1), [1, 5, 9, 13, 17, 21, 25, 29, 33]);
  assert.deepEqual(stripedTvs(4, 4), [4, 8, 12, 16, 20, 24, 28, 32]);
});

test("buildRoutePlan preset_2 assigns up to N programs and omits unused slots", () => {
  const plan = buildRoutePlan({
    mode: "preset_2",
    programs: [
      { kind: "game", id: "g1", label: "Chiefs @ Bills", channel: "FOX", channelNumber: "206" },
      { kind: "game", id: "g2", label: "Eagles @ Cowboys", channel: "CBS", channelNumber: "207" },
    ],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.mode, "preset_2");
  assert.equal(plan.commit, "dry_run");
  assert.equal(plan.slots.length, 2);
  assert.equal(plan.slots[0].encoderId, "ENC-01");
  assert.deepEqual(plan.slots[0].tvs, stripedTvs(4, 1));
  assert.equal(plan.slots[1].encoderId, "ENC-02");
  assert.equal(plan.error, undefined);
});

test("buildRoutePlan preset_2 caps at 4 programs", () => {
  const programs = Array.from({ length: 5 }, (_, i) => ({
    kind: "game",
    id: `g${i}`,
    label: `Game ${i}`,
    channel: "FOX",
  }));
  const plan = buildRoutePlan({
    mode: "preset_2",
    programs,
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.slots.length, 4);
  assert.match(plan.warnings.join(" "), /ignored/i);
});

test("buildRoutePlan adhoc claims lowest free encoder including spare", () => {
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "channel", id: "ch-espn", label: "ESPN", channel: "ESPN", channelNumber: "206" }],
    selectedTvs: [3, 7],
    busyEncoderIds: ["ENC-01", "ENC-02", "ENC-03", "ENC-04", "ENC-05", "ENC-06", "ENC-07", "ENC-08", "ENC-09"],
  });
  assert.equal(plan.slots.length, 1);
  assert.equal(plan.slots[0].encoderId, "ENC-10");
  assert.deepEqual(plan.slots[0].tvs, [3, 7]);
});

test("buildRoutePlan adhoc errors when no free encoders", () => {
  const busy = listFreeEncoders([]);
  const plan = buildRoutePlan({
    mode: "adhoc",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX" }],
    selectedTvs: [1],
    busyEncoderIds: busy,
  });
  assert.equal(plan.slots.length, 0);
  assert.match(plan.error, /No free encoders/i);
});

test("buildRoutePlan preset_1 uses ENC-01 and all TVs", () => {
  const plan = buildRoutePlan({
    mode: "preset_1",
    programs: [{ kind: "game", id: "g1", label: "A @ B", channel: "FOX" }],
    selectedTvs: [],
    busyEncoderIds: [],
  });
  assert.equal(plan.slots.length, 1);
  assert.equal(plan.slots[0].encoderId, "ENC-01");
  assert.equal(plan.slots[0].tvs.length, 35);
});
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `node --test tests/js/route-planner.test.js`  
Expected: FAIL (module not found)

- [ ] **Step 3: Implement minimal planner**

```js
// homeassistant/config/www/panels/route-planner.js
const ALL_ENCODERS = Array.from({ length: 10 }, (_, i) => `ENC-${String(i + 1).padStart(2, "0")}`);

export function stripedTvs(stripeCount, encoderOrdinal) {
  return Array.from({ length: 35 }, (_, i) => i + 1).filter(
    (tv) => (tv - 1) % stripeCount === encoderOrdinal - 1
  );
}

export function encoderIdForOrdinal(ordinal) {
  return `ENC-${String(ordinal).padStart(2, "0")}`;
}

export function listFreeEncoders(busyEncoderIds, { includeSpare = true } = {}) {
  const busy = new Set(busyEncoderIds);
  const pool = includeSpare ? ALL_ENCODERS : ALL_ENCODERS.slice(0, 9);
  return pool.filter((id) => !busy.has(id));
}

function slot(index, encoderId, program, tvs) {
  return {
    index,
    encoderId,
    program,
    tvs: [...tvs].sort((a, b) => a - b),
    tune: program.channelNumber ? { channelNumber: String(program.channelNumber) } : null,
    udp: null,
    status: "planned",
  };
}

export function buildRoutePlan({
  mode,
  programs,
  selectedTvs = [],
  busyEncoderIds = [],
  commit = "dry_run",
}) {
  const warnings = [];
  const list = Array.isArray(programs) ? [...programs] : [];

  if (mode === "preset_1") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    return {
      mode,
      commit,
      slots: [slot(1, "ENC-01", list[0], Array.from({ length: 35 }, (_, i) => i + 1))],
      warnings,
    };
  }

  if (mode === "preset_2" || mode === "preset_3") {
    const n = mode === "preset_2" ? 4 : 9;
    if (list.length === 0) return { mode, commit, slots: [], warnings, error: "No program selected" };
    if (list.length > n) {
      warnings.push(`Ignored ${list.length - n} extra program(s); cap is ${n}`);
    }
    const chosen = list.slice(0, n);
    return {
      mode,
      commit,
      slots: chosen.map((program, i) => slot(i + 1, encoderIdForOrdinal(i + 1), program, stripedTvs(n, i + 1))),
      warnings,
    };
  }

  if (mode === "adhoc") {
    if (!list[0]) return { mode, commit, slots: [], warnings, error: "No program selected" };
    const tvs = [...new Set(selectedTvs)].sort((a, b) => a - b);
    if (tvs.length === 0) return { mode, commit, slots: [], warnings, error: "No TVs selected" };
    const free = listFreeEncoders(busyEncoderIds, { includeSpare: true });
    if (free.length === 0) return { mode, commit, slots: [], warnings, error: "No free encoders" };
    return {
      mode,
      commit,
      slots: [slot(1, free[0], list[0], tvs)],
      warnings,
    };
  }

  return { mode, commit, slots: [], warnings, error: `Unknown mode: ${mode}` };
}
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `node --test tests/js/route-planner.test.js`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/route-planner.js tests/js/route-planner.test.js
git commit -m "feat: add striped route planner for multi-program groups"
```

---

### Task 2: Slot-aware assignment store

**Files:**
- Modify: `homeassistant/config/www/panels/assignment-store.js`
- Modify: `tests/js/assignment-store.test.js`

**Interfaces:**
- Consumes: `RoutePlan.slots` shape from Task 1
- Produces (additions; keep existing exports working):
  - `export function createEmptyOccupancy()` → `{ byEncoder: {}, byTv: {} }` optional helper OR derive from assignments
  - Prefer extending routes: each applied slot stored under `routeId = encoderId` (or `${encoderId}:${program.id}`) with `{ encoderId, kind, label, channel, tvs, updatedAt, programId }`
  - `export function applyRoutePlan(assignments, plan)` — for each slot, apply as an assignment keyed by `encoderId`; clear overlapping TVs from other encoder routes (same conflict rule as `applyAssignment`)
  - `export function listBusyEncoderIds(assignments)` → `string[]` of encoderIds that currently have ≥1 TV
  - Keep `applyAssignment` / `getAssignmentForTv` for backward compatibility; `getAssignmentForTv` should still resolve after `applyRoutePlan`

- [ ] **Step 1: Write failing tests**

```js
import test from "node:test";
import assert from "node:assert/strict";
import {
  applyRoutePlan,
  listBusyEncoderIds,
  getAssignmentForTv,
  createEmptyAssignments,
} from "../../homeassistant/config/www/panels/assignment-store.js";

test("applyRoutePlan stores encoder slots and clears overlapping TVs", () => {
  let assignments = createEmptyAssignments();
  assignments = applyRoutePlan(assignments, {
    mode: "preset_2",
    commit: "dry_run",
    slots: [
      {
        index: 1,
        encoderId: "ENC-01",
        program: { kind: "game", id: "g1", label: "A @ B", channel: "FOX" },
        tvs: [1, 5, 9],
        tune: null,
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
  });
  assert.deepEqual(assignments["ENC-01"].tvs, [1, 5, 9]);
  assert.equal(listBusyEncoderIds(assignments).includes("ENC-01"), true);

  assignments = applyRoutePlan(assignments, {
    mode: "adhoc",
    commit: "dry_run",
    slots: [
      {
        index: 1,
        encoderId: "ENC-02",
        program: { kind: "game", id: "g2", label: "C @ D", channel: "CBS" },
        tvs: [5, 6],
        tune: null,
        udp: null,
        status: "planned",
      },
    ],
    warnings: [],
  });
  assert.deepEqual(assignments["ENC-01"].tvs, [1, 9]);
  assert.deepEqual(assignments["ENC-02"].tvs, [5, 6]);
  assert.equal(getAssignmentForTv(assignments, 5).encoderId ?? getAssignmentForTv(assignments, 5).routeId, "ENC-02");
});

test("applyRoutePlan no-ops when plan has error", () => {
  const before = createEmptyAssignments();
  const after = applyRoutePlan(before, {
    mode: "adhoc",
    commit: "dry_run",
    slots: [],
    warnings: [],
    error: "No free encoders",
  });
  assert.deepEqual(after, before);
});
```

- [ ] **Step 2: Run to FAIL**

Run: `node --test tests/js/assignment-store.test.js`  
Expected: FAIL on missing `applyRoutePlan`

- [ ] **Step 3: Implement**

```js
export function listBusyEncoderIds(assignments) {
  return Object.entries(assignments)
    .filter(([, route]) => (route.tvs?.length ?? 0) > 0)
    .map(([routeId, route]) => route.encoderId ?? routeId)
    .sort();
}

export function applyRoutePlan(assignments, plan) {
  if (!plan || plan.error || !Array.isArray(plan.slots) || plan.slots.length === 0) {
    return assignments;
  }
  let next = assignments;
  for (const s of plan.slots) {
    next = applyAssignment(next, {
      routeId: s.encoderId,
      kind: s.program.kind,
      sportId: s.program.sportId ?? null,
      label: s.program.label,
      channel: s.program.channel,
      presetId: plan.mode,
      tvs: s.tvs,
    });
    next[s.encoderId] = {
      ...next[s.encoderId],
      encoderId: s.encoderId,
      programId: s.program.id,
    };
  }
  return next;
}
```

- [ ] **Step 4: Run full store + planner tests**

Run: `node --test tests/js/assignment-store.test.js tests/js/route-planner.test.js`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/assignment-store.js tests/js/assignment-store.test.js
git commit -m "feat: apply RoutePlan slots into encoder occupancy store"
```

---

### Task 3: Preset metadata in panel-data

**Files:**
- Modify: `homeassistant/config/www/panels/panel-data.js`
- Modify: `tests/js/panel-data.test.js`

**Interfaces:**
- Consumes: none
- Produces: each preset includes:
  - `mode`: `"preset_1" | "preset_2" | "preset_3"`
  - `programCapacity`: `1 | 4 | 9`
  - `stripeCount`: `null | 4 | 9`
  - Keep `id` values `1_all` / `2_four_programs` / `3_nine_programs`
  - Remove reliance on contiguous `blocks` for Send semantics; either delete `blocks` or leave unused — **delete `blocks`** to avoid drift
  - Update descriptions to striped/multi-program language

- [ ] **Step 1: Write failing test**

```js
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
```

- [ ] **Step 2: Run to FAIL**

Run: `node --test tests/js/panel-data.test.js`  
Expected: FAIL

- [ ] **Step 3: Update PRESETS**

```js
export const PRESETS = [
  {
    id: "1_all",
    mode: "preset_1",
    label: "Preset 1 — ALL",
    shortLabel: "ALL",
    description: "One program on ENC-01 → all 35 TVs",
    programCapacity: 1,
    stripeCount: null,
    tvs: range(1, 35),
  },
  {
    id: "2_four_programs",
    mode: "preset_2",
    label: "Preset 2 — 4 Programs",
    shortLabel: "4 Prog",
    description: "Pick up to 4 programs; striped across ENC-01..04",
    programCapacity: 4,
    stripeCount: 4,
    tvs: range(1, 35),
  },
  {
    id: "3_nine_programs",
    mode: "preset_3",
    label: "Preset 3 — 9 Programs",
    shortLabel: "9 Prog",
    description: "Pick up to 9 programs; striped across ENC-01..09",
    programCapacity: 9,
    stripeCount: 9,
    tvs: range(1, 35),
  },
];
```

- [ ] **Step 4: Run tests**

Run: `node --test tests/js/panel-data.test.js`  
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-data.js tests/js/panel-data.test.js
git commit -m "feat: add programCapacity and stripe metadata to presets"
```

---

### Task 4: Panel UX — group-first multi-program + dry-run

**Files:**
- Modify: `homeassistant/config/www/panels/panel-health.js`
- Modify: `tests/js/panel-shell.test.js`
- Modify: `homeassistant/config/configuration.yaml` (bump to `?v=8`)

**Interfaces:**
- Consumes: `buildRoutePlan`, `listBusyEncoderIds`, `applyRoutePlan`, `PRESETS`, existing sports/guide data
- Produces UI state additions:
  - `groupMode`: `"preset_1" | "preset_2" | "preset_3" | "adhoc" | null`
  - `selectedPrograms`: array (ordered)
  - `lastPlan`: `RoutePlan | null`
  - screen: add `"program-picker"` for Preset 2/3 (group-first)
- Actions:
  - `select-group` (value preset id / mode)
  - `toggle-program` (add/remove in order; ignore when at capacity)
  - `clear-programs`
  - `send-plan` (build plan, if error show it; else `applyRoutePlan`, save, set `lastPlan`, return to browse)
- Behavior:
  - Preset 1 from destination OR from group chip: single program path (existing content-first OK)
  - Preset 2/3: selecting group opens `program-picker` (Sports|Guide exclusive lists); show slot chips `1..N` filled by selection order; striped preview text per filled slot; primary **Dry-run Send**
  - Adhoc: Pick TVs → one program → `send-plan` with `mode: "adhoc"`; disable when plan would error
  - After send, show dry-run summary banner (`lastPlan` slots) briefly or on a dismissible panel
  - Import planner + store helpers; stop using `_applyPreset` as “select all 35 for any preset” for Preset 2/3 Send

- [ ] **Step 1: Add shell contract tests**

```js
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
```

- [ ] **Step 2: Run to FAIL**

Run: `node --test tests/js/panel-shell.test.js`  
Expected: FAIL on new contracts

- [ ] **Step 3: Implement UI wiring (minimal reshaping)**

Implementation notes for the implementer (must follow):
1. Import `{ buildRoutePlan } from "./route-planner.js"` and `{ applyRoutePlan, listBusyEncoderIds }` from `./assignment-store.js`.
2. Extend `_state` with `groupMode`, `selectedPrograms`, `lastPlan`.
3. Add screen branch `_renderProgramPickerScreen()` with:
   - heading from active preset label
   - ordered slot strip (`Slot 1: …` / empty)
   - exclusive Sports|Guide content lists whose cards use `toggle-program` instead of immediate destination for group modes 2/3
   - disabled `send-plan` when `selectedPrograms.length === 0` or when a speculative `buildRoutePlan` returns `error`
4. Group entry: from TVs browse / destination Presets mode, `select-group` with preset id sets `groupMode` from `preset.mode`; if capacity > 1 → `screen: "program-picker"` and clear `selectedPrograms`; if capacity === 1 keep single-content destination flow.
5. `_sendPlan()`:
   ```js
   const plan = buildRoutePlan({
     mode: this._state.groupMode,
     programs: this._state.selectedPrograms,
     selectedTvs: this._state.selectedTvs,
     busyEncoderIds: listBusyEncoderIds(this._assignments),
     commit: "dry_run",
   });
   if (plan.error) {
     this._setState({ lastPlan: plan });
     return;
   }
   const assignments = applyRoutePlan(this._assignments, plan);
   saveAssignments(this._storage(), STORAGE_KEY, assignments);
   this._assignments = assignments;
   this._setState({
     lastPlan: plan,
     selectedPrograms: [],
     screen: this._browseScreenForContent(),
   });
   ```
6. Render a dry-run summary when `lastPlan` is set (slot lines + warnings/error).
7. Keep Graphite + Cyan tokens; no second accent.
8. Bump `configuration.yaml` `module_url` to `?v=8`.

- [ ] **Step 4: Run automated checks**

```bash
node --test tests/js/*.test.js
.venv/bin/python -m pytest tests/test_validate_panels.py -q
bash scripts/run_ha_panel_validation.sh
```

Expected: all PASS

- [ ] **Step 5: Commit**

```bash
git add homeassistant/config/www/panels/panel-health.js tests/js/panel-shell.test.js homeassistant/config/configuration.yaml
git commit -m "feat: group-first multi-program picker with dry-run RoutePlan"
```

---

### Task 5: README operator rewrite + GUI smoke

**Files:**
- Modify: `README.md`
- Artifacts (optional): `/opt/cursor/artifacts/track_a_dry_run_*.png` if computer-use available

**Interfaces:**
- Consumes: shipped Track A UI
- Produces: accurate operator docs (no claims of live UDP/IR or EPG)

- [ ] **Step 1: Rewrite Goals + Operator guide sections**

Document:
- Preset 1 = one program → all TVs on ENC-01
- Preset 2/3 = pick up to 4/9 programs; striped TV assignment; unused encoders unchanged
- Pick TVs = adhoc free encoder; error if none free
- Send in Track A is **dry-run** (plan + local occupancy only)
- Cache `?v=8`

Remove/replace language that says Preset 2/3 are “encoder blocks” filled as all-TV shortcuts.

- [ ] **Step 2: Manual GUI smoke (computer-use if available)**

Checklist:
1. Select Preset 2 → pick 2 games → Dry-run Send → summary shows ENC-01/02 striped TV lists  
2. Pick TVs with all ENC-01..10 busy (simulate via prior plans) → error “No free encoders”  
3. Preset 1 still single-program path  
4. No live network calls required

- [ ] **Step 3: Commit docs**

```bash
git add README.md
git commit -m "docs: document striped multi-program dry-run group flows"
git push -u origin HEAD
```

---

## Spec coverage check (Track A)

| Spec requirement | Task |
|------------------|------|
| Striped maps Preset 2/3 | 1 |
| Up to N programs; unused omitted | 1, 4 |
| Cap and ignore extras | 1, 4 |
| Preset 1 ENC-01 all TVs | 1, 4 |
| Adhoc free encoder / fail if none | 1, 4 |
| Slot-aware occupancy | 2 |
| Group-first multi-program UX | 4 |
| Dry-run summary | 4 |
| Language / README | 3, 5 |
| No live UDP/IR / no EPG | all (explicit non-scope) |

## Placeholder scan

No TBD/TODO steps; commands and interfaces specified.

## Type consistency

- `buildRoutePlan` / `applyRoutePlan` / `listBusyEncoderIds` names shared across Tasks 1–4
- Preset `mode` strings match planner `mode` values
- Encoder ids always `ENC-XX` zero-padded

## Out of scope (next plans)

- Track B: live commit, inventory, IR/UDP execution  
- Track C: Guide now/next EPG overlay
