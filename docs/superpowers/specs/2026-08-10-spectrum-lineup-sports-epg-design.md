# Spectrum Gold Full Lineup + Sports-from-EPG Design

**Status:** Approved (pending implementation plan)  
**Date:** 2026-08-10  
**Extends:** Track C Guide EPG in `2026-08-10-avaccess-route-planner-design.md`  
**Does not change:** RoutePlan shape, striped presets, dry-run/live hybrid execute

## Problem

1. **Guide lineup is a tiny favorites seed** in `panel-data.js` (`GUIDE_CHANNELS`). Channel numbers for ZIP 27403 may be wrong vs real Spectrum Greensboro dial, and bartenders cannot browse the full package.
2. **Sports section uses demo seed games** (`SPORTS` in `panel-data.js`) — not what’s actually airing or upcoming on Spectrum sports channels.

Operators need the **full Spectrum TV Gold** channel list for this location (correct numbers, no music) and Sports driven by the **same XMLTV/EPG pipeline** already used for Guide now/next.

## Goals

| Area | Goal |
|------|------|
| Lineup | Full Spectrum **Gold** dial for ZIP **27403**, excluding music channels |
| Guide UI | Browse/search/filter the full dial; tune by correct channel number |
| Listings | Operator-configured XMLTV URL → `guide_epg.json` now/next on mapped channels |
| Sports | **Now** + **Upcoming** derived from EPG titles on sports-category channels (no league APIs) |
| Ops | Public lineup pull → committed snapshot; refreshable; test env works offline |

## Non-goals

- Spectrum unofficial account / My Spectrum API as a hard dependency
- League schedule APIs (ESPN, NFL.com, etc.) or live odds
- Address-exact Spectrum account lineup (public market lineup is the authority for v1)
- Music channels (Music Choice, Sonic Tap, and similar)
- Premium add-ons beyond Gold (RedZone packs, etc.) unless they appear in the Gold public list
- True list virtualization (defer unless >~500 rows is slow in the panel)
- Team logo matching from EPG titles
- Changing RoutePlan / encoder allocation behavior

## Locked decisions

| Topic | Decision |
|-------|----------|
| Package | Spectrum **TV Gold** |
| Location | ZIP **27403** (Greensboro, NC) |
| Lineup scope | **Full** Gold dial, **no music** |
| Lineup source | **Public pull** → JSON artifact; operator may override file |
| Listings source | Operator **XMLTV URL** (existing Track C builder) |
| Sports data | EPG-only: Now + Upcoming on sports-category channels |
| Sports tabs | Keyword filters over titles (All / NFL / CFB / NBA / NHL / Other) — not hard-coded seed leagues |
| Approach | **A**: lineup JSON as channel-number authority; XMLTV for listings; Sports from EPG |

## Architecture

```text
Public Spectrum Gold lineup (Greensboro)
        │
        ▼
pull_spectrum_lineup.py  ──►  config/spectrum_lineup_27403.json
        │                              │
        │                              ├─► panel Guide channels (full dial)
        │                              └─► channel_number_map stubs / name-match hints
        ▼
Operator XMLTV URL (guide_epg.yaml)
        │
        ▼
build_guide_epg.py  ──►  /local/avaccess/guide_epg.json
                           • channels[number].now / .next
                           • sports.now[] / sports.upcoming[]

Bartender panel
  Guide  ← lineup JSON + mergeGuideWithEpg
  Sports ← guide_epg.json sports block (no SPORTS seed games)
  Select channel/game → existing route-planner (unchanged)
```

## §1 Lineup ingest

### Artifact

Committed path: `config/spectrum_lineup_27403.json` (also served or copied under `homeassistant/config/www/avaccess/` if the panel fetches JSON at runtime).

```json
{
  "zip": "27403",
  "package": "gold",
  "source": "https://…",
  "generatedAt": "2026-08-10T00:00:00Z",
  "channels": [
    {
      "id": "ch-2",
      "number": "2",
      "name": "WFMY CBS",
      "category": "Local",
      "music": false
    }
  ]
}
```

### Rules

- `number` is a string (Spectrum dial string as published).
- Stable `id` = `ch-{number}` (if duplicate numbers ever appear, append a short slug — prefer failing the pull instead).
- Drop rows classified as music via source category and/or name denylist (e.g. Music Choice, Sonic Tap, Stingray Music).
- Keep Gold-tier channels only when the source exposes package flags; if the source is Gold-only for that market page, keep all non-music rows.
- Fail the pull if count is implausibly low or core locals/sports nets (e.g. ESPN, local FOX/CBS/NBC/ABC) are missing.

### Script

`scripts/avaccess/pull_spectrum_lineup.py`

- Config/example documents the public Greensboro Spectrum URL and parse expectations.
- Writes the JSON artifact; optional `--check` mode validates an existing file without network.
- HA optional `shell_command` wrapper for refresh (same pattern as Guide EPG refresh).

### Panel wiring

Replace the favorites-only `GUIDE_CHANNELS` seed with the full lineup (either generated ES module from the JSON, or `fetch('/local/avaccess/spectrum_lineup_27403.json')` with a small offline fallback). Tune continues to use `number`.

## §2 Guide UI

