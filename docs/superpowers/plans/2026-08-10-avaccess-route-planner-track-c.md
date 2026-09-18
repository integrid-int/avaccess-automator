# AVAccess Route Planner Track C Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Overlay **now/next** program titles on the fixed ZIP 27403 Spectrum/Xumo Guide lineup in the bartender panel, with search-by-title and graceful degrade when EPG is missing or stale.

**Architecture:** Keep `GUIDE_CHANNELS` as the source of truth for tune numbers. Add a Python job that reads XMLTV and writes `guide_epg.json` keyed by channel number. The panel fetches that JSON on a timer, merges now/next onto Guide rows, and never blocks Guide browsing if the feed is absent/stale. No `RoutePlan` shape changes.

**Tech Stack:** Python 3.12+ (XMLTV parse, reuse patterns from `origin/cursor/avaccess-preset-plan` `sync_weekly_schedule.py`), Node `node:test`, HA static `/local/avaccess/guide_epg.json`, vanilla panel custom element.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-10-avaccess-route-planner-design.md` (Track C)
- Guide ZIP: `27403`; fixed favorites lineup in `panel-data.js` `GUIDE_CHANNELS`
- Row shape: `Ch # · Name · Now · Next`
- Search matches number, name, **and** now/next titles
- Stale/missing EPG: still list channels; muted “guide unavailable”
- Guide does **not** replace sport chips
- EPG delivery: JSON file at `/local/avaccess/guide_epg.json` (not Spectrum unofficial API)
- No change to RoutePlan / Live Send / encoder logic
- Custom element remains `panel-health`
- Bump `module_url` on UI ship (currently `?v=12` → `?v=13`)
- Stale threshold: treat feed as unavailable if `generatedAt` older than **6 hours** OR missing

## File map

| File | Responsibility |
|------|----------------|
| `config/guide_epg.example.yaml` | XMLTV source + channel_number_map for favorites |
| `scripts/avaccess/xmltv_lib.py` | Shared XMLTV fetch/parse helpers |
| `scripts/avaccess/build_guide_epg.py` | Build `guide_epg.json` for favorites |
| `tests/fixtures/guide_sample.xmltv` | Tiny XMLTV fixture |
| `tests/test_build_guide_epg.py` | Now/next selection + JSON shape |
| `homeassistant/config/www/avaccess/guide_epg.json` | Served feed (fixture or generated; may be empty shell) |
| `homeassistant/config/www/panels/panel-data.js` | `mergeGuideEpg`, search includes titles |
| `tests/js/panel-data.test.js` | Merge + filter tests |
| `homeassistant/config/www/panels/panel-health.js` | Fetch feed, render Now/Next, unavailable state |
| `tests/js/panel-shell.test.js` | Source contracts |
| `homeassistant/config/packages/avaccess_routing.yaml` or new `avaccess_guide.yaml` | Optional shell_command + automation to refresh EPG |
| `homeassistant/config/configuration.yaml` | `module_url` bump |
| `README.md` | Operator: configure XMLTV + refresh |

---

### Task 1: XMLTV → guide_epg.json builder

**Files:**
- Create: `config/guide_epg.example.yaml`
- Create: `scripts/avaccess/xmltv_lib.py`
- Create: `scripts/avaccess/build_guide_epg.py`
- Create: `tests/fixtures/guide_sample.xmltv`
- Create: `tests/test_build_guide_epg.py`

**Interfaces:**
- Consumes: XMLTV file/url; guide config mapping Spectrum numbers → XMLTV channel ids
- Produces JSON:

```json
{
  "zip": "27403",
  "generatedAt": "2026-08-10T22:00:00+00:00",
  "channels": {
    "206": {
      "number": "206",
      "now": { "title": "SportsCenter", "start": "...", "stop": "..." },
      "next": { "title": "NFL Live", "start": "...", "stop": "..." }
    }
  }
}
```

- CLI:

```bash
python3 scripts/avaccess/build_guide_epg.py \
  --config config/guide_epg.yaml \
  --out homeassistant/config/www/avaccess/guide_epg.json
```

Config example keys:
- `timezone: America/New_York`
- `zip_code: "27403"`
- `source: { file: tests/fixtures/guide_sample.xmltv }` or `url`
- `channel_number_map:` map `"206"` → XMLTV channel id(s)

Now/next rules at time `now`:
- `now` = program where `start <= now < stop` (or `stop` null → treat as ongoing if start <= now)
- `next` = earliest program with `start >= now` on that channel after current (if now occupies, next is first start >= now.stop or >= now)

Adapt fetch/parse helpers from preset-plan `sync_weekly_schedule.py` (`fetch_xmltv_bytes`, `parse_xmltv_time`, channel/programme walk) into `xmltv_lib.py` — do **not** copy NFL blackout slot logic.

- [ ] **Step 1: Write fixture + failing tests**

