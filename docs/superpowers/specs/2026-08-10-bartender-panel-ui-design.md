# Bartender Sports Routing Panel UI Design

**Date:** 2026-08-10  
**Status:** Spec updated — awaiting re-approval (sports + Spectrum guide)  
**Surface:** Home Assistant custom panel (`panel-health` / `/panel-health`) for iPad Companion

## Problem

The current panel is functionally aligned with AVAccess goals (sport tabs, presets, TVs 1–35) but feels clunky because:

1. **Preset and adhoc TV controls overlap** on one screen, creating decision noise.
2. **Two-column density** forces scanning and scrolling under bar conditions.

## Goals

- Bartender-speed routing on iPad Home Assistant app
- Games listed by sport tab with team names + logos
- Sport coverage: **NFL, CFB, NBA, NHL, MLB, WNBA**
- Groups = project presets (`1_all`, `2_four_programs`, `3_nine_programs`)
- Individuals = TVs **1–35**, multi-select adhoc
- **Spectrum channel guide for ZIP 27403** (Xumo tune numbers/labels)
- Contiguous visual and interaction language across every screen
- One primary action per screen; exclusive destination modes

## Non-goals (this redesign)

- Wiring UDP/Telnet backend (`apply_preset.py`, `route_targets.py`) — keep local assignment model for now
- Live unofficial Spectrum API scraping as a hard dependency (static/configurable lineup file is enough for v1)
- Zone-based mapping UI (`zone_v1`)
- Dark-mode-only theming or multiple accent colors

## Approved interaction model

### Pattern: full-screen destination (Option B)

Primary screens, one active focus:

1. **Games list** — browse sport + pick a game  
2. **Guide** — Spectrum/Xumo channel lineup for ZIP 27403  
3. **Destination** — choose **either** Presets **or** Pick TVs, then Send

Never show presets and the TV grid at the same time.

### Operator flow (games)

1. Open Sports Routing panel  
2. Choose sport tab (**NFL / CFB / NBA / NHL / MLB / WNBA**)  
3. Tap a game card (logos + names + channel/time)  
4. Land on full-screen destination for that game  
5. Toggle mode:
   - **Presets** → tap Preset 1/2/3 (and block chips for 2/3)  
   - **Pick TVs** → multi-select TVs 1–35  
6. Tap **Send to TVs**  
7. Return to games list with updated assignment badge  
8. Repeat for additional games

### Operator flow (guide)

1. Tap **Guide** (same chip row as sports; graphite filled when active)  
2. See Spectrum lineup for **ZIP 27403** (channel number + name + category)  
3. Optional filter/search by name or number  
4. Tap a channel row  
5. Same full-screen destination flow (Presets | Pick TVs → Send)  
6. Assignment label uses channel name/number (e.g. `ESPN · 206`)

### Destination mode rules

| Mode | Shows | Hides |
|------|--------|--------|
| Presets | Preset 1 ALL, Preset 2 (+ blocks A–D), Preset 3 (+ blocks 1–9) | TV grid |
| Pick TVs | TV grid 1–35, Select all / Clear | Preset cards / block chips |

- Preset 1 selects TVs 1–35  
- Preset 2/3 default-preselect block A / block 1 for speed; bartender can change  
- Switching modes clears the inactive mode’s transient selection UI but keeps pending destination until Send or Back  
- Send disabled when zero TVs selected

### Assignment conflict rule

A TV can only show one route (game or guide channel). On Send, selected TVs are removed from any other assignment.

## Approved visual system (contiguous)

### Visual system 3 — Graphite + Cyan

| Token | Value | Use |
|-------|--------|-----|
| Canvas (list/guide) | `#f4f6f8` | Games list + Guide backgrounds |
| Stage (destination) | `#111827` | Full-screen destination background |
| Surface | `#ffffff` / `#1f2937` | Cards on list/guide / destination |
| Accent | `#0e7490` | Selected tabs, selected mode, primary CTA, selected borders |
| Accent muted | `#ecfeff` / `#a5f3fc` | Assignment badges on list |
| Text primary | `#111827` (list/guide) / `#ffffff` (destination) | Titles |
| Text muted | `#6b7280` / `#9ca3af` | Meta (channel, time, hints) |
| Radius | `8px`–`10px` | Tabs, cards, buttons, TV cells, guide rows |
| Type | Single geometric sans (Sora or equivalent) | All screens |

