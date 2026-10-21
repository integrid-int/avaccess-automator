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

---

## WP-F — Visual / UX Soft Launch blockers

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S1-VIS-TOKENS, S1-SCROLL-JUMP, S2-LOGO-FALLBACK, S2-RAIL-FOLD |
| Commit | `601c170` (panel, `panel-view.js`, cache bump, tests) |
| Verify | `node --test tests/js/*.test.js` 87/87 (9 new: 4 behavioral in `panel-view.test.js`, 5 source checks in `panel-shell.test.js`). Headless Chrome 1024×768 harness with fake `hass` and the repo's real `sports_schedule.json`: computed colors, rail positions, logo fallback, scroll retention all as below. |

**Changes**
- **S1-VIS-TOKENS:** the panel renders into light DOM (no shadow root), so `:host` never matched and every `var(--…)` was unset. Tokens now live on `panel-health { … }`; `.routing` remaps the light browse tokens to the dark board palette (`--cyan #0b5cab`, `--muted #c8c8c8`, `--surface #1a1a1a`, `--live #b91c1c`) so shared rules (`.plan-warning`, `.tv-toolbar span`) stay legible instead of turning grey-on-black. Active league chip: filled blue with a light inset ring. **Live commit** button reads `Live commit: ON|OFF`; ON is filled red, OFF is outlined.
- **PRACTICE / LIVE banner:** always in the header next to “Bar”. `PRACTICE – TVs will not change` (slate) unless Live commit is on **and** inventory is Live-ready, then `LIVE – TVs WILL change` (red) plus a red top stripe on the board. Same rule as `_sendPlan` (`commitModeBanner` in new `panel-view.js`).
- **S2-LOGO-FALLBACK:** all team logos go through `_teamLogoHtml`. Empty URLs (most of the current DirecTV slate) render an initials tile directly; a capture-phase `error` listener swaps a failed `<img>` for the tile and remembers the URL so later renders skip it.
- **S2-RAIL-FOLD:** rail is `rail-pinned` (Guide, Now, Sets) above `rail-sports` (scrolls on its own). With the current 14-sport slate, Guide used to sit at ~780 px, below the fold on an iPad in landscape; now Sets ends at ~340 px.
- **S1-SCROLL-JUMP:** `render()` builds the HTML first and returns without touching the DOM when it matches the last render (most `hass` pushes). Otherwise it captures `scrollTop/scrollLeft` of `[data-scroll-key]` containers (sources bank, displays bank, rail sports, plan summary, league chips) and restores them after `innerHTML`. Source keys include screen/sport/league/search, so switching lists still opens at the top.
- Cache-bust `panel-health.js?v=33` in `configuration.yaml` and `prepare_ha_staging.py`; new module imported as `panel-view.js?v=1`.

**Browser evidence (harness):** active chip `rgb(11,92,171)`; Live ON toggle and banner `rgb(185,28,28)`; Guide/Now/Sets bottoms 248/294/340 px of a 681 px viewport; sources scrolled to 400 px and rail to 120 px both survive an unchanged and a changed `hass` push (unchanged push keeps the same DOM node); sport switch resets sources to 0; broken URL → `MS` tile, empty URLs → `MTS`/`FIU`, valid image kept; ESPN URLs (no egress in the sandbox) all fell back to initials.

**Not in this WP:** docs still cite `?v=30` (WP-G). Legacy `_render*Screen` methods remain unreachable dead code (not removed, to keep scope). Not checked on a physical iPad / HA Companion.

---

## WP-G — Docs corrections

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S1-MATRIX-CONFUSION, S1-INVENTORY-TRAP, S1-DOCKER-UDP, S0-OFF-FICTION (docs) |
| Commit | `ce04dc8` (docs + staff PDF builder text) |
| Verify | `rg` scan of edited files: no `?v=30`, `Dry-run Send`, `DRY-RUN`, “turn off”/“go off” (except “do not turn off”), `**Off**`, “Swipe the left”, or “bottom of the left”. `python3 -m py_compile scripts/build_staff_pdfs.py` OK. No product code changed; `node --test tests/js/*.test.js` 87/87, `python3 -m unittest discover -s tests` 151 OK. |