```xml
<!-- tests/fixtures/guide_sample.xmltv -->
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE tv SYSTEM "xmltv.dtd">
<tv>
  <channel id="espn.example"><display-name>ESPN</display-name></channel>
  <channel id="fox.example"><display-name>WGHP</display-name></channel>
  <programme start="20260810180000 +0000" stop="20260810190000 +0000" channel="espn.example">
    <title>SportsCenter</title>
  </programme>
  <programme start="20260810190000 +0000" stop="20260810200000 +0000" channel="espn.example">
    <title>NFL Live</title>
  </programme>
  <programme start="20260810170000 +0000" stop="20260810230000 +0000" channel="fox.example">
    <title>Local News</title>
  </programme>
</tv>
```

```python
# tests/test_build_guide_epg.py
from pathlib import Path
from scripts.avaccess.build_guide_epg import build_guide_epg
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]

def test_build_guide_epg_now_next_for_mapped_channels():
    cfg = {
        "timezone": "UTC",
        "zip_code": "27403",
        "source": {"file": str(ROOT / "tests/fixtures/guide_sample.xmltv"), "compression": "none"},
        "channel_number_map": {"206": ["espn.example"], "4": ["fox.example"]},
    }
    now = dt.datetime(2026, 8, 10, 18, 30, tzinfo=dt.timezone.utc)
    out = build_guide_epg(cfg, now=now)
    assert out["zip"] == "27403"
    assert out["channels"]["206"]["now"]["title"] == "SportsCenter"
    assert out["channels"]["206"]["next"]["title"] == "NFL Live"
    assert out["channels"]["4"]["now"]["title"] == "Local News"
```

- [ ] **Step 2: Run FAIL**

Run: `.venv/bin/python -m pytest tests/test_build_guide_epg.py -q`  
Expected: FAIL

- [ ] **Step 3: Implement xmltv_lib + build_guide_epg**

- [ ] **Step 4: PASS + commit**

```bash
git add config/guide_epg.example.yaml scripts/avaccess/xmltv_lib.py scripts/avaccess/build_guide_epg.py \
  tests/fixtures/guide_sample.xmltv tests/test_build_guide_epg.py
git commit -m "feat: build guide_epg.json now/next from XMLTV"
```

---

### Task 2: Panel data merge + search-by-title

**Files:**
- Modify: `homeassistant/config/www/panels/panel-data.js`
- Modify: `tests/js/panel-data.test.js`

**Interfaces:**
- Produces:
  - `export const GUIDE_EPG_STALE_MS = 6 * 60 * 60 * 1000`
  - `export function isGuideEpgFresh(feed, nowMs = Date.now())` → boolean
  - `export function mergeGuideWithEpg(channels, feed, nowMs = Date.now())`  
    → `{ channels: Array<channel & { nowTitle?: string, nextTitle?: string }>, epgAvailable: boolean }`
  - Update `filterGuideChannels(channels, query)` to also match `nowTitle` / `nextTitle` (case-insensitive)

Merge rules:
- If feed missing/null or not fresh → `epgAvailable: false`, channels unchanged (no now/next fields required)
- If fresh → for each guide channel, attach `nowTitle`/`nextTitle` from `feed.channels[number]` when present

- [ ] **Step 1: Failing tests**

```js
import {
  mergeGuideWithEpg,
  filterGuideChannels,
  GUIDE_CHANNELS,
  isGuideEpgFresh,
} from "../../homeassistant/config/www/panels/panel-data.js";

test("mergeGuideWithEpg attaches now/next when feed fresh", () => {
  const nowMs = Date.parse("2026-08-10T18:30:00Z");
  const feed = {
    zip: "27403",
    generatedAt: "2026-08-10T18:00:00Z",
    channels: {
      "206": {
        number: "206",
        now: { title: "SportsCenter" },
        next: { title: "NFL Live" },
      },
    },
  };
  const { channels, epgAvailable } = mergeGuideWithEpg(GUIDE_CHANNELS, feed, nowMs);
  assert.equal(epgAvailable, true);
  const espn = channels.find((c) => c.number === "206");
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

test("filterGuideChannels matches now/next titles", () => {
  const rows = [{ number: "206", name: "ESPN", category: "Sports", nowTitle: "SportsCenter", nextTitle: "NFL Live" }];
  assert.equal(filterGuideChannels(rows, "sportscenter").length, 1);
  assert.equal(filterGuideChannels(rows, "nfl live").length, 1);
});
```

- [ ] **Step 2–4: TDD implement → PASS → commit**

```bash
git add homeassistant/config/www/panels/panel-data.js tests/js/panel-data.test.js
git commit -m "feat: merge guide EPG now/next into channel rows and search"
```

---

### Task 3: Panel UI — fetch feed, render Now/Next, unavailable

