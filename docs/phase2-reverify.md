# Phase 2 — Re-verify findings

Iteration 2 is current. Iteration 1 is kept below for history.

## Iteration 2 of 5

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Branch | `cursor/remediation-2026-10-21-af45` |
| Code verified at | `71e04b714e2ccb1d8f0c1f6fa370d95e49884d15` (`71e04b7`) |
| Changes since iteration 1 | F-1a `6280e01` (code + tests), `eca1ec2` (docs); F-3 `a9af537`; F-2 `71e04b7` |
| JS tests | `node --test tests/js/*.test.js` → **107 pass / 0 fail** (was 100; +6 occupancy, +1 hint) |
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py' -q` → **151 OK** |

**Result (22 findings-table rows):** PASS 20 · FAIL 0 · BLOCKED 2 · WON'T FIX 0

**S0/S1 FAIL:** none. S0-OCCUPANCY-IPAD moved FAIL → PASS. S0-OFF-FICTION stays BLOCKED on the PDF rebuild only.

### Findings

| ID | Severity | Status | Evidence | Gap (if FAIL) |
|----|----------|--------|----------|---------------|
| S0-SILENT-LIVE | S0 | PASS | `_sendPlan` now saves through `_saveAssignments(nextAssignments, occupancyKey)`, still after `runLiveSendSafe` returns, and `occupancyPlanFromLiveResult` still keeps only `ok` slots. Iteration 1 tests pass. Mutation re-run: saving every slot → JS 100 pass / 7 fail (same as iteration 1). | — |
| S0-NO-CHANNEL | S0 | PASS | Unchanged since iteration 1: `takeBlockReason` path in `_sendPlan` and executor preflight untouched; `panel-send.test.js` / `take-guards.test.js` / `test_execute_route_plan_live_tune.py` pass. | — |
| S0-OCCUPANCY-IPAD | S0 | **PASS** | F-1a. `panel-data.js` adds `PRACTICE_STORAGE_KEY = "avaccess-bartender-panel-practice-v1"`; Live stays `STORAGE_KEY = "avaccess-bartender-panel-v2"`. `panel-health.js` `_occupancyKey()` picks Live only when `liveCommit` and inventory ready. `_syncLiveCommitFromHass` ends with `_syncOccupancyStore`, which reloads `_assignments` from the target key on a mode change (no merge) and clears Replace/Confirm choices. `_sendPlan` captures the store key before the await, so a Live send that finishes after Live is turned off saves to the Live key only. `_clearRoomState` removes both keys. Planner busy encoders and Now read `_assignments`, so they follow the mode. Tests (`panel-send.test.js`, real panel through Take): practice Take writes only the practice key; Live Take after practice Takes claims ENC-01 with one script call and no `replaced`; a full practice room asks Confirm in PRACTICE but not after Live arms; practice Take after a Live Take leaves the Live key byte-identical and Live reloads it; in-flight Live send survives a mode flip; Clear room state removes both keys and keeps TV sets. Mutations: one shared key → 6 fail; Clear without the practice key → 1 fail. Docs: `HA_LIVE.md` 7b (bullet, step 3, return-to-practice line, checklist 8c), `README.md` occupancy + Now + Live gating, `OPERATIONS_GUIDE.md` Soft Launch, `STAFF_TRAINING.md` Clear room state / Now / troubleshooting say the stores are separate and Clear wipes both. Cache-bust `panel-health.js?v=34` (`configuration.yaml`, `prepare_ha_staging.py`, docs); `panel-data.js?v=21`. Single-iPad Live and BLOCK-SERVER-LEDGER unchanged. | — |
| S0-REUSE-BAR | S0 | PASS | Unchanged since iteration 1 (`route-planner.js` untouched); `_gateReuseConfirm` unchanged. Reuse tests pass, plus the new full-practice-room test shows Confirm comes only from the current mode's store. | — |
| S0-OFF-FICTION | S0 | BLOCKED | UI and Markdown still pass: the `rg` sweep of `docs/*.md`, `README.md`, `scripts/build_staff_pdfs.py`, and panel JS finds only negations ("do not turn off") and the boolean being **off**. F-2 done: every PDF link carries the pending-rebuild note. **Blocked:** `STAFF_QUICK_START.pdf` and `STAFF_FULL_GUIDE.pdf` are unchanged since iteration 1; decoded text still has "turn off" (quick start) and "DRY-RUN" (full guide). `pip install reportlab` → "No matching distribution found". | — |
| S1-LIVE-BOOLEAN | S1 | PASS | Unchanged since iteration 1 for the gate (`avaccess_routing.yaml`, wrapper). `_syncLiveCommitFromHass` still sets `liveCommit` only from `liveCommitFromStates`; it now also syncs the occupancy store. `live-commit-sync.test.js`, `test_live_interlock.py`, and "Take re-reads the HA boolean…" pass. | — |
| S1-B64-SHELL | S1 | PASS | Unchanged since iteration 1: YAML and Python untouched; `test_live_interlock.py` passes. | — |
| S1-UDP-TRUST | S1 | PASS | Unchanged since iteration 1: `execute_route_plan.py` untouched since `94cbb66`; tests pass. | — |
| S1-SHEF-STATUS | S1 | PASS | Unchanged since iteration 1: `directv_shef.py` / executor untouched; tests pass. | — |
| S1-PRESET-PARTIAL | S1 | PASS | Unchanged since iteration 1: `apply_preset.py` untouched; `test_apply_preset.py` passes. | — |
| S1-DOUBLE-TAP | S1 | PASS | `_sending` / `createInFlightLock` unchanged. "a second Take while Live is in flight…" passes; the new in-flight mode-flip test also goes through the lock. | — |
| S1-DEMO-FALLBACK | S1 | PASS | Unchanged since iteration 1; "demo sports fallback blocks Live Take but still allows a PRACTICE Take" passes. | — |
| S1-VIS-TOKENS | S1 | PASS | Unchanged since iteration 1 (CSS and `commitModeBanner` untouched); `panel-shell.test.js`, `panel-render.test.js` banner tests pass. | — |
| S1-SCROLL-JUMP | S1 | PASS | Unchanged since iteration 1; scroll tests pass. | — |
| S1-MATRIX-CONFUSION | S1 | PASS | `OPERATIONS_GUIDE.md` still has "Which one changes the wall" / "AVAccess Matrix is always live"; `STAFF_TRAINING.md` still says Matrix has no PRACTICE mode. | — |
| S1-INVENTORY-TRAP | S1 | PASS | Unchanged since iteration 1: `cp --remove-destination` in `HA_QUICKSTART.md` and `HA_LIVE.md` section 3. | — |
| S1-DOCKER-UDP | S1 | PASS | Unchanged since iteration 1: `HA_LIVE.md` section 0 "Live UDP needs Home Assistant OS or host networking" and "Warning — Docker bridge". | — |
| S2-LOGO-FALLBACK | S2 | PASS | Unchanged since iteration 1; tests pass. | — |
| S2-RAIL-FOLD | S2 | PASS | Unchanged since iteration 1; tests pass. | — |
| S2-SPORTS-STALE | S2 | PASS | Unchanged since iteration 1; tests pass. | — |
| S2-TESTS-SHALLOW | S2 | PASS | Harness still drives the real panel. New occupancy tests use the real `_sendPlan` and a recording `localStorage` (`savedPracticeAssignments`, `setLiveState` helpers). JS 107, Python 151. | — |
| BLOCK-SITE-* | — | BLOCKED | Unchanged: needs the site (wall, `msg_b_reconnect` eviction, host NIC / Docker UDP, Sunday channel set). | — |