### Contiguous component rules

- One type family and scale on games, guide, and destination  
- One accent color only (`#0e7490`) for all selected/active/primary states  
- Same chip style for sports + Guide (active = cyan fill for sports, graphite fill for Guide to distinguish mode-of-browse without introducing a second accent)  
- Same mode-switch control style on destination (two equal segments)  
- Primary CTA appears only on destination: full-width **Send to TVs**  
- No second accent (no green/amber competing CTAs)  
- Squarer geometry throughout (radius ≤10px)

## Screen specifications

### Screen 1 — Games list

- Header: `AVAccess · iPad` eyebrow + `Sports Routing` title  
- Chip row: **NFL · CFB · NBA · NHL · MLB · WNBA · Guide**  
- When a sport is active, show that sport’s game rows:
  - Away logo + name, `@`, home logo + name  
  - Spectrum/Xumo channel label + tipoff  
  - Status chip: `Unassigned` or compact `TVs …` summary  
- Tap row → destination screen  
- No right-rail assignment editor on this screen

### Screen 2 — Guide (Spectrum ZIP 27403)

- Same header + chip row (Guide active)  
- Subheader: `Spectrum · ZIP 27403 · Xumo`  
- Search field (filters number/name)  
- Rows: **Ch #** (cyan emphasis) · **Name** · **Category** (Sports / Local / etc.)  
- Seed lineup from project channel catalog (aligned with `channels.yaml` / Spectrum Greensboro-area locals such as FOX/CBS/NBC/ABC + sports nets)  
- ZIP is fixed to **27403** for this venue; store as config constant (`spectrumZip: "27403"`) for easy change later  
- Tap row → same destination screen as games

### Screen 3 — Destination

- Back control: `← Games` or `← Guide` (returns to prior browse screen)  
- Title: game matchup **or** channel name  
- Meta: channel · tipoff/category  
- Mode switch: **Presets** | **Pick TVs**  
- Mode body (exclusive content)  
- Sticky/full-width primary: **Send to TVs** (shows count)  
- Secondary: Clear selection

### Live assignments

- Per-row badges on games/guide lists  
- Optional short “Live routes” strip at bottom of browse screens (single column)

## Data model (UI)

```text
spectrumZip = "27403"

sports = [nfl, cfb, nba, nhl, mlb, wnba]

guideChannels[] = {
  id, number, name, category
}

assignments[routeId] = {
  kind: "game" | "channel",
  sportId | null,
  label,
  channel,
  presetId | null,
  tvs: number[],   // 1..35
  updatedAt
}
```

Persist assignments in `localStorage` until backend route/tune scripts are wired.

## Error / empty states

- Empty sport day: “No games listed” with Guide shortcut  
- Guide search miss: “No channels match”  
- Send with 0 TVs: button disabled  
- Logo load failure: initials fallback tile (same radius/size as logo)  
- Storage failure: keep in-memory assignments for session; warn in console only

## Testing

- Keep `scripts/validate_panels.py` + pytest coverage for panel registration  
- Manual GUI validation on iPad-width viewport:
  1. All sport chips switch lists (including NHL/MLB/WNBA)  
  2. Guide shows ZIP 27403 Spectrum/Xumo lineup and search works  
  3. Game or channel tap opens full-screen destination  
  4. Presets and Pick TVs never appear together  
  5. Send updates badges; TV conflicts clear prior routes  
  6. Contiguous tokens: accent/radius/type match on games, guide, destination

## Decisions log

| Decision | Choice |
|----------|--------|
| Overall layout pattern | Option 1 interaction model, **full-screen destination (B)** |
| Visual system | **3 · Graphite + Cyan** |
| Density fix | Remove two-column editor; list-first |
| Confusion fix | Exclusive destination modes |
| Contiguity | Shared tokens/components across screens |
| Sports set | NFL, CFB, NBA, **NHL, MLB, WNBA** |
| Guide | Spectrum/Xumo channel guide for **ZIP 27403** |
| Guide interaction | Same destination Send flow as games |

## Out of scope follow-ups

- Connect Send to HA `shell_command` / `script.avaccess_route_*` + Xumo IR tune  
- Live EPG “now/next” from XMLTV  
- Weekly schedule-driven game labels  
- Zone presets beyond numeric blocks