**Changes**
- `HA_QUICKSTART.md`: section 2 now `rm -f` + `cp --remove-destination` for inventory, channels, and directv (inventory ships as a symlink to the example; plain `cp` wrote through it). `?v=33`. PRACTICE banner mention.
- `HA_LIVE.md`: `?v=33` everywhere (matches `configuration.yaml` after WP-F); note that panel imports carry their own `?v=`. New “How Live is gated” subsection (`script.avaccess_live_execute`, `mode: single`, shared `input_boolean.avaccess_live_commit`, `--live-commit` defense, UDP re-enrich, SHEF verify, success-only occupancy, Sending… lock). New section 7b **Soft Launch**: leave `REPLACE_ME` in `www/avaccess/inventory.json` to keep Live blocked, boolean off, PRACTICE banner on every iPad, Matrix is always live; first-Live steps incl. **Clear room state** on every iPad (wipes `avaccess-bartender-panel-v2`, keeps TV sets) and single-iPad Live. Section 0 warns that both checked-in compose files are Docker bridge and Live UDP must run on HA OS / host network. Surface table and checklist say which surface is live. Inventory symlink trap explained in section 3.
- `STAFF_TRAINING.md`: PRACTICE / LIVE banners; Matrix has no practice mode; Guide/Now/Sets pinned at top of the rail; **PRACTICE summary** / **Live summary** (not DRY-RUN SUMMARY); Take → Confirm before leftover TVs; leftover TVs keep the retuned program (no turn-off); Now says **Unassigned**; **Clear room state**; Take gray with **Cannot Take: … has no DirecTV channel**; demo/stale sports banners; Sending… and Live ok/error lines; troubleshooting rows. Notes that the screenshots predate the banner and pinned rail.
- `OPERATIONS_GUIDE.md`: Sports Routing screenshots flagged stale; “Which one changes the wall” (Matrix always live SHEF + UDP, contiguous `numeric_v1` presets vs striped Sports Routing); Soft Launch guidance.
- `README.md`: `?v=33`; Take/PRACTICE/LIVE wording replaces Dry-run Send / Live Send; returnResponse + success-only occupancy replaces the “stdout often not returned” note; free-box-first + Confirm; Unassigned / Clear room state; pinned rail; Matrix has no Live gate.
- `scripts/build_staff_pdfs.py` (doc source only): same wording changes so the next rebuild of `STAFF_QUICK_START.pdf` / `STAFF_FULL_GUIDE.pdf` drops the turn-off/Off fiction.

**BLOCKED — PDF rebuild:** `reportlab` is not installed and PyPI is unreachable (`pip install reportlab` SSL EOF; no apt package). `docs/STAFF_QUICK_START.pdf` and `docs/STAFF_FULL_GUIDE.pdf` are **not** rebuilt and still contain the old “turn off” / “Off” / DRY-RUN SUMMARY text. Rebuild with `pip install reportlab && python3 scripts/build_staff_pdfs.py` on a machine with PyPI access. `docs/STAFF_TRAINING.pdf` (legacy combined, `build_staff_training_pdf.py`) and `docs/AVACCESS_OPERATORS_GUIDE.pdf` were not edited; both are already marked superseded/older layout. Staff screenshots (`docs/images/staff/*`) predate the PRACTICE banner, pinned rail, and Unassigned wording; recapture is Phase 7.

**Not in this WP:** README Path A / Path B still describe the older multi-screen flow (destination screen, TVs chip); only button labels were synced. Not checked against a real HA instance.

---

## WP-H — Test hardening

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Findings | S2-TESTS-SHALLOW |
| Commit | `6e5b23d` (Python tests unittest-safe), `fe9232c` (panel-driven JS tests, regex cleanup, reuse-warning period), log commit (this entry + README test commands) |
| Verify | `node --test tests/js/*.test.js` → 100 pass / 0 fail (was 87; 15 new, 2 superseded regex tests removed). `python3 -m unittest discover -s tests -p 'test_*.py' -q` → 151 OK, no import errors (was 86 run + 3 modules failing to import `pytest`; 65 bare `test_*` functions were silently skipped). |

**Python: unittest now runs everything.** `unittest discover` never collected bare `def test_*` functions, so 65 tests in 12 modules (all 20 executor live-path tests in `test_execute_route_plan.py`, plus enrich, inventory_lib, HA wrappers, sports, guide, panels validation) only ran under pytest, which is not installed here or reachable from PyPI. Each module's tests now sit in a `unittest.TestCase` (pytest still collects them). `tmp_path` → `TemporaryDirectory` in `setUp`; `monkeypatch.setattr` → `self.patch` over `unittest.mock.patch`; `capsys` → `redirect_stdout` in `run_main`; `pytest.raises` → `assertRaises`/`assertRaisesRegex` (`excinfo.exception`). Test and assert counts match the originals file by file. Mutation check: disabling `_missing_tune_errors` fails 3 executor tests under plain unittest. The sports Selenium test now closes its local HTTP server socket (`ResourceWarning`).

