# Bartender Sports Routing Panel UI Design

**Date:** 2026-08-10  
**Status:** Approved for spec review (Option B + Visual system 3)  
**Surface:** Home Assistant custom panel (`panel-health` / `/panel-health`) for iPad Companion

## Problem

The current panel is functionally aligned with AVAccess goals (sport tabs, presets, TVs 1–35) but feels clunky because:

1. **Preset and adhoc TV controls overlap** on one screen, creating decision noise.
2. **Two-column density** forces scanning and scrolling under bar conditions.

## Goals

- Bartender-speed routing on iPad Home Assistant app
- Games listed by sport tab with team names + logos
- Groups = project presets (`1_all`, `2_four_programs`, `3_nine_programs`)
- Individuals = TVs **1–35**, multi-select adhoc
- Contiguous visual and interaction language across every screen
- One primary action per screen; exclusive destination modes

## Non-goals (this redesign)

- Wiring UDP/Telnet backend (`apply_preset.py`, `route_targets.py`) — keep local assignment model for now
- Zone-based mapping UI (`zone_v1`)
- Dark-mode-only theming or multiple accent colors

## Approved interaction model

### Pattern: full-screen destination (Option B)

Two screens, one active focus:

1. **Games list** — browse sport + pick a game  
2. **Destination** — choose **either** Presets **or** Pick TVs, then Send

Never show presets and the TV grid at the same time.

### Operator flow

1. Open Sports Routing panel  
2. Choose sport tab (NFL / College Football / Basketball)  
3. Tap a game card (logos + names + channel/time)  
4. Land on full-screen destination for that game  
5. Toggle mode:
   - **Presets** → tap Preset 1/2/3 (and block chips for 2/3)  
   - **Pick TVs** → multi-select TVs 1–35  
6. Tap **Send to TVs**  
7. Return to games list with updated assignment badge  
8. Repeat for additional games

### Destination mode rules

| Mode | Shows | Hides |
|------|--------|--------|
| Presets | Preset 1 ALL, Preset 2 (+ blocks A–D), Preset 3 (+ blocks 1–9) | TV grid |
| Pick TVs | TV grid 1–35, Select all / Clear | Preset cards / block chips |

- Preset 1 selects TVs 1–35  
- Preset 2/3 require an encoder block before Send is enabled (unless a default first-block preselect is used — default: preselect block A / block 1 for speed, bartender can change)  
- Switching modes clears the inactive mode’s transient selection UI but keeps pending destination until Send or Back  
- Send disabled when zero TVs selected

### Assignment conflict rule

A TV can only show one game. On Send, selected TVs are removed from any other game’s assignment.

## Approved visual system (contiguous)

### Visual system 3 — Graphite + Cyan

| Token | Value | Use |
|-------|--------|-----|
| Canvas (list) | `#f4f6f8` | Games list background |
| Stage (destination) | `#111827` | Full-screen destination background |
| Surface | `#ffffff` / `#1f2937` | Cards on list / destination |
| Accent | `#0e7490` | Selected tabs, selected mode, primary CTA, selected borders |
| Accent muted | `#ecfeff` / `#a5f3fc` | Assignment badges on list |
| Text primary | `#111827` (list) / `#ffffff` (destination) | Titles |
| Text muted | `#6b7280` / `#9ca3af` | Meta (channel, time, hints) |
| Radius | `8px`–`10px` | Tabs, cards, buttons, TV cells |
| Type | Single geometric sans (Sora or equivalent) | All screens |

### Contiguous component rules

- One type family and scale on both screens  
- One accent color only (`#0e7490`) for all selected/active/primary states  
- Same mode-switch control style on destination (two equal segments)  
- Same sport-chip style on list (filled cyan = active)  
- Primary CTA appears only on destination: full-width **Send to TVs**  
- No second accent (no green/amber competing CTAs)  
- Squarer geometry throughout (avoid pill-heavy UI except where sport chips already use soft radius ≤10px)

## Screen specifications

### Screen 1 — Games list

- Header: `AVAccess · iPad` eyebrow + `Sports Routing` title  
- Sport tabs: NFL / College Football / Basketball  
- Game rows:
  - Away logo + name, `@`, home logo + name  
  - Channel + tipoff  
  - Status chip: `Unassigned` or compact `TVs …` summary  
- Tap row → navigate to destination screen for that game  
- No right-rail assignment editor on this screen

### Screen 2 — Destination

- Back control: `← Games`  
- Title: `{Away} @ {Home}`  
- Meta: channel · tipoff  
- Mode switch: **Presets** | **Pick TVs**  
- Mode body (exclusive content)  
- Sticky/full-width primary: **Send to TVs** (shows count)  
- Secondary: Clear selection

### Live assignments

- Compact summary remains on games list as per-row badges  
- Optional short “Live routes” strip at bottom of list (single column, not a second dense column)

## Data model (UI)

```text
assignments[gameId] = {
  sportId,
  label,
  channel,
  presetId | null,
  tvs: number[],   // 1..35
  updatedAt
}
```

Persist in `localStorage` (existing panel pattern) until backend route scripts are wired.

## Error / empty states

- No game selected: destination not shown (list only)  
- Send with 0 TVs: button disabled  
- Logo load failure: initials fallback tile (same radius/size as logo)  
- Storage failure: keep in-memory assignments for session; warn in console only

## Testing

- Keep `scripts/validate_panels.py` + pytest coverage for panel registration  
- Manual GUI validation on iPad-width viewport:
  1. Sport tab switch updates game list only  
  2. Game tap opens full-screen destination  
  3. Presets and Pick TVs never appear together  
  4. Preset 1 / block selection / adhoc multi-TV Send updates badges  
  5. Contiguous tokens: accent/radius/type match on both screens

## Decisions log

| Decision | Choice |
|----------|--------|
| Overall layout pattern | Option 1 interaction model, **full-screen destination (B)** |
| Visual system | **3 · Graphite + Cyan** |
| Density fix | Remove two-column editor; list-first |
| Confusion fix | Exclusive destination modes |
| Contiguity | Shared tokens/components across screens |

## Out of scope follow-ups

- Connect Send to HA `shell_command` / `script.avaccess_route_*`  
- Weekly schedule-driven game labels  
- Zone presets beyond numeric blocks
