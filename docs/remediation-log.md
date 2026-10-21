# Remediation Log

**Branch:** `cursor/remediation-2026-10-21-af45` (alias `remediation/2026-10-21`)  
**Rule:** Never merge/push to `main` until Phase 6.

---

## Phase 1 — Plan

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Plan | `docs/remediation-plan.md` |
| Source | `docs/qa/PRE_PROD_QA_REVIEW_RESULTS.md` (+ reliability) |
| Note | Opus/GPT planners hit usage limits; plan authored by coordinator from merged reviews; implementation delegated to first-party models |

**Finding counts (deduplicated):** S0×5 · S1×12 · S2+ packaged · BLOCK-SITE×5  

**WP order:** A ∥ B ∥ C → D → E → F → G → H  

**Next:** Execute WP-A, WP-B, WP-C in parallel.

---

## Phase 1 — Execution

| When | Event |
|------|-------|
| 2026-10-21 | Branch renamed `remediation/2026-10-21` → `cursor/remediation-2026-10-21-af45` (PR tool prefix). Draft PR #11. |
| 2026-10-21 | WP-A/B/C delegated to Grok high agents (Opus/GPT usage limited). Agents told to push to new branch name on completion. |
| 2026-10-21 | Usage limits restored. Will re-verify/finish WP-A/B/C with Opus when Grok agents complete; subsequent WPs use Opus/GPT high. Local WIP present (`live-execute.js`, planner prefer-free, Clear room state); JS tests currently 42 pass / 5 fail (incomplete exports). |
| 2026-10-21 | **WP-B** S0-REUSE-BAR / S0-OFF-FICTION / S0-OCCUPANCY-IPAD (partial). Adhoc planner prefers a free encoder when any exist; `singleEncoderForTvs` reuse only if none are free. Explicit `replaceEncoderId` still retunes the chosen box. Panel `_gateReuseConfirm` blocks Take until Confirm when `replaced.offTvs.length > 0`; copy says leftover TVs keep showing the retuned program (not “turn off”). Now empty rows say **Unassigned** / still showing last box. **Clear room state** removes assignment `localStorage` and resets panel occupancy. Patio-after-All-35 test expects ENC-02. `node --test tests/js/*.test.js` → 70 pass / 0 fail. Panel-health also contains concurrent WP-A/C wiring already in the working tree (`live-execute.js`, `takeBlockReason`); executor Python left unstaged for WP-C. BLOCK-SERVER-LEDGER still BLOCKED. |
| 2026-10-21 | **WP-A** S0-SILENT-LIVE / S1-DOUBLE-TAP / S0-OCCUPANCY-IPAD (success-only local occupancy). See section below. |

_(per-WP commit entries follow)_

---

## WP-A — Live feedback & occupancy honesty

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S0-SILENT-LIVE, S1-DOUBLE-TAP, S0-OCCUPANCY-IPAD (success-only local occupancy) |
| Commit | `520bb13` (live-execute + `_sendPlan`; shared panel-health with WP-B). Log commit SHA recorded after this entry. |
| Verify | `node --test tests/js/*.test.js` → 70 pass / 0 fail |

**Changes**
- New `live-execute.js`: HA frontend `callService(..., target, notifyOnError, returnResponse)` with 6th arg `true`.
- Missing report, `report.ok === false`, or `returncode !== 0` → `lastPlan.error` plus warnings; slots left `planned` are marked `error` (exit 2 / empty stdout no longer look like success).
- Live occupancy is applied only after the service returns, and only for slots with `status === "ok"`. Full success is never saved before the live call.
- Dry-run still applies occupancy for training; summary eyebrow is **PRACTICE summary**.
- `_sending` in-flight lock: Take disabled / “Sending…” while awaiting; `send-destination` / `send-plan` / `send-tv-first` ignored if a send is already in flight.

**Not in this WP:** server occupancy ledger (BLOCK-SERVER-LEDGER); Clear room state / free-encoder preference (WP-B); no-channel Live block (WP-C). Panel-health on this branch also contains concurrent WP-B/C wiring already in the working tree.

**Tests:** `tests/js/live-execute.test.js` covers returnResponse arity, exit 1/2/empty, occupancy-after-ok, double-tap lock, and `_sendPlan` source ordering.