**JS: the real panel is driven through Take.** New `tests/js/panel-harness.js` stubs `HTMLElement`, `customElements`, and `localStorage` (records write order) so `<panel-health>` can be built, rendered to a string, and sent through `_sendPlan` with a fake `hass.callService`.
- `panel-send.test.js` (8): Live partial failure (exit 1, ENC-01 error / ENC-02 ok) saves only ENC-02, nothing is in storage while the script is pending, and the Live summary shows the error; context-only response (HA dropped `returnResponse`) saves nothing and shows "no report"; second Take / `_sendDestination` / `_sendTvFirst` while in flight makes no second script call and the Take button renders disabled, `aria-busy`, "Sending…"; Live Take of a game with no channel never calls HA; demo fallback blocks Live but allows PRACTICE; boolean switched off after arming makes Take run PRACTICE with zero service calls; patio (TVs 8–10) after All 35 sends ENC-02 with no Confirm step and ENC-01 keeps 32 TVs; no free encoders + shared box shows "Tap Confirm to continue." and the Confirm label first, then sends ENC-03 on the second Take.
- `panel-render.test.js` (7): PRACTICE/LIVE banner text, `data-commit-mode`, and `routing is-live` from rendered HTML (incl. boolean on + inventory not ready → PRACTICE; `render()` re-reads the boolean); rail renders Guide/Now/Sets in `rail-pinned` before every sport in `rail-sports`; unchanged `hass` push skips the `innerHTML` write and a changed push restores scroll of matching keys; demo-fallback and stale sports banners render.
- Removed brittle source regexes these replace: `_sendPlan` body slicing (`live-execute.test.js`), `_sendPlan…takeBlockReason…callService` (`take-guards`, `panel-shell`), header/rail/`render()` method slicing (`panel-shell`). CSS-only checks stay as source regexes.
- **Mutation matrix** (re-introduce pre-fix behavior one at a time, run the new files): 12 of 14 caught: save-before-Live, save-whole-plan, no in-flight lock, no `_sendPlan` Take guard, both channel guards removed, `_sendPlan` trusting the cached flag, reuse-before-free, no Confirm gate, `render()` not resyncing, sports above Guide/Now/Sets, no scroll restore, rebuild on every push. Not caught by the new files: planner-only channel guard removed (the panel guard still blocks; the 4 existing `buildRoutePlan` channel tests catch it), and the banner dropping its inventory check (equivalent mutant: `_state.liveCommit` already folds in readiness on every render).

**Product fix found by the tests:** the reuse warning read "…until reassigned Tap Confirm to continue." (no period). Now "…until reassigned. Tap Confirm to continue.", matching `STAFF_TRAINING.md`. Cache-bust **not** bumped (`panel-health.js?v=33`, cosmetic only); bump with the next panel change.

**Remaining gaps**
- Nothing runs against a real HA frontend: `callService` 6-arg `returnResponse` and the script's `response_variable` are only exercised with fakes (BLOCK-SITE-WALL).
- Multi-iPad occupancy is untested by design (BLOCK-SERVER-LEDGER); tests cover one panel's `localStorage` only.
- Logo fallback (`_onLogoError`, initials swap) is covered only by the WP-F headless Chrome harness, not by `node --test`.
- `_sendDestination`'s non-planner branch (`applyAssignment` with no service call) has no test; it needs `destMode: "presets"` with no `groupMode`, which leaves Take disabled in the UI.
- `live-commit-sync.test.js` still has its own DOM stub; it could move to `panel-harness.js`.
- The converted Python modules were not run under pytest here (no pytest); pytest collects `unittest.TestCase` natively.

---

## Phase 2 — Re-verify, iteration 1 of 5

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| HEAD verified | `94cbb665f4b15aa26696faae4e71223725c2ecf1` (`94cbb66`) |
| Report | `docs/phase2-reverify.md` |
| Verify | `node --test tests/js/*.test.js` → 100 pass / 0 fail. `python3 -m unittest discover -s tests -p 'test_*.py' -q` → 151 OK. Mutation spot-check 4/4 caught. |

**Counts (22 findings-table rows):** PASS **19** · FAIL **1** · BLOCKED **2** · WON'T FIX **0**