- Keep header: `Spectrum · ZIP 27403`.
- Keep search (number, name, category, now/next titles).
- Add **category chips**: All + distinct categories present in the lineup (hide empty).
- Render the **filtered** list only (no virtualization in v1).
- Row: number · name · Now / Next (Track C merge unchanged in spirit).
- Unmapped channels remain listed and tunable; they simply omit now/next titles.
- Global banner “Guide listings unavailable” only when the whole EPG feed is missing/stale (existing freshness rule).
- Music never appears (excluded at ingest).

### EPG map expansion

- Generate `channel_number_map` stubs from every lineup number.
- Prefer automatic XMLTV id match by normalized display-name when unambiguous; leave empty stubs for operator fill otherwise.
- Builder emits now/next for all mapped channels that have programmes.

## §3 Sports from EPG

### Channel set (v1)

Only lineup rows with `category: Sports`. Do not scan locals for game-like titles in v1.

### Output shape

Extend `guide_epg.json` with a `sports` block (same file; one fetch for the panel):

```json
{
  "generatedAt": "…",
  "zipCode": "27403",
  "channels": { "206": { "now": {…}, "next": {…} } },
  "sports": {
    "windowHours": 12,
    "now": [
      {
        "id": "sport-206-…",
        "channelNumber": "206",
        "channelName": "ESPN",
        "title": "College Football: …",
        "start": "ISO-8601",
        "end": "ISO-8601",
        "sportKey": "cfb"
      }
    ],
    "upcoming": [ ]
  }
}
```

- **Now:** programmes currently airing on sports channels.
- **Upcoming:** programmes starting within the next **12 hours** (configurable `windowHours`), sorted by start.
- Do not duplicate a programme in both lists (Now wins if currently airing).

### Tabs / classification

| Tab | `sportKey` | Title keyword heuristics (case-insensitive) |
|-----|------------|-----------------------------------------------|
| All | `*` | all rows |
| NFL | `nfl` | `\bNFL\b`, Sunday Night Football, Monday Night Football, etc. |
| CFB | `cfb` | College Football, NCAA Football |
| NBA | `nba` | `\bNBA\b` |
| NHL | `nhl` | `\bNHL\b` |
| Other | `other` | no keyword match |

Empty tab copy: “No games on Spectrum sports channels in this window.”

### Panel behavior

- Remove reliance on demo `SPORTS[].games` for the live Sports list (tabs become filters over the EPG sports block).
- Row shows title, channel name/number, start/end (or tipoff-style time). No team logos required in v1.
- Selecting a row plans that `channelNumber` via the existing Guide/sports → route-planner path.
- If `sports` is missing or the feed is stale: show the same degrade affordance as Guide; **do not** fall back to seed demo games.

## §4 Ops refresh & success criteria

### Operator flow

1. Run lineup pull → refresh `spectrum_lineup_27403.json` (and panel-served copy if separate).
2. Set XMLTV `source.url` in `guide_epg.yaml`.
3. Refresh map stubs / name-match; fill remaining XMLTV ids.
4. Run `build_guide_epg.py` → `guide_epg.json` including `sports`.
5. Optional HA shell commands + timer for EPG refresh (lineup refresh is infrequent/manual).

### Test env

- Commit the Gold (no music) lineup snapshot so Guide works offline with correct numbers.
- Use fixture XMLTV to prove Sports Now/Upcoming + GUI selection → plan.
- Document that production listings require a live XMLTV URL.

### Success criteria

- Guide shows full Spectrum Gold dial for 27403 with music excluded; numbers match the public snapshot used for ingest.
- Search + category chips work on the full list.
- Now/Next merge works for mapped channels; unmapped rows remain tunable.
- Sports lists EPG-derived Now + Upcoming (not Chiefs/Bills seed demos); empty/degraded when feed stale.
- Selecting a Guide channel or Sports game still dry-runs / live-routes via the existing planner.
- No Spectrum account API; no league schedule APIs.

## Testing

| Layer | What |
|-------|------|
| Unit | Lineup parse/filter (music drop, Gold keep, id/number shape) |
| Unit | Sports extraction (now vs upcoming, window, sportKey, no duplicates) |
| Unit | Guide filter + category chip derivation |
| Integration | `build_guide_epg` fixture → JSON with `channels` + `sports` |
| GUI | Full dial searchable; Sports shows fixture games; select → plan channel number |

## File touch list (expected)

| Path | Role |
|------|------|
| `scripts/avaccess/pull_spectrum_lineup.py` | Public Gold lineup pull |
| `config/spectrum_lineup_27403.json` | Committed snapshot |
| `config/guide_epg.example.yaml` | Map stubs / sports window notes |
| `scripts/avaccess/build_guide_epg.py` | Emit `sports` block |
| `homeassistant/config/www/avaccess/*` | Served lineup + `guide_epg.json` |
| `homeassistant/config/www/panels/panel-data.js` | Load full lineup; Sports from EPG helpers |
| `homeassistant/config/www/panels/panel-health.js` | Category chips; Sports UI wired to EPG |
| `tests/*` | Lineup + sports EPG coverage |
| `README.md` | Operator refresh steps |

## Relationship to prior tracks

- **Track A/B:** unchanged (planner + IR/UDP).
- **Track C:** still XMLTV → `guide_epg.json`; this design widens the channel set and adds Sports extraction.
- Prior non-goal “favorites-only Guide” is **superseded** for lineup breadth; now/next delivery mechanism stays the same.