### Recommended tasks from iteration 1

| Task | Status | Evidence |
|------|--------|----------|
| F-1a separate practice occupancy | PASS | See S0-OCCUPANCY-IPAD. |
| F-2 PDF links point at `STAFF_TRAINING.md` | PASS | All 8 lines with `STAFF_QUICK_START.pdf` / `STAFF_FULL_GUIDE.pdf` links (14 links: `README.md` 2 lines, `HA_LIVE.md` 3, `OPERATIONS_GUIDE.md` 1, `STAFF_TRAINING.md` 2) carry "PDFs pending rebuild; use STAFF_TRAINING.md for the current UI". `rg "STAFF_(QUICK_START\|FULL_GUIDE)\.pdf" … \| rg -v "pending rebuild"` returns nothing. `OPERATIONS_GUIDE.md` Sports Routing paragraph and `STAFF_TRAINING.md` intro now name `STAFF_TRAINING.md` as current. The PDF content itself is still BLOCKED. |
| F-3 Live commit hint copy | PASS | `_renderLiveCommitToggle` hint is "PRACTICE — Take only plans; TVs do not change" / "LIVE — Take changes the TVs"; tooltip says Take. Test `panel-render.test.js` "Live commit hint uses PRACTICE / LIVE and Take wording" renders both modes and asserts no "Dry run" / "— Send". Ships in `?v=34`. |
| F-4 dead render path | Open (not required) | Not done. `_renderScreen` / `_planSendLabel` "Dry-run Send" are still unreachable. Leave for Phase 5 diff review. |

