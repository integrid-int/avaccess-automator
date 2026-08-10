# Bartender Sports Routing Panel UI Design

**Date:** 2026-08-10  
**Status:** Approved — implementation plan written  
**Surface:** Home Assistant custom panel (`panel-health` / `/panel-health`) for iPad Companion

## Problem

The current panel is functionally aligned with AVAccess goals (sport tabs, presets, TVs 1–35) but feels clunky because:

1. **Preset and adhoc TV controls overlap** on one screen, creating decision noise.
2. **Two-column density** forces scanning and scrolling under bar conditions.
3. Operators sometimes think **TV-first** (“TV 12 needs a game”) rather than content-first.

## Goals

- Bartender-speed routing on iPad Home Assistant app
- Games listed by sport tab with team names + logos
- Sport coverage: **NFL, CFB, NBA, NHL, MLB, WNBA**
- Groups = project presets (`1_all`, `2_four_programs`, `3_nine_programs`)
- Individuals = TVs **1–35**, multi-select adhoc
- **Dual entry paths:** content-first **or** TV-first
- **Spectrum channel guide for ZIP 27403** (Xumo tune numbers/labels)
- Contiguous visual and interaction language across every screen
- One primary action per screen; exclusive destination modes

## Non-goals (this redesign)

- Wiring UDP/Telnet backend (`apply_preset.py`, `route_targets.py`) — keep local assignment model for now
- Live unofficial Spectrum API scraping as a hard dependency (static/configurable lineup file is enough for v1)
- Zone-based mapping UI (`zone_v1`)
- Dark-mode-only theming or multiple accent colors

## Approved interaction model

### Dual entry paths

| Path | Browse first | Then | Send |
|------|--------------|------|------|
| **Content-first** | Sport game **or** Guide channel | Destination: Presets **or** Pick TVs | Send to TVs |
| **TV-first** | TVs chip → select TV(s) 1–35 | Choose content: sport game **or** Guide channel | Send to N TVs |

Never show presets and the TV grid as competing editors on the same step.

### Top chip row (contiguous)

`NFL · CFB · NBA · NHL · MLB · WNBA · Guide · TVs`

- Sport active → cyan fill  
- Guide / TVs active → graphite fill (browse-mode distinction without a second accent color)

### Path A — Content-first operator flow

1. Choose a sport chip or **Guide**  
2. Tap a game card or channel row  
3. Full-screen destination:
   - Mode **Presets** → Preset 1/2/3 (+ blocks for 2/3)  
   - Mode **Pick TVs** → multi-select 1–35  
4. Tap **Send to TVs**  
5. Return to prior browse list with updated badge

### Path B — TV-first operator flow

1. Tap **TVs** chip  
2. On TV browse screen, use exclusive mode switch:
   - **Pick TVs** → multi-select grid 1–35  
   - **Presets** → Preset 1/2/3 (+ blocks) as quick TV fills  
3. Tap **Next: Choose content** (enabled only when ≥1 TV selected)  
4. Full-screen content picker with exclusive sub-modes:
   - **Sports** → sport chips + game list  
   - **Guide** → ZIP 27403 Spectrum/Xumo list + search  
5. Tap a game or channel  
6. Tap **Send to N TVs** (TVs already chosen — no second TV picker)  
7. Return to TVs browse (or games) with updated occupancy

### Destination / picker mode rules

| Context | Mode A | Mode B |
|---------|--------|--------|
| Content-first destination | Presets | Pick TVs |
| TV-first browse | Presets (fill selection) | Pick TVs |
| TV-first content step | Sports | Guide |

- Preset 1 selects TVs 1–35  
- Preset 2/3 default-preselect block A / block 1; bartender can change  
- Send disabled when zero TVs **or** no content selected (path-dependent)  
- Back targets: `← Games` / `← Guide` / `← TVs` depending on entry path

### Assignment conflict rule

A TV can only show one route (game or guide channel). On Send, selected TVs are removed from any other assignment.

## Approved visual system (contiguous)

### Visual system 3 — Graphite + Cyan

