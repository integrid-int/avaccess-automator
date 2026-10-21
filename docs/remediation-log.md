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
| 2026-10-21 | Stuck Grok WP-A/C agents abandoned (usage-limit hang). Coordinator took over; WP-A/B/C complete; Opus WP-D/E started. |

_(per-WP commit entries follow)_

---

## WP-A — Live feedback & occupancy honesty

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S0-SILENT-LIVE, S1-DOUBLE-TAP, S0-OCCUPANCY-IPAD (success-only local occupancy) |
| Commit | code `520bb13` (live-execute + `_sendPlan`; shared panel-health with WP-B); log `c6ebd61` |
| Verify | `node --test tests/js/*.test.js` → 70 pass / 0 fail |

**Changes**
- New `live-execute.js`: HA frontend `callService(..., target, notifyOnError, returnResponse)` with 6th arg `true`.
- Missing report, `report.ok === false`, or `returncode !== 0` → `lastPlan.error` plus warnings; slots left `planned` are marked `error` (exit 2 / empty stdout no longer look like success).
- Live occupancy is applied only after the service returns, and only for slots with `status === "ok"`. Full success is never saved before the live call.
- Dry-run still applies occupancy for training; summary eyebrow is **PRACTICE summary**.
- `_sending` in-flight lock: Take disabled / “Sending…” while awaiting; `send-destination` / `send-plan` / `send-tv-first` ignored if a send is already in flight.

**Not in this WP:** server occupancy ledger (BLOCK-SERVER-LEDGER); Clear room state / free-encoder preference (WP-B); no-channel Live block (WP-C). Panel-health on this branch also contains concurrent WP-B/C wiring already in the working tree.

**Tests:** `tests/js/live-execute.test.js` covers returnResponse arity, exit 1/2/empty, occupancy-after-ok, double-tap lock, and `_sendPlan` source ordering.

---

## WP-C — No-channel & demo guard

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S0-NO-CHANNEL, S1-DEMO-FALLBACK (panel), live executor reject |
| Commit | `4b1bab2` (executor); panel guards in `520bb13` |
| Verify | `node --test tests/js` 70/70; `python3 -m unittest tests.test_execute_route_plan_live_tune` 6/6 |

**Changes**
- Panel: `takeBlockReason` / `programsMissingTuneChannel`; sports fallback + stale banners (in `520bb13`).
- Executor: live preflight `_missing_tune_errors`; live slot guard skips UDP when tune missing; CLI exit 2.
- Tests: `tests/test_execute_route_plan_live_tune.py`, JS take-guards.


---

## WP-E — SHEF status + Matrix preset preflight

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S1-SHEF-STATUS, S1-PRESET-PARTIAL |
| Commit | `ab8d938` (SHEF status + verify), `69d33db` (apply_preset preflight) |
| Verify | `python3 -m unittest tests.test_directv_shef tests.test_apply_preset` 41/41; `unittest discover` 66 OK (3 pytest-only modules not importable: PyPI unreachable); pytest-style `test_execute_route_plan`, `test_enrich_plan`, `test_ha_route_wrappers`, `test_directv_sports` via offline pytest shim 42/42 |

**Changes**
- `directv_shef.check_shef_status`: body `status.code` must be 200 and `commandResult` (when present) 0; `shef_get` applies it to every call; `/tv/tune` additionally requires a `status` block. Socket timeouts now raise `SHEF connection failed for <url>` instead of a bare `timed out`.
- `verify_tuned` / `tune_and_verify`: poll `/tv/getTuned` (3 attempts, 0.5 s apart) until major (and minor when given) match. CLI `tune --verify` now exits non-zero on mismatch.
- Executor `send_directv_tune` calls `tune_and_verify`; SHEF `SystemExit` → slot `error` before UDP, other slots continue (exit 1). `verify_tune: false` in `directv.yaml` skips getTuned (documented in `config/directv.example.yaml`; default on).
- `apply_preset.plan_preset_messages`: validates every route (unknown ENC/RX, empty/REPLACE_ME/non-ASCII/whitespace/`:` hostnames, non-list routes, RX on two encoders, preset without routes) and builds all payloads before `send_udp` runs; all errors reported in one `failed preflight; nothing sent` message. Sessions stay sequential over non-empty routes.