### Allowed BLOCKED items (outside the findings table, still open)

| Item | Status | Note |
|------|--------|------|
| BLOCK-SERVER-LEDGER | BLOCKED | Occupancy is still per-iPad `localStorage` (now two keys per iPad). Live stays single-iPad. |
| PDF rebuild | BLOCKED | `reportlab` not installable. Blocks S0-OFF-FICTION. `scripts/build_staff_pdfs.py` text is updated for F-1a, so the next rebuild picks it up. |
| Real HA `returnResponse` integration | BLOCKED | Still tested with offline fakes only. |

### Commands run (iteration 2)

```bash
git checkout cursor/remediation-2026-10-21-af45            # HEAD 71e04b7
node --test tests/js/*.test.js                             # 107 pass / 0 fail
python3 -m unittest discover -s tests -p 'test_*.py' -q    # Ran 151 tests, OK
pip install reportlab                                      # No matching distribution (PDF rebuild stays BLOCKED)
git diff --stat 94cbb66 HEAD -- live-execute.js route-planner.js assignment-store.js \
  scripts/execute_route_plan.py docs/STAFF_*.pdf homeassistant/packages   # empty
# Mutation checks (each reverted; tree clean afterwards)
#   panel-health.js _occupancyKey always STORAGE_KEY        : JS 100 pass / 6 fail
#   panel-health.js Clear room state skips practice key     : JS 105 pass / 1 fail
#   live-execute.js occupancy filter -> all slots           : JS 100 pass / 7 fail
```

---

## Iteration 1 of 5 (superseded)

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Branch | `cursor/remediation-2026-10-21-af45` |
| Code verified at | `94cbb665f4b15aa26696faae4e71223725c2ecf1` (`94cbb66`) |
| Source | Findings table in `docs/remediation-plan.md` (22 rows) |
| JS tests | `node --test tests/js/*.test.js` → **100 pass / 0 fail** |
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py' -q` → **151 OK** |

**Result:** PASS 19 · FAIL 1 · BLOCKED 2 · WON'T FIX 0