| Token | Value | Use |
|-------|--------|-----|
| Canvas (browse) | `#f4f6f8` | Games / Guide / TVs browse backgrounds |
| Stage (focus) | `#111827` | Destination + content-picker stages |
| Surface | `#ffffff` / `#1f2937` | Cards on browse / stage |
| Accent | `#0e7490` | Selected sports chips, selected modes, primary CTA, selected TVs/borders |
| Accent muted | `#ecfeff` / `#a5f3fc` | Assignment badges |
| Text primary | `#111827` (browse) / `#ffffff` (stage) | Titles |
| Text muted | `#6b7280` / `#9ca3af` | Meta |
| Radius | `8px`–`10px` | Chips, cards, buttons, TV cells, guide rows |
| Type | Single geometric sans (Sora or equivalent) | All screens |

### Contiguous component rules

- One type family and scale on games, guide, TVs, destination, and content picker  
- One accent color only (`#0e7490`) for selected/active/primary states  
- Identical mode-switch control (two equal segments) wherever exclusive modes appear  
- Primary CTA full-width cyan only on commit steps (**Send to TVs** / **Send to N TVs**)  
- No second accent; radius ≤10px throughout

## Screen specifications

### Screen 1 — Games list (sport chip active)

- Header: `AVAccess · iPad` + `Sports Routing`  
- Chip row including Guide + TVs  
- Game rows with logos, names, channel/tipoff, assignment badge  
- Tap → content-first destination

### Screen 2 — Guide (ZIP 27403)

- Subheader: `Spectrum · ZIP 27403 · Xumo`  
- Search by number/name  
- Rows: Ch # · Name · Category  
- Seed from project Spectrum catalog (Greensboro-area locals + sports nets)  
- Config constant: `spectrumZip: "27403"`  
- Tap → content-first destination

### Screen 3 — TVs browse (TV-first entry)

- Subheader: `Select TVs` + occupancy hints (assigned cells use muted amber/neutral occupied styling without introducing a second brand accent — use graphite hatch or label only; selected = cyan)  
- Mode switch: **Presets | Pick TVs**  
- Grid 1–35  
- Primary: **Next: Choose content**

### Screen 4 — Content-first destination

- Back to Games/Guide  
- Title = matchup or channel  
- Mode switch: **Presets | Pick TVs**  
- **Send to TVs**

### Screen 5 — TV-first content picker

- Back to TVs  
- Shows locked summary: `Sending to TVs: 3, 7, 12`  
- Mode switch: **Sports | Guide**  
- Sport chips + list **or** Guide list (exclusive)  
- Selecting an item enables **Send to N TVs**

### Live assignments

- Badges on game/guide rows  
- TV cells show occupied state on TVs browse  
- Optional single-column live routes strip on browse screens

## Data model (UI)

```text
spectrumZip = "27403"

sports = [nfl, cfb, nba, nhl, mlb, wnba]

guideChannels[] = { id, number, name, category }

assignments[routeId] = {
  kind: "game" | "channel",
  sportId | null,
  label,
  channel,
  presetId | null,
  tvs: number[],   // 1..35
  updatedAt
}

uiSession = {
  entryPath: "content" | "tv",
  selectedTvs: number[],
  selectedContentId | null
}
```

Persist assignments in `localStorage` until backend route/tune scripts are wired.

## Error / empty states

- Empty sport day: “No games listed” + shortcuts to Guide / TVs  
- Guide search miss: “No channels match”  
- TV-first with 0 TVs: Next disabled  
- Content-first Send with 0 TVs: Send disabled  
- TV-first Send with no content: Send disabled  
- Logo failure: initials fallback tile  
- Storage failure: session memory only + console warn

## Testing

- Panel validator + pytest remain green  
- Manual GUI (iPad width):
  1. All sport chips including NHL/MLB/WNBA  
  2. Guide ZIP 27403 list + search  
  3. Content-first: game/channel → Presets|TVs → Send  
  4. TV-first: TVs → content Sports|Guide → Send  
  5. Exclusive modes never show both editors at once  
  6. Conflict clearing across paths  
  7. Contiguous tokens across all screens

## Decisions log

| Decision | Choice |
|----------|--------|
| Layout pattern | Full-screen focus steps (Option B family) |
| Visual system | **3 · Graphite + Cyan** |
| Density fix | No two-column editor |
| Confusion fix | Exclusive mode switches |
| Sports set | NFL, CFB, NBA, NHL, MLB, WNBA |
| Guide | Spectrum/Xumo for **ZIP 27403** |
| Entry paths | **Content-first and TV-first** |

## Out of scope follow-ups

- Connect Send to HA route/tune scripts + Xumo IR  
- Live EPG now/next  
- Weekly schedule-driven labels  
- Zone presets beyond numeric blocks