- **FAIL — S0-OCCUPANCY-IPAD:** practice Takes still persist occupancy to the Live `localStorage` key, and there is no clear-on-load or clear-on-Live-arm. Manual **Clear room state** is the only mitigation. Proposed fixes F-1a (separate practice store, preferred) and F-1b (tag and drop practice routes when Live arms) are in the report. Single-iPad doc, Clear room state control, and ledger-BLOCKED note are done. The plan's WP-A step 4 prefers keeping practice occupancy, so the coordinator may instead record WON'T FIX with that reason.
- **BLOCKED — S0-OFF-FICTION:** UI and Markdown pass. `STAFF_QUICK_START.pdf` / `STAFF_FULL_GUIDE.pdf` still say "turn off" (`reportlab` still not installable). Recommended F-2: until the PDFs are rebuilt, mark them pending next to every link and point staff to `STAFF_TRAINING.md`.
- **BLOCKED — BLOCK-SITE-\*** (wall, reconnect, broadcast, Sunday channels).
- Still BLOCKED outside the table: BLOCK-SERVER-LEDGER, PDF rebuild, real HA `returnResponse` integration (offline fakes only).
- Minor copy observations, not findings: F-3 (Live commit hint still says "Dry run — Send"), F-4 (unreachable `_renderScreen` path keeps "Dry-run Send").