**S0/S1 FAIL:** `S0-OCCUPANCY-IPAD` only. Gap and proposed fix tasks are in the [S0/S1 FAIL](#s0s1-fail--gaps-and-proposed-fix-tasks) section.

---

### Findings

| ID | Severity | Status | Evidence | Gap (if FAIL) |
|----|----------|--------|----------|---------------|
| S0-SILENT-LIVE | S0 | PASS | `live-execute.js`: `liveExecuteCallServiceArgs` passes `returnResponse` as the 6th arg. `interpretLiveServiceResponse` fails on a missing report, `ok:false`, or nonzero `returncode`. `occupancyPlanFromLiveResult` keeps only `status==="ok"` slots, and `panel-health.js` `_sendPlan` saves after `runLiveSendSafe` returns. Tests: `live-execute.test.js` (exit 2 with empty slots; returncode 1 saves only ok slots; empty stdout; unparsable stdout; occupancy applied only after callService; thrown call) and `panel-send.test.js` ("Live Take saves only slots the server reported ok…", "…no report from Home Assistant saves nothing…"). Mutation: saving every slot makes 7 JS tests fail. | — |
| S0-NO-CHANNEL | S0 | PASS | Panel: `takeBlockReason` (`panel-data.js`) is used in `_sendPlan` and `_takeError`, so Take is disabled. Planner: `finishPlan` errors on a program with no channel. Executor: `_missing_tune_errors` live preflight (exit 2), plus a per-slot `elif live: raise` before UDP. Tests: `panel-send.test.js` ("Live Take of a game with no DirecTV channel never reaches Home Assistant"), `take-guards.test.js`, `test_execute_route_plan_live_tune.py` (6), and `test_execute_route_plan.py` live-tune cases. Mutation: removing the executor preflight makes 6 Python tests fail. | — |
| S0-OCCUPANCY-IPAD | S0 | **FAIL** | Done: single-iPad Live is documented (`HA_LIVE.md` 7b step 7; `README.md` occupancy section). **Clear room state** is implemented (`_clearRoomState` removes `avaccess-bartender-panel-v2`). The server ledger is recorded as BLOCK-SERVER-LEDGER. | The criterion "dry-run does not persist occupancy **OR** clear-on-load option" is not met. `runDryRunSend` → `_saveAssignments` writes practice routes to the same `localStorage` key as Live occupancy (test `live-execute.test.js` "dry-run applies occupancy for training…" asserts this). Nothing clears them on load or when Live arms: `_syncLiveCommitFromHass` only flips the flag. The only mitigation is a manual Clear room state on every iPad (`HA_LIVE.md` 7b step 3). `HA_LIVE.md` also says "To go back to practice at any time, turn Live commit off", and a practice Take done then overwrites real Live occupancy with fiction. When Live is turned back on, the planner can then pick a busy box or ask for a needless Confirm. |
| S0-REUSE-BAR | S0 | PASS | `route-planner.js` adhoc: `listFreeEncoders` is tried first, and `singleEncoderForTvs` runs only when none are free. `_gateReuseConfirm` blocks Take until Confirm when `replaced.offTvs.length > 0`, and the summary lists the leftover TVs. Tests: `route-planner.test.js` ("patio after All-35 claims a free encoder…", "does not reuse a shared box when a free encoder exists"), `panel-send.test.js` ("patio Take after All 35 claims a free encoder…", "reusing a shared box with no free encoders needs Confirm before Live is sent"). Mutation: reuse-before-free makes 3 JS tests fail. | — |
| S0-OFF-FICTION | S0 | BLOCKED | UI and Markdown pass. The summary row reads "`<label>` still on retuned box · TVs …". The warning says "…will keep showing the retuned program until reassigned". Empty Now rows say **Unassigned** / "Still showing last box until reassigned". `rg -i "turn off\|go off\|**Off**\|DRY-RUN SUMMARY"` finds no product claim in `docs/*.md`, `README.md`, `scripts/build_staff_pdfs.py`, or panel JS. `STAFF_TRAINING.md` says "nothing on this screen turns a TV off". **Blocked:** `docs/STAFF_QUICK_START.pdf` and `docs/STAFF_FULL_GUIDE.pdf` are unchanged since `82267a2`, and their decoded text still contains "turn off" (both) and "DRY-RUN" (full guide). `pip install reportlab` still fails here ("No matching distribution found"), so the PDF rebuild is the allowed BLOCKED. | — (see recommended task F-2) |
| S1-LIVE-BOOLEAN | S1 | PASS | `avaccess_routing.yaml`: `script.avaccess_live_execute` (`mode: single`) runs the shell only when `input_boolean.avaccess_live_commit` is `on`; otherwise it returns `returncode` 3. The shell template renders `--live-commit on\|off`, and `run_execute_route_plan.py` `live_refusal` exits 3. The panel toggle calls `input_boolean.turn_on/off`. `_syncLiveCommitFromHass` runs on every `hass` set, every `render()`, and at the start of `_sendPlan`. Tests: `test_live_interlock.py` (wrapper gate on/off/missing, Jinja+shlex render of the real YAML, script structure), `live-commit-sync.test.js` (5), `panel-send.test.js` ("Take re-reads the HA boolean…"). Real HA `response_variable` / `returnResponse` is tested only with offline fakes (allowed BLOCKED). | — |
| S1-B64-SHELL | S1 | PASS | `plan_b64` / `sets_b64` render only if they match `^[A-Za-z0-9+/]+={0,2}$` and are single-quoted. Python `decode_plan_b64` uses `validate=True` plus an alphabet regex, and `allow_abbrev=False`. Tests: `test_live_interlock.py` (`test_injected_plan_b64_cannot_add_arguments`, `test_injected_sets_b64_cannot_add_arguments`, `test_cli_injected_plan_b64_exits_2_without_sends`, `test_cli_rejects_abbreviated_live_flag`, `test_save_tv_sets_rejects_non_base64`). | — |
| S1-UDP-TRUST | S1 | PASS | `execute_plan`: `if live or _any_udp_null(working): enrich_route_plan(...)`, so live always overwrites `udp` from inventory. Tests: `test_live_overwrites_caller_supplied_udp_hostnames`, `test_live_prefilled_udp_for_unknown_tv_is_preflight_without_sends`. Mutation: dropping `live or` makes 1 Python test fail. | — |
| S1-SHEF-STATUS | S1 | PASS | `directv_shef.check_shef_status` runs on every `shef_get`. `tune_and_verify` polls `/tv/getTuned`. Executor `send_directv_tune` raises before UDP. Tests: `test_directv_shef.py` (`test_http_200_with_error_body_status_raises`, `test_non_200_code_rejected`, `test_nonzero_command_result_rejected`, `test_mismatch_raises_after_attempts`, `test_error_body_status_fails_slot_without_udp`, `test_verify_mismatch_fails_slot_without_udp`), `test_execute_route_plan.py` (`test_live_shef_error_body_status_fails_slot_before_udp`, `test_cli_live_shef_unverified_tune_exit_1_without_udp`). | — |
| S1-PRESET-PARTIAL | S1 | PASS | `apply_preset.plan_preset_messages` validates every route and builds every payload before any `send_udp`; on failure it reports "failed preflight; nothing sent". Tests: `test_apply_preset.py` (9), including unknown RX/ENC or a placeholder in a later route sending nothing, and all errors reported together. | — |
| S1-DOUBLE-TAP | S1 | PASS | `_sending` plus `createInFlightLock`. `_sendPlan`, `_sendDestination`, and `_sendTvFirst` return early while sending. `_renderTake` shows `disabled`, `aria-busy="true"`, and "Sending…". Tests: `panel-send.test.js` ("a second Take while Live is in flight sends nothing and the button shows Sending…"), `live-execute.test.js` ("in-flight lock ignores a second send…"). | — |
| S1-DEMO-FALLBACK | S1 | PASS | `sportsStatus` is `fallback` (or still `loading`), so `_usingSportsFallback()` returns true and `takeBlockReason` blocks Live Take. `SPORTS_FALLBACK_BANNER` reads "…showing demo games. Live Take is blocked." Tests: `panel-send.test.js` ("demo sports fallback blocks Live Take but still allows a PRACTICE Take"), `panel-render.test.js` (sports banner), `take-guards.test.js`. | — |
| S1-VIS-TOKENS | S1 | PASS | No `:host` left in `panel-health.js`. Tokens are declared on `panel-health { … }`, with the `.routing` remap. `commitModeBanner` (`panel-view.js`) drives the PRACTICE/LIVE header banner, `data-commit-mode`, and `routing is-live`. Tests: `panel-shell.test.js` ("resolves CSS tokens outside a shadow root", "styles the LIVE banner red…"), `panel-render.test.js` (banner text and mode, 4 cases), `panel-view.test.js`. Computed colors were checked in the WP-F headless Chrome harness (log WP-F). | — |
| S1-SCROLL-JUMP | S1 | PASS | `render()` returns early when the HTML is unchanged. Otherwise `captureScrollPositions` and `restoreScrollPositions` run over `[data-scroll-key]`. Tests: `panel-render.test.js` ("hass pushes keep list scroll…"), `panel-view.test.js` (2), `panel-shell.test.js` ("tags every scrolling list with a scroll key"). | — |
| S1-MATRIX-CONFUSION | S1 | PASS | `OPERATIONS_GUIDE.md` has a "Which one changes the wall" section ("AVAccess Matrix is always live"). `HA_LIVE.md` has the surface table and a "Which surface is live" line. `STAFF_TRAINING.md` says Matrix has no practice mode. The PRACTICE banner is in the panel header. | — |
| S1-INVENTORY-TRAP | S1 | PASS | `HA_QUICKSTART.md` uses `rm -f` + `cp --remove-destination` and explains the symlink. `HA_LIVE.md` section 3 has the same commands and explanation. `config/inventory.yaml` is still a symlink to `inventory.example.yaml` in the repo, so the warning is still needed. | — |
| S1-DOCKER-UDP | S1 | PASS | `HA_LIVE.md` section 0 says "Live UDP needs Home Assistant OS or host networking" and has a "Warning — Docker bridge" naming both compose files. Section 7b step 1 and checklist row 8b repeat it. | — |
| S2-LOGO-FALLBACK | S2 | PASS | `_teamLogoHtml` renders an initials tile for an empty or known-failed URL. The capture-phase `_onLogoError` swaps a failed `<img>` for the tile. Tests: `panel-view.test.js` (`teamInitials`), `panel-shell.test.js` ("falls back to team initials…"). The runtime swap was verified only in the WP-F headless Chrome harness. | — |
| S2-RAIL-FOLD | S2 | PASS | `_renderRail` puts Guide/Now/Sets in `.rail-pinned` above the scrolling `.rail-sports`. Tests: `panel-render.test.js` ("rail renders Guide, Now, Sets pinned above the sports list"), `panel-shell.test.js` ("keeps the pinned rail fixed…"). | — |
| S2-SPORTS-STALE | S2 | PASS | `isSportsScheduleFresh` uses a 24 h limit (`SPORTS_STALE_MS`). `_sportsScheduleBannerHtml` shows `SPORTS_STALE_BANNER`. Tests: `take-guards.test.js` ("isSportsScheduleFresh is false after 24 hours…", banner copy), `panel-data.test.js`, `panel-render.test.js`. | — |
| S2-TESTS-SHALLOW | S2 | PASS | `tests/js/panel-harness.js` drives the real `<panel-health>` through Take (`panel-send.test.js` 8, `panel-render.test.js` 7). Python bare `test_*` functions are now `unittest.TestCase`, and discover runs 151 with no import errors. Independent mutation spot-check in this pass: 4 of 4 caught (save-all-live-slots → 7 JS fails; reuse-before-free → 3 JS fails; live trusts caller udp → 1 Py fail; no live tune preflight → 6 Py fails). | — |
| BLOCK-SITE-* | — | BLOCKED | Needs the site: real wall (BLOCK-SITE-WALL), `msg_b_reconnect` eviction (BLOCK-SITE-RECONNECT), host NIC / Docker UDP (BLOCK-SITE-BROADCAST), and the Sunday channel set (BLOCK-SITE-SUNDAY-CH). Listed in `docs/remediation-plan.md` "Out of scope / BLOCKED pending site". | — |

#### Allowed BLOCKED items (outside the findings table, still open)

| Item | Status | Note |
|------|--------|------|
| BLOCK-SERVER-LEDGER | BLOCKED | No server occupancy store. Occupancy stays per-iPad `localStorage`, and Live is documented as single-iPad. |
| PDF rebuild | BLOCKED | `reportlab` cannot be installed (PyPI unreachable). This is what blocks S0-OFF-FICTION. |
| Real HA `returnResponse` integration | BLOCKED | `callService` 6th-arg `returnResponse` and the script's `response_variable` / `stop` are tested only with offline fakes. |

---

### S0/S1 FAIL — gaps and proposed fix tasks

#### S0-OCCUPANCY-IPAD

**Gap:** Practice (dry-run) Takes persist fictional occupancy into the same `localStorage` key that Live uses (`avaccess-bartender-panel-v2`). Nothing clears that occupancy on load or when Live arms. A practice Take done while the boolean is off overwrites real Live occupancy. The only mitigation is the manual **Clear room state** step on every iPad.

Note for the coordinator: WP-A step 4 in the plan says "prefer: dry-run applies for training but label PRACTICE", which conflicts with this acceptance row. If that trade-off is intended, record this row as WON'T FIX with that reason in the log. Otherwise pick one fix task:

| Task | Scope | Files | Test |
|------|-------|-------|------|
| **F-1a (preferred)** Keep practice occupancy separate | Practice Takes read and write a separate key (for example `avaccess-bartender-panel-practice-v1`), or memory only, and Live Takes use `avaccess-bartender-panel-v2`. `_loadAssignments` and `listBusyEncoderIds` read the store that matches the current mode. Clear room state wipes both. | `panel-health.js` (`_loadAssignments`, `_saveAssignments`, `_sendPlan` practice branch, `_clearRoomState`, plus a mode switch in `_syncLiveCommitFromHass`), `panel-data.js` (new key) | `panel-send.test.js`: a practice Take does not change the Live key. A Live Take after practice Takes still claims ENC-01 and does not need Confirm. A practice Take after a Live Take leaves Live occupancy intact. |
| F-1b (smaller) Tag and drop practice routes when Live arms | `applyRoutePlan` stamps `practice: true` on dry-run routes. When `_syncLiveCommitFromHass` flips to Live (and on load while Live), drop practice-tagged routes and save. | `assignment-store.js`, `live-execute.js` (`runDryRunSend`), `panel-health.js` | Same as F-1a, minus the practice-after-Live case: F-1b still lets a practice Take overwrite real occupancy. |

Either way, update the `HA_LIVE.md` 7b practice-occupancy bullet and step 3, `README.md` occupancy paragraph, `OPERATIONS_GUIDE.md` Soft Launch bullet, and `STAFF_TRAINING.md` Clear room state text to match.

#### Recommended (not needed to clear an S0/S1)

| Task | Why | Files |
|------|-----|-------|
| **F-2** Point staff at `STAFF_TRAINING.md` until the PDFs are rebuilt | `README.md`, `OPERATIONS_GUIDE.md` ("Sports Routing staff training (current landscape layout)"), `HA_LIVE.md` (lines 14, 373, 425), and `STAFF_TRAINING.md` present the two PDFs as current. Those PDFs still teach "turn off" and DRY-RUN SUMMARY, so S0-OFF-FICTION is still visible to staff. | Docs only: add "PDFs pending rebuild; use STAFF_TRAINING.md" next to each PDF link. Rebuild the PDFs on a machine with PyPI access in Phase 7. |
| F-3 Live commit hint copy | `_renderLiveCommitToggle` still shows "Dry run — Send only previews the plan" / "Live — Send changes the TVs" under the toggle. Everything else says Take / PRACTICE / LIVE. | `panel-health.js` (and bump `?v=`) |
| F-4 Dead render path | `_renderScreen` has no callers, so `_renderProgramPickerScreen` and the `_planSendLabel` "Dry-run Send" / "Live Send" labels are unreachable. Delete them, or leave them until the Phase 5 diff review. | `panel-health.js` |

---

### Commands run

```bash
git checkout cursor/remediation-2026-10-21-af45 && git pull origin cursor/remediation-2026-10-21-af45   # HEAD 94cbb66
node --test tests/js/*.test.js                                   # 100 pass / 0 fail
python3 -m unittest discover -s tests -p 'test_*.py' -q          # Ran 151 tests, OK
pip install reportlab                                            # No matching distribution (PDF rebuild stays BLOCKED)
# Mutation spot-checks (each reverted with git checkout; tree clean afterwards)
#   live-execute.js  occupancy filter -> all slots       : JS 93 pass / 7 fail
#   route-planner.js reuse shared box before free        : JS 97 pass / 3 fail
#   execute_route_plan.py live skips udp re-enrich       : Python FAILED (failures=1)
#   execute_route_plan.py no _missing_tune_errors        : Python FAILED (failures=6)
```
