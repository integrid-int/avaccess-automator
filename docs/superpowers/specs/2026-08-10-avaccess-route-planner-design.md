# AVAccess Route Planner + Guide Now/Next Design

**Status:** Draft for review  
**Date:** 2026-08-10  
**Supersedes (partial):** bartender panel preset behavior in `2026-08-10-bartender-panel-ui-design.md` where that spec treated Presets 2/3 as whole-TV-set shortcuts. Visual system (Graphite + Cyan) and dual entry paths remain.

## Problem

The bartender Sports Routing panel on `main` is a solid UI shell, but it does not match the original AVAccess operating model:

1. **Groups/Programs** — Preset 2/3 should assign up to 4/9 programs across encoders with a **striped** TV layout, not paint one program onto all 35 TVs.
2. **Encoder routing** — Send does not allocate encoders or emit UDP/IR; there is no free-encoder policy.
3. **Guide** — ZIP 27403 lineup is static; bartenders cannot see **now/next** what’s on.

Related engine pieces exist on `origin/cursor/avaccess-preset-plan` (inventory, `apply_preset.py`, `route_targets.py`, IR, XMLTV sync) but use **contiguous** blocks and are not wired into this panel.

## Goals

| Track | Goal |
|-------|------|
| **A** | Correct group/program model + pure `RoutePlan` planner + dry-run UX |
| **B** | Hybrid execute: dry-run default, live UDP + Xumo IR when inventory validates |
| **C** | Guide shows now/next from XMLTV/EPG on the fixed ZIP 27403 lineup |

## Non-goals

- Stealing/rebalancing busy encoders (no round-robin onto occupied slots)
- Spectrum unofficial API as a hard dependency
- Zone/named room maps (numeric striped only for this design)
- Replacing the Graphite + Cyan bartender visual system
- Live sports-odds or full provider guide browse beyond favorites + now/next

## Locked decisions

| Topic | Decision |
|-------|----------|
| Delivery approach | UI-first vertical slices: **A → B → C** |
| Preset 2/3 selection | Up to N programs (1–4 / 1–9); unused encoder slots **unchanged** |
| TV mapping | **Striped / round-robin** across TVs |
| Adhoc (Pick TVs) | Always claim a **free** encoder; **fail** if none free |
| Guide | Fixed ZIP 27403 favorites + **now/next** overlay |
| Live routing | **Hybrid**: dry-run default + live commit when inventory OK |
| Preset 1 | One program → ENC-01 → all 35 TVs |

## Architecture

```text
Bartender panel (HA custom element)
        │  1..N programs + destination mode
        ▼
route-planner (pure logic; JS in panel, Python twin for live engine)
  • Preset 1 / Preset 2-3 striped / Adhoc free-encoder
  • Output: RoutePlan
        │
        ├─ dry-run → summarize + audit log (default)
        └─ live → IR tune per slot + UDP msg_b_reconnect per encoder

Guide data: channels lineup + EPG now/next (Track C; does not change RoutePlan shape)
```

### RoutePlan (conceptual)

```text
RoutePlan {
  mode: "preset_1" | "preset_2" | "preset_3" | "adhoc"
  commit: "dry_run" | "live"
  slots: [
    {
      index: 1..N          // program slot / encoder ordinal
      encoderId: "ENC-01"
      program: { kind, id, label, channel }
      tvs: number[]        // striped or adhoc set
      tune: { channelNumber } | null
      udp: { txHostname, rxHostnames[] } | null  // filled when inventory present
      status: "planned" | "ok" | "error" | "skipped"
      error?: string
    }
  ]
  warnings: string[]
}
```

## Track A — Group UX + planner

### Operator flows

**Preset 1 — ALL**
1. Pick one game or guide channel (content-first or TV-first with all TVs).
2. Send → one slot: ENC-01 → TVs 1–35.

**Preset 2 — 4 Programs / Preset 3 — 9 Programs**
1. Choose group mode Preset 2 or 3 **first** (not “one game → all TVs”).
2. Multi-select **1..N** programs from Sports and/or Guide (order = slot order: 1st → ENC-01, 2nd → ENC-02, …).
3. Send enabled when ≥1 program selected; cap at N (extra taps ignored or replace last—**cap and ignore**).
4. Unused slots are omitted from the plan and left unchanged on the matrix.
5. Dry-run summary shows each program → encoder → TV list.

Content-first sport/guide browse still exists for **Preset 1** and **adhoc**. For Preset 2/3 the primary path is **group-first → multi-program picker → Send** (dual-path chip row can deep-link into that picker).

**Pick TVs (adhoc)**
1. Select any non-empty TV set.
2. Pick **one** program.
3. Planner claims a free encoder (prefer lowest free id; ENC-10 is eligible as spare).
4. If no free encoder → Send disabled / error: “No free encoders.”

### Striped maps

For Preset *N* ∈ {4, 9}, encoder ordinal `k` (1-based) owns:

```text
tvs = [t for t in 1..35 if (t - 1) % N == (k - 1)]
```