**Files:**
- Modify: `homeassistant/config/www/panels/panel-health.js`
- Modify: `tests/js/panel-shell.test.js`
- Create: `homeassistant/config/www/avaccess/guide_epg.json` — start as empty fresh shell OR generated from fixture for demo:

```json
{
  "zip": "27403",
  "generatedAt": "1970-01-01T00:00:00Z",
  "channels": {}
}
```

(Empty + old timestamp → UI shows “guide unavailable” until operator runs builder.)

Optionally also commit a `guide_epg.demo.json` built from the fixture for manual demos; default served file may be the demo if you regenerate `generatedAt` to “now” in Task 5 docs — **prefer empty/stale default** so degrade path is obvious; document how to generate demo.

- Modify: `homeassistant/config/configuration.yaml` → `module_url` `?v=13`

**Interfaces / behavior:**
- State: `guideEpg: null | object`, `guideEpgAvailable: boolean`
- On connect: `fetch('/local/avaccess/guide_epg.json', { cache: 'no-store' })` then merge; refresh every **15 minutes**
- `_renderGuideScreen` / guide options in program-picker + content-picker:
  - Row columns: number · name · **now** · **next** (next can wrap/truncate)
  - If `!guideEpgAvailable`: muted banner “Guide listings unavailable — channel list only”
- Search already uses updated `filterGuideChannels`
- Do not change sport screens

- [ ] **Step 1: Contract tests**

```js
test("panel shell loads guide EPG feed and renders now/next columns", () => {
  const src = readPanelSource();
  assert.match(src, /guide_epg\.json/);
  assert.match(src, /mergeGuideWithEpg/);
  assert.match(src, /guide unavailable|Guide listings unavailable/i);
  assert.match(src, /nowTitle|Now/);
  assert.match(src, /nextTitle|Next/);
});
```

- [ ] **Step 2–4: Implement → full JS + pytest validate_panels + check_config → commit**

```bash
git add homeassistant/config/www/panels/panel-health.js tests/js/panel-shell.test.js \
  homeassistant/config/www/avaccess/guide_epg.json homeassistant/config/configuration.yaml
git commit -m "feat: show Guide now/next from guide_epg.json with degrade banner"
```

---

### Task 4: HA refresh command + README

**Files:**
- Modify: `homeassistant/config/packages/avaccess_routing.yaml` (or create `avaccess_guide.yaml` in packages)
- Modify: `homeassistant/docker-compose.yml` if guide config path needs a mount (reuse `/config/avaccess/config`)
- Modify: `README.md`
- Create: `config/guide_epg.yaml` symlink → `guide_epg.example.yaml` (same pattern as inventory)

**HA additions:**

```yaml
shell_command:
  avaccess_refresh_guide_epg: >-
    python3 /config/avaccess/scripts/build_guide_epg.py
    --config /config/avaccess/config/guide_epg.yaml
    --out /config/www/avaccess/guide_epg.json
```

Optional automation (commented example in README): refresh every hour.

Wrapper: ensure `build_guide_epg.py` is reachable the same way as `execute_route_plan.py` (mounted `scripts/avaccess`).

README must document:
1. Copy `guide_epg.example.yaml` → `guide_epg.yaml` (rm symlink first)
2. Point `source` at XMLTV file/url; fill `channel_number_map` for favorites
3. Run builder / `shell_command.avaccess_refresh_guide_epg`
4. Stale = 6h; banner behavior
5. Track C does not change Live routing

- [ ] **Step 1: Package + symlink + README**
- [ ] **Step 2: check_config PASS**
- [ ] **Step 3: Commit + push**

```bash
git add homeassistant/config/packages config/guide_epg.example.yaml config/guide_epg.yaml \
  homeassistant/docker-compose.yml README.md
git commit -m "docs: document Guide EPG refresh and wire HA shell_command"
git push -u origin HEAD
```

---

## Spec coverage check (Track C)

| Spec requirement | Task |
|------------------|------|
| Fixed ZIP 27403 favorites lineup | 2, 3 (unchanged GUIDE_CHANNELS) |
| Now/next overlay from XMLTV/JSON | 1, 3 |
| Row Ch # · Name · Now · Next | 3 |
| Search includes now/next titles | 2, 3 |
| Graceful degrade if stale/missing | 2, 3 |
| Guide ≠ sports browser | 3 |
| No RoutePlan changes | all |
| Fixture/tests for EPG | 1, 2 |

## Placeholder scan

No TBD steps; XMLTV URL in example may be placeholder by design.

## Type consistency

- Feed key = channel `number` string (e.g. `"206"`)
- Panel fields `nowTitle` / `nextTitle`
- Freshness via `generatedAt` + `GUIDE_EPG_STALE_MS`

## Out of scope

- Spectrum unofficial API scraping  
- Changing sports chip seed schedules  
- Live IR/UDP behavior (Track B already shipped)