**Next:** coordinator spawns a fix agent for S0-OCCUPANCY-IPAD (or records WON'T FIX), then Phase 2 iteration 2.

## Fix F-1a / F-2 / F-3 (S0-OCCUPANCY-IPAD)

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Commits | `6280e01` F-1a code + tests, `eca1ec2` F-1a docs, `a9af537` F-3, `71e04b7` F-2 |

- **F-1a:** PRACTICE and Live occupancy are separate `localStorage` stores. PRACTICE reads and writes `avaccess-bartender-panel-practice-v1` (`PRACTICE_STORAGE_KEY`, `panel-data.js`); Live (Live commit on and inventory ready) reads and writes `avaccess-bartender-panel-v2` (`STORAGE_KEY`). `_syncLiveCommitFromHass` → `_syncOccupancyStore` reloads `_assignments` from the target key on a mode change, with no merge, and clears Replace/Confirm choices. `_sendPlan` saves to the key captured before the await, so a Live send that finishes after Live is turned off still lands in the Live store. **Clear room state** removes both keys (TV sets kept). Planner busy encoders and Now follow `_assignments`, so they are mode-specific. Docs: `HA_LIVE.md` 7b and checklist 8c, `README.md`, `OPERATIONS_GUIDE.md` Soft Launch, `STAFF_TRAINING.md`, and the `build_staff_pdfs.py` source text. Cache-bust `panel-health.js?v=34`, `panel-data.js?v=21`.
- **Tests:** 6 new `panel-send.test.js` cases on the real panel: practice Take does not write the Live key; Live Take after practice Takes claims ENC-01 with no Confirm; a full practice room needs Confirm only in PRACTICE; practice Take after a Live Take leaves the Live key unchanged and Live reloads it; in-flight Live send survives a mode flip; Clear room state removes both keys. Harness gains `savedPracticeAssignments()` and `setLiveState()`. Mutations: shared key → 6 fail; Clear skips practice key → 1 fail.
- **F-3:** Live commit hint reads "PRACTICE — Take only plans; TVs do not change" / "LIVE — Take changes the TVs"; tooltip says Take. New `panel-render.test.js` case. Same `?v=34`.
- **F-2:** every `STAFF_QUICK_START.pdf` / `STAFF_FULL_GUIDE.pdf` link in `README.md`, `HA_LIVE.md`, `OPERATIONS_GUIDE.md`, `STAFF_TRAINING.md` says the PDFs are pending rebuild and points at `STAFF_TRAINING.md`. The PDFs themselves are unchanged (`reportlab` still not installable).
- **Verify:** `node --test tests/js/*.test.js` → 107 pass / 0 fail. `python3 -m unittest discover -s tests -p 'test_*.py' -q` → 151 OK.
- F-4 (dead `_renderScreen` path) not done; left for Phase 5.

## Phase 2 — Re-verify, iteration 2 of 5

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| HEAD verified | `71e04b714e2ccb1d8f0c1f6fa370d95e49884d15` (`71e04b7`) |
| Report | `docs/phase2-reverify.md` (iteration 2 section) |
| Verify | JS 107 pass / 0 fail. Python 151 OK. Mutations: shared occupancy key → 6 fail; Clear skips practice key → 1 fail; save every Live slot → 7 fail. |

**Counts (22 findings-table rows):** PASS **20** · FAIL **0** · BLOCKED **2** · WON'T FIX **0**

- **PASS — S0-OCCUPANCY-IPAD** (was FAIL): F-1a separate stores, mode-switch reload, Clear wipes both; tests and docs above.
- **BLOCKED — S0-OFF-FICTION:** UI and Markdown pass, and F-2 (PDF links note) is PASS. The PDF content still says "turn off" / "DRY-RUN" until the rebuild.
- **BLOCKED — BLOCK-SITE-\*** unchanged.
- F-3 PASS. F-4 open (not required).
- Still BLOCKED outside the table: BLOCK-SERVER-LEDGER, PDF rebuild, real HA `returnResponse` integration.

**Next:** no S0/S1 FAIL remains. Rebuild the staff PDFs on a machine with PyPI access to clear S0-OFF-FICTION; site items stay BLOCKED.

## Model policy (from 2026-10-21)

After Phase 3 completes, remaining phases (4–8 and any fix loops) use **Grok extra-high fast** (`grok-4.7-xhigh-fast`) only. Do not launch Opus/GPT sub-agents. Phase 3 itself was already running and is allowed to finish.


---

## Phase 3 — Production readiness

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Plan | `docs/prod-readiness-plan.md` (`bf7b5b6`) |
| Report | `docs/prod-readiness-report.md` |
| Started at | `c02d617` (+ `0d5cc1a` model-policy note) |
| Iterations | 2 of 5 |
| Verify | `node --test tests/js/*.test.js` → 107 pass / 0 fail. `python3 -m unittest discover -s tests -p 'test_*.py'` → 164 OK (was 151; +13). 50 `.py` compile, 19 `.js` pass `node --check`, 24 YAML + 4 JSON parse, `validate_panels.py` passes. HA `check_config` N/A (no Docker, no HA package). |

**Verdict:** Soft Launch **ready with conditions** (placeholder `inventory.json`, boolean off, train from `STAFF_TRAINING.md`, HA `check_config` at install, staff told Matrix is always live). Live **not ready**: BLOCKED on BLOCK-SITE-\* and a real HA `returnResponse` round trip; after that, single-iPad only (BLOCK-SERVER-LEDGER).

**Counts (PR-01…PR-10, PR-09 split a/b = 11 rows):** iteration 1: PASS 3 · FAIL 6 · BLOCKED 2. Final: PASS 9 · FAIL 0 · BLOCKED 2 (PR-09b, PR-10).

| Commit | Criterion | Change |
|--------|-----------|--------|
| `4de70d1` | PR-07, PR-05 | HA kills `shell_command` at 60 s and the panel gets no report. Bench (`tests/bench_live_latency.py`, real CLI vs fake H25s): slow `/tv/getTuned` went from killed at 60 s with 5 TV groups switched and no report, to 35 s with a full report (3 ok, 6 "Not attempted", UDP count = ok count). Executor starts a slot only if its worst case (17 s at `timeout_seconds` 4) fits a 50 s budget (`--time-budget`); too-long SHEF timeout fails preflight; `elapsedMs` on report and slots. `tests/test_live_time_budget.py` (8, all fail pre-fix). |
| `4bf42db` | PR-05 | `script.avaccess_live_execute` keeps 50 traces (HA default 5); each trace holds the executor report. `HA_LIVE.md` "How Live is gated" items 7–8. 1 test. |
| `60477b8` | PR-03 | `complete_ha_onboarding.py` applied a fixed owner password that six docs published (two next to port-forward 8123). Now `--password`, `AVACCESS_HA_OWNER_PASSWORD`, or a generated one printed once after success; dry-run redacts. Docs scrubbed with a rotate note. 4 tests (3 fail + 1 error pre-fix). The old value remains in git history. |
| `8bcee90` | PR-08 | HA OS update steps skipped the copied `run_*.py` / `directv_shef.py`; the pre-WP-D wrapper rejects `--live-commit` (exit 2, no report), so Live would fail after a `git pull`. Update now backs up and recopies; rollback is four ordered steps (boolean off, placeholder `inventory.json`, restore backup + SHA, Matrix). |
| `cf9c5e3` | PR-04, PR-06 | README configuration reference (all config files, Live boolean, all env vars; two were undocumented). `requirements-dev.txt`: `pytest>=9.0.3`, `PyYAML>=6.0`, `jinja2>=3.1.6` (HA template tests skipped without jinja2). New `requirements-docs.txt`: `reportlab>=3.6.13`, `pillow>=13.0.0`. Floors from the GitHub Advisory Database (`gh api graphql`); Snyk MCP was in error state and PyPI unreachable, so the floors were not install-tested. |

**Still BLOCKED:** PDF rebuild / S0-OFF-FICTION (PyPI SSL EOF); BLOCK-SERVER-LEDGER; real HA `returnResponse`; BLOCK-SITE-WALL / RECONNECT / BROADCAST / SUNDAY-CH.

**Next:** Phase 4 (Chrome primary flows). On site before Soft Launch: HA `check_config`, placeholder `inventory.json`, boolean off.
