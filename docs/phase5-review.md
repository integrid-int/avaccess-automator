# Phase 5 — Final pre-merge diff review

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Branch | `cursor/remediation-2026-10-21-af45` |
| Base | `origin/main` `e2f97d3` (Restyle the Matrix dashboard with Sports Routing keys) |
| Diff reviewed | `git diff origin/main...HEAD` at `c693c25`, then the one fix below |
| Fix | `9b715c1` |
| JS tests | `node --test tests/js/*.test.js` → **107 pass / 0 fail** |
| Python tests | `python3 -m unittest discover -s tests -p 'test_*.py'` → **164 OK** |
| Live boolean | `input_boolean.avaccess_live_commit` is **off** (`last_changed` `2026-10-21T05:58:40.209207+00:00`) |

**Verdict: satisfied.** One finding was fixed and verified. Everything else from this pass is WON'T FIX. Previously accepted blockers were not reopened.

Not merged. Not pushed to `main`. No pull request.

## Not reopened

These stay as already recorded. They are not new rows.

- Soft Launch is conditional. Live stays BLOCKED on site hardware (wall, reconnect, broadcast, Sunday channels) and the server occupancy ledger.
- Staff PDFs still say turn off / DRY-RUN. `reportlab` cannot be installed here.
- Staging package `avaccess_matrix` template list does not merge. Shipped `homeassistant/config` `check_config` has no fatal YAML error.
- Chrome on port 8123 passed PRACTICE flows. A 390px width stacks the inventory hint. The iPad 1180 layout does not. 390px is not a ship blocker.

## What was reviewed

Product diff against `origin/main`: panel Take path (`panel-health.js`, `live-execute.js`, `route-planner.js`, `panel-data.js`, `panel-view.js`), Live script and shell quoting (`avaccess_routing.yaml`, `run_execute_route_plan.py`), executor preflight / time budget / UDP re-enrich (`execute_route_plan.py`), SHEF status and tune verify (`directv_shef.py`), preset preflight (`apply_preset.py`), base64 checks (`save_tv_sets.py`), and the onboarding password removal. Phase 4’s live Home Assistant gate response (`returncode` 3, refusal stdout, boolean left off) matches `interpretLiveServiceResponse`.

No new S0 or S1 defect. Live still refuses unless the boolean is on, occupancy is success-only and split by mode, and a missing tune does not send UDP.

## Findings

| ID | Severity | File | Finding | Disposition |
|----|----------|------|---------|-------------|
| F-4 | S2 | `homeassistant/config/www/panels/panel-health.js` | `_renderScreen` had no callers. `render()` builds the board with `_renderRoutingBoard`. The only "Dry-run Send" / "Live Send" label was `_planSendLabel`, used by `_renderProgramPickerScreen` and `_renderContentPickerScreen`, which only `_renderScreen` called. `entryPath` is never set to `"tv"`, so the TV-first picker was unreachable too. | **FIX** (`9b715c1`). Removed those renderers, `_planSendLabel`, and the helpers only they used (`_renderGameCard`, `_renderGuideRowCells`, `_speculativePlan`, `_renderSlotStrip`). Cache-bust is `panel-health.js?v=35`. Source tests that pinned the retired templates now follow the live Take board and reject `Dry-run Send`. JS 107, Python 164. Click handlers for the old actions (`send-plan`, `send-tv-first`, `next-choose-content`) remain, but no rendered control has those `data-action`s, so they do not run. |
| P5-H25-COPY | S2 | `docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md` | Rollback step F still says "Dry-run Send stays occupancy-only." The button is Take, and practice is occupancy-only. | **WON'T FIX.** Pre-existing site-test wording. The safety instruction (Live commit off, wall unchanged) is still right. Staff UI copy is `STAFF_TRAINING.md`. Not the accepted PDF rebuild. |
| P5-SPORTS-EMPTY | S2 | `docs/HA_LIVE.md` | The `sports_schedule.json` row says the sports rail stays empty when the file is missing. The panel shows the hardcoded demo slate and the fallback banner instead. | **WON'T FIX.** The banner says demo games and Live Take is blocked. The `source` column (`directv-sports-info`) is the check that matters. Not a behavior bug. |
