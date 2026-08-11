# Spectrum Gold Lineup + Sports-from-EPG Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the favorites seed Guide with the full Spectrum Gold (TV Platinum) dial for ZIP 27403 (no music), and drive Sports Now/Upcoming from `guide_epg.json` programme titles.

**Architecture:** Pull/parse a public Greensboro lineup into `spectrum_lineup_27403.json` + generated JS module; expand `build_guide_epg.py` to emit a `sports` block; panel loads full dial with category chips and reads Sports from the EPG feed (no seed games).

**Tech Stack:** Python 3.12+, existing `xmltv_lib` / `build_guide_epg`, Node `node:test`, HA static `/local/avaccess/`.

## Global Constraints

- Spec: `docs/superpowers/specs/2026-08-10-spectrum-lineup-sports-epg-design.md`
- ZIP `27403`; package key `gold` maps to tvchannelsguide **TV Platinum** column (current Spectrum naming)
- Exclude `category == Music` and Music Choice / Sonic Tap name matches
- Sports v1: sports-category channels only; tabs = title keyword filters
- No league APIs; no Spectrum account API
- Bump panel `?v=14` → `?v=15`
- Do not change RoutePlan / live execute

## File map

| File | Responsibility |
|------|----------------|
| `scripts/avaccess/pull_spectrum_lineup.py` | Parse public markdown/HTML → lineup JSON + JS module |
| `tests/fixtures/spectrum_greensboro_tvchannelsguide.md` | Offline Greensboro snapshot for pull/tests |
| `config/spectrum_lineup_27403.json` | Committed Gold/Platinum snapshot |
| `homeassistant/config/www/avaccess/spectrum_lineup_27403.json` | Served copy |
| `homeassistant/config/www/panels/spectrum-lineup-data.js` | Generated `GUIDE_CHANNELS` export |
| `scripts/avaccess/build_guide_epg.py` | Emit `sports.now` / `sports.upcoming` |
| `config/guide_epg.example.yaml` | Map stubs + `sports_window_hours` |
| `tests/fixtures/guide_sample.xmltv` | Richer sports programmes |
| `homeassistant/config/www/panels/panel-data.js` | Import lineup; sports helpers; remove seed games usage |
| `homeassistant/config/www/panels/panel-health.js` | Category chips; Sports from EPG |
| `tests/test_pull_spectrum_lineup.py`, `tests/test_build_guide_epg.py`, `tests/js/*` | Coverage |
| `README.md` | Operator refresh |

---

### Task 1: Lineup pull + committed snapshot

**Files:**
- Create: `scripts/avaccess/pull_spectrum_lineup.py`
- Create: `tests/fixtures/spectrum_greensboro_tvchannelsguide.md`
- Create: `tests/test_pull_spectrum_lineup.py`
- Create: `config/spectrum_lineup_27403.json`
- Create: `homeassistant/config/www/avaccess/spectrum_lineup_27403.json`
- Create: `homeassistant/config/www/panels/spectrum-lineup-data.js`

**Interfaces:**
- `parse_tvchannelsguide_markdown(text: str, *, package_column: str = "TV Platinum") -> list[dict]`
- `filter_lineup(channels, *, exclude_music=True) -> list[dict]`
- `build_lineup_payload(...) -> dict` with `zip`, `package: "gold"`, `source`, `generatedAt`, `channels[]`
- Each channel: `{id: "ch-{number}", number, name, category, music: false}`
- CLI: `--from-markdown PATH --out JSON --js-out PATH`; optional `--url` (best-effort; CF may block)
- Fail if `< 100` channels or missing ESPN / a local affiliate name

- [ ] **Step 1: Save fixture markdown** from the known Greensboro dump (table + numbers).
- [ ] **Step 2: Failing tests** for Platinum filter, music drop, id shape, validation.
- [ ] **Step 3: Implement pull script + generate committed artifacts.**
- [ ] **Step 4: pytest pass; commit.**

### Task 2: Sports block in build_guide_epg

**Files:**
- Modify: `scripts/avaccess/build_guide_epg.py`
- Modify: `config/guide_epg.example.yaml`
- Modify: `tests/fixtures/guide_sample.xmltv`
- Modify: `tests/test_build_guide_epg.py`

**Interfaces:**
- Config optional: `sports_window_hours: 12`, `sports_channel_numbers: ["16","17",...]` (default: numbers whose lineup category is Sports when `lineup_file` set, else explicit list)
- `classify_sport_key(title: str) -> str` ∈ `nfl|cfb|nba|nhl|other`
- Output `sports: { windowHours, now: [...], upcoming: [...] }`
- Item: `{id, channelNumber, channelName, title, start, end, sportKey}`
- Now vs upcoming: no duplicates; upcoming start within window

- [ ] **Step 1: Extend fixture with CFB/NFL titles on ESPN.**
- [ ] **Step 2: Failing tests for sports extraction + classify.**
- [ ] **Step 3: Implement; pytest pass; commit.**

### Task 3: Panel Guide full dial + Sports from EPG

**Files:**
- Modify: `panel-data.js`, `panel-health.js`, `configuration.yaml` (`?v=15`)
- Modify: `tests/js/panel-data.test.js`, `tests/js/panel-shell.test.js`

**Interfaces:**
- `GUIDE_CHANNELS` from `spectrum-lineup-data.js`
- `SPORT_TABS` = All/NFL/CFB/NBA/NHL/Other (metadata only; no seed games)
- `guideCategories(channels)`, `filterGuideByCategory(channels, cat)`
- `sportsFromEpg(feed, nowMs)` → `{ available, now, upcoming }` using freshness rule
- `filterSportsByTab(items, sportKey)`
- Panel: category chips on Guide; Sport screens list EPG items; `_toProgram` sets `channelNumber` for EPG games
- No fallback to demo seed games when stale

- [ ] **Step 1: JS unit tests for helpers.**
- [ ] **Step 2: Wire panel UI + cache bust.**
- [ ] **Step 3: node tests pass; commit.**

### Task 4: Ops docs + end-to-end verification

**Files:**
- Modify: `README.md`
- Generate demo `guide_epg.json` for HA GUI test (may restore empty shell after, or leave fresh fixture-generated feed for demo)

- [ ] **Step 1: Document pull + EPG refresh.**
- [ ] **Step 2: Run full pytest + node tests.**
- [ ] **Step 3: Build fixture EPG; GUI-verify Guide full dial + Sports games if HA up.**
- [ ] **Step 4: Commit/push; update PR.**

## Spec coverage

| Spec requirement | Task |
|------------------|------|
| Full Gold dial, no music | 1 |
| Correct numbers snapshot | 1 |
| Guide search + category chips | 3 |
| XMLTV now/next map expansion | 2 (stubs in example yaml from lineup sports+) |
| Sports Now + Upcoming from EPG | 2, 3 |
| Keyword tabs | 2, 3 |
| No seed games fallback | 3 |
| Ops refresh docs | 4 |