**Tests:** `tests/test_directv_shef.py` (status, timeout, verify retry/mismatch, CLI `--verify`, executor end-to-end via fake urlopen: 403 body and getTuned mismatch fail slot with no UDP, other slot still routes); `tests/test_execute_route_plan.py` (403 body → slot error, CLI unverified tune → exit 1, no UDP); new `tests/test_apply_preset.py` (9 cases incl. all example presets passing when commissioned).

**Risk / follow-up:** verify adds up to ~1 s per slot when the H25 is slow to report; with 9 slots plus 4 s SHEF timeouts the 60 s HA shell timeout is still the outer bound. A stale `/config/avaccess/directv_shef.py` copy without `tune_and_verify` fails every live slot closed (AttributeError) — redeploy both files together.

---

## WP-D — Server Live interlock & plan safety

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S1-LIVE-BOOLEAN, S1-B64-SHELL, S1-UDP-TRUST |
| Commit | `482e66a` (interlock, b64, re-enrich, panel, tests), `4589c17` (README / HA_LIVE) |
| Verify | `node --test tests/js/*.test.js` 78/78; `python3 -m unittest tests.test_live_interlock` 23/23; full Python suite (pytest-style modules via offline shim, PyPI unreachable) 151/151. New tests fail on pre-fix code (14 failures + 23 errors Python, 6 JS) and pass on the branch. |

**Changes**
- **S1-LIVE-BOOLEAN:** new `script.avaccess_live_execute` (`mode: single`) in `avaccess_routing.yaml`: runs `shell_command.avaccess_execute_route_plan` with `live: true` only when `input_boolean.avaccess_live_commit` is `on`; otherwise returns a failed report (`returncode` 3, `errors: ["Live Commit is off in Home Assistant. Nothing was sent."]`) without calling the shell. Defense in depth: the shell_command template renders `--live-commit on|off` from `is_state(...)` at call time and `run_execute_route_plan.py` refuses `--live` (exit 3, JSON report) unless it reads `on`, so calling the shell_command directly cannot bypass the boolean.
- Panel: Live Take calls `script.avaccess_live_execute` (returnResponse) instead of the raw shell_command. **Live commit** button calls `input_boolean.turn_on/turn_off`; panel state is re-derived from `hass.states` on every `hass` update, every `render()`, and at the start of `_sendPlan` (one-shot `_liveCommitSynced` removed). Toggle failure shows “Could not change Live commit in Home Assistant.” Cache-bust `panel-health.js?v=32`, `live-execute.js?v=21`.
- **S1-B64-SHELL:** HA shlex-splits templated shell_commands (no shell), so the real risk was argument injection (e.g. `plan_b64="… --inventory /x"`). `plan_b64` / `sets_b64` now render only if they match `^[A-Za-z0-9+/]+={0,2}$` and are single-quoted; otherwise an empty arg. Python decodes strictly (`validate=True`, alphabet regex) and rejects bad payloads (executor exit 2; `save_tv_sets` exits without writing). `allow_abbrev=False` on both parsers so `--liv` cannot alias `--live`.
- **S1-UDP-TRUST:** `execute_plan(live=True)` always runs `enrich_route_plan`, overwriting caller `udp` hostnames from inventory (dry-run unchanged: enrich only when `udp` is null).

**Tests:** `tests/test_live_interlock.py` (live UDP overwrite, strict b64, CLI injection exit 2, `--liv` rejected, `save_tv_sets` rejection, wrapper gate on/off/missing, real `avaccess_routing.yaml` templates rendered with Jinja + `shlex.split` like HA for gate and injection cases, script structure); `tests/js/live-commit-sync.test.js` (instantiates `PanelHealth` with a DOM stub: resync on every hass update, toggle writes `input_boolean`, failure path, Live Take calls the script); `live-execute.test.js` / `panel-shell.test.js` updated for the script path.

**Risk / follow-up:** not exercised on a real HA instance. Script `response_variable` + `stop` needs HA ≥ 2023.7 (compose uses `stable`). With `mode: single`, a second concurrent Live Take from another iPad gets no report and shows a failure (nothing sent). Turning the boolean on now affects every iPad (intended: one shared server truth).