Examples (Preset 2, N=4):
- ENC-01 → 1, 5, 9, 13, 17, 21, 25, 29, 33
- ENC-02 → 2, 6, 10, 14, 18, 22, 26, 30, 34
- ENC-03 → 3, 7, 11, 15, 19, 23, 27, 31, 35
- ENC-04 → 4, 8, 12, 16, 20, 24, 28, 32

### Language

| Avoid (current drift) | Prefer |
|-----------------------|--------|
| Preset 2/3 as “select all 35 TVs” | Group / Programs |
| “4 Prog” with no multi-select | “4 Programs — pick up to 4” |
| Silent blocks data unused | Show slot chips + striped preview |

UI may keep the word **Presets** for Preset 1/2/3 names but must explain Programs + striped coverage.

### Assignment state

Replace “single content → tvs[] only” as the sole truth with **slot-aware** occupancy:

- Which encoder is busy, with what label/channel, covering which TVs.
- Conflict rule for adhoc: claiming TVs moves those RXs to the new free encoder; does **not** steal another encoder’s identity—previous encoder may drop those RXs from its set in the plan.

### Files (Track A, expected)

- `homeassistant/config/www/panels/route-planner.js` (new) — pure planner + striped maps
- `homeassistant/config/www/panels/panel-data.js` — update `PRESETS` (remove misleading contiguous-only behavior as Send semantics; keep metadata)
- `homeassistant/config/www/panels/panel-health.js` — multi-program selection UX, dry-run summary
- `homeassistant/config/www/panels/assignment-store.js` — slot-aware occupancy helpers
- `tests/js/route-planner.test.js` (new)
- README operator section rewrite for Groups/Programs

## Track B — Live routing (hybrid)

### Commit modes

- **Dry-run (default):** build `RoutePlan`, show summary, append audit log; no network side effects.
- **Live:** allowed only when inventory validation passes (every referenced ENC/RX has hostname; broadcast/port configured). Exposed as panel toggle and/or HA `input_boolean`.

### Execution order per slot

1. IR-tune Xumo for that encoder’s source to `channelNumber` (iTach).
2. UDP `:5010` `msg_b_reconnect` for TX → RX hostnames in the slot.
3. Record per-slot status; **continue** on individual failures; surface a final report.

### Engine on `main`

Bring forward and **adapt** from `cursor/avaccess-preset-plan`:

- `config/inventory.example.yaml` — striped `mapping_profiles` (replace contiguous blocks as active profile)
- `scripts/route_targets.py` / apply helper — execute `RoutePlan` slots
- `scripts/send_xumo_ir_itach.py` — tune step
- Free-encoder registry seeded from last successful live plan (Telnet truth optional later)

### Out of scope for B

- Occupied-encoder steal / round-robin rebalance  
- Automatic discovery replacing filled inventory  
- Multiview products

## Track C — Guide now/next

### Data

- Keep fixed Spectrum/Xumo favorites for ZIP **27403**.
- Overlay **now** and **next** from XMLTV/EPG (HA EPG entities or JSON produced by sync job).
- Row shape: `Ch # · Name · Now · Next`.

### Panel behavior

- Search matches number, name, and now/next titles.
- If EPG stale/missing: still list channels; show muted “guide unavailable.”
- Guide does not replace sport chips; sports lists remain a separate surface.

### Delivery

- Panel reads a small JSON/API or HA-templated feed refreshed on a timer.
- No change to `RoutePlan` structure beyond using channel numbers already on guide rows.

## Phased delivery

| Phase | Track | Done when |
|-------|-------|-----------|
| 1 | A | Multi-program Preset 2/3 + striped planner tests green; dry-run summary in UI; README language fixed |
| 2 | B | Live commit executes IR+UDP from `RoutePlan` with hybrid toggle; inventory example striped; failure report |
| 3 | C | Guide rows show now/next; search includes titles; graceful degrade without EPG |

Each phase gets its own implementation plan under `docs/superpowers/plans/` after this spec is approved.

## Testing strategy

- **A:** Node tests for striped maps, up-to-N slots, free-encoder claim/fail, unused slots omitted.
- **B:** Planner → command payload golden tests; optional offline dry-run integration; live tests gated on inventory.
- **C:** Fixture EPG → row rendering + search; stale-EPG fallback test.
- Keep existing panel validator/pytest green; bump `module_url` cache on UI ships.

## Risks

| Risk | Mitigation |
|------|------------|
| Contiguous inventory on preset-plan branch confuses implementers | Spec + inventory profile explicitly striped; delete/replace contiguous as active |
| Free-encoder truth drifts from hardware | Start from last live plan; document manual sync; Telnet status later |
| Multi-program UX clutter on iPad | Ordered slot chips + compact striped preview; exclusive modes retained |
| EPG source variance | Favorites lineup always works; now/next progressive enhancement |

## Open questions (non-blocking)

- Exact IR settle delay between digit sends (inherit iTach docs defaults).
- Whether Preset 1 should also offer an explicit “keep other encoders unchanged” note in UI (behavior already: only ENC-01 planned).
- Preferred EPG integration in HA (XMLTV sensor vs generated JSON) — choose during Track C plan.

## Approval

Design sections approved in brainstorming (architecture, Track A, Track B, Track C).  
Awaiting review of this written spec before implementation plans.
