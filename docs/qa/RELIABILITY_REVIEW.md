# Reliability review — AVAccess Automator (Sports Routing live path)

Reviewer lens: reliability / systems. Read-only. Base: `cursor/pre-prod-qa-review-af45` @ `e2f97d3`.
Evidence logs in this folder: `probe_executor_output.log`, `probe_panel_output.log` (probes drive the real
`execute_plan()` and the real `PanelHealth` class headlessly), `js_tests.log`, `python_unittest_subset.log`,
`python_pytest_shim.log`. Upstream HA behavior verified against `home-assistant/core` `shell_command/services.py`
and `home-assistant/frontend` `src/state/connection-mixin.ts` (fetched via `gh api`).

## Verdict

- **Live Send: NO-GO.** Three independent S0s each produce silent wrong content or a false "done" on the bar
  iPad under ordinary conditions (not edge cases).
- **Dry-run-only soft launch: GO with conditions** — keep `/config/www/avaccess/inventory.json` un-exported
  (REPLACE_ME) so the panel's Live toggle stays disabled, keep `config/inventory.yaml` on the example so the
  executor preflight also refuses, and wipe iPad `localStorage` (`avaccess-bartender-panel-v2`) before any later
  Live enablement because dry-run Takes write occupancy.
- Matrix Lovelace path (apply_preset / directv_shef CLI) is out of this lens but shares hardware with the panel and
  is invisible to it (see S1-6).

## S0 — block Live

### S0-1 Live result never reaches the panel; every failure renders as a clean "Live summary"
- `panel-health.js` `_sendPlan()` calls `this.hass.callService("shell_command","avaccess_execute_route_plan",{plan_b64, live:true})`
  with no 4th/5th/6th args. HA frontend `callService(domain, service, data, target, notifyOnError=true, returnResponse=false)`.
  Without `return_response`, HA core `shell_command` returns `None` → frontend resolves `{context}` only.
- HA core: non-zero return code is only `_LOGGER.exception(...)`; it does **not** raise. Only the 60 s timeout raises.
- `parseLiveExecuteReport({context})` → `null` (probe Q1) → `lastPlan` keeps planner slots with `status:"planned"`,
  which `_renderDryRunSummary()` renders with no status suffix = looks successful.
- Consequences: executor exit 2 (preflight: REPLACE_ME, missing `directv.yaml`, wrapper/import failure), exit 1
  (SHEF failure on N slots) and any Python crash are all invisible on the iPad. Partial-failure semantics in the
  executor (correct — see "Partial failure" below) are therefore **not surfaced** at all.
- Occupancy is written before the call (`applyRoutePlan` + `_saveAssignments` precede `callService`) so the panel
  believes the route happened (probe Q5).
- Tests don't catch it: `tests/js/panel-shell.test.js` only regex-matches that `parseLiveExecuteReport` exists.
- Fix direction: pass `returnResponse=true`; treat `response.response.returncode !== 0` or `report.ok === false` or
  missing report as failure; write occupancy only for slots whose report status is `ok`.

### S0-2 Games without a DirecTV channel are live-routed with no tune (UDP only)
- `route-planner.js` `slot()` sets `tune: null` when `program.channelNumber` is falsy; `_toProgram()` yields
  `channelNumber: null` for games with `"channel": "No channel"`.
- `execute_route_plan.py` `execute_plan()` skips SHEF when channel is empty, then still sends UDP and marks `ok`
  (probe P1: `calls: [('udp', 'IPE935-03', …)]`, `slot status: ok`).
- Panel does not block it: `_takeError()` returns `""` and the live plan is sent with `tune:null` (probe Q7).
- Scale: `www/avaccess/sports_schedule.json` has **212 / 552** games with `channelNumber: null`. All 25 hard-coded
  fallback games in `panel-data.js` `SPORTS` have no `channelNumber` (probe Q11).
- Effect: the TVs are switched to the lowest "free" encoder, whose H25 is on whatever it last showed. Silent wrong
  content, reported ok. README §Guide even says "Games do not tune" (stale model from when encoders were fixed).
- Fix direction: in Live, refuse slots with no tune (planner error + executor preflight), or require an explicit
  "switch TVs only (box already on it)" mode tied to a known-tuned encoder.

### S0-3 Occupancy is per-iPad `localStorage`; a second iPad (or a cleared cache) reallocates a busy encoder
- `assignment-store.js` `loadAssignments/saveAssignments` → `localStorage[STORAGE_KEY]` only. Nothing is stored in HA.
- `listFreeEncoders(listBusyEncoderIds(this._assignments))` is device-local. Probe Q4: iPad A Takes TVs 1–2 → ENC-01 /
  ch 212; iPad B Takes TVs 20–21 → **ENC-01 / ch 206** → H25-01 retunes, iPad A's TVs now show 206; iPad A still says 212.
- Same failure for one iPad after Companion "reset frontend cache" (which HA_LIVE §8 tells operators to do after every
  panel update), Safari private mode, or a replacement iPad.
- No executor-side lock or occupancy ledger; two concurrent `shell_command` processes run unserialized.
- Fix direction: server-side occupancy (e.g. HA `input_text`/JSON file written by the executor only on success, or
  an HA `todo`/`sensor` entity) read by every iPad, plus an `fcntl` lock around `execute_plan`.

## S1 — high

### S1-1 The HA kill switch `input_boolean.avaccess_live_commit` is not enforced
- `_syncLiveCommitFromHass()` reads the entity **once** (`_liveCommitSynced = true`) and never again (probe Q8: HA
  flips off → panel still `liveCommit:true`).
- `toggle-live-commit` only flips local state; it never calls `input_boolean.turn_on/off`. With the HA boolean off,
  staff can tap the panel toggle and go live (probe Q8).
- `avaccess_routing.yaml` renders `--live` from the caller's `live` argument; `execute_route_plan.py` never reads the boolean.
  Any authenticated HA user can call the service with `live: true`.
- HA_LIVE §9 #7 ("off except during a live Take") and §Rollback ("leave Live commit off") assume a central switch that
  does not exist. STAFF_TRAINING "until a manager turns Live commit on" — no role gating exists.
- Fix direction: executor (or a `script:` wrapper with a `condition:`) refuses `--live` unless the boolean is on;
  panel subscribes to the entity on every `hass` update and toggles it via service call; consider `require_admin`.

### S1-2 Retuning a shared encoder changes TVs the staff did not select; panel marks them "Off"
- `route-planner.js` adhoc: `singleEncoderForTvs()` reuses the encoder when all selected TVs are on it, even when free
  encoders exist; `replaceEncoderId` path does the same. `replaced.offTvs` lists the rest.
- Executor only sends `msg_b_reconnect` for the selected RXs. Nothing is sent to `offTvs`.
- Probe Q6: ENC-01 on TVs 1–10 (CBS) → Take NFL on TVs 1–3 → plan reuses ENC-01, tunes 212, UDP to RX-01..03 only;
  panel stores `ENC-01:[1,2,3]` and shows TVs 4–10 as Off. Unless `msg_b_reconnect` evicts unlisted RXs from the TX
  (undocumented in the repo), TVs 4–10 physically switch to NFL.
- Staff copy asserts the opposite: picker text "TVs that were on it and are not in X turn off"; `build_staff_pdfs.py`.
- Fix direction: prefer a free encoder when one exists; when reusing/replacing, either include `offTvs` in the move or
  explicitly route them (blank/default source) and show it; verify on-site what reconnect does to unlisted RXs.

### S1-3 Occupancy drift sources with no reconciliation or reset
- Written before/independent of live result (S0-1, probe Q5: call throws, occupancy still records TV 5).
- **Dry-run Takes write occupancy** (`_sendPlan` applies `applyRoutePlan` regardless of `commit`; probe Q10). Weeks of
  "practice presses" (STAFF_TRAINING) become phantom busy encoders on day one of Live → spurious "All DirecTV boxes are
  in use" / replace sheets, and allocation decisions made against fiction.
- Matrix dashboard (`apply_preset.py`, numeric_v1 contiguous) drives the same TX/RX/H25s; panel never learns.
- No "clear all / sync from wall" action exists in `panel-health.js`. "Now playing" (`_renderNowPlaying`) is local state,
  never SHEF `getTuned`.
- Fix direction: server-side ledger (S0-3) + reset action + optional SHEF `/tv/getTuned` reconciliation per encoder.

### S1-4 No in-flight guard; long, silent sends invite double-taps; HA 60 s kill leaves partial state
- Take button `ready` (`_renderTake`) has no "sending" state; selection is only cleared after `await` resolves.
  Probe Q3: two taps → **two concurrent live executions** (same plan here because the 1st already wrote occupancy;
  idempotent-ish but doubles SHEF+UDP and races with any change staff make mid-flight).
- Budget: SHEF `urlopen(timeout=4)` per slot, sequential, preset_3 = 9 slots → 36 s typical unreachable-box case,
  ~72 s worst case (connect + stalled read) > HA `COMMAND_TIMEOUT = 60` → process killed mid-plan, no report, some
  boxes retuned/some TVs switched; panel shows "Live execute failed" while occupancy records full success.
- iPad sleep / websocket drop during the call → promise rejects though the server keeps executing → staff retry.
- Fix direction: disable Take + spinner while in flight, idempotency key per Take, overall executor deadline (<50 s) with
  parallel SHEF, flock to serialize.

### S1-5 Docker bridge / wrong-NIC broadcast fails silently and leaves half-applied routes
- `udp_reconnect.send_udp()` = one `sendto` to `255.255.255.255:5010`; success only means the kernel accepted it
  (probe P5). In bridge mode it goes to `docker0`; on multi-NIC hosts it leaves the default-route NIC.
- SHEF (unicast TCP) works through NAT, so H25s retune but TVs never switch → encoders feeding other TVs change content.
- Repo's `homeassistant/docker-compose.yml` is bridge (`ports: 8123`) with `TZ=UTC`; HA_LIVE says edit it to host mode,
  but nothing detects the mistake. Inventory gate accepts `255.255.255.255`.
- Fix direction: executor preflight asserting the broadcast address is on a local interface subnet (and not a docker
  bridge), or unicast to known RX IPs; site checklist item that observes a reconnect packet on the AV LAN.

### S1-6 Inventory symlink-to-example trap, and two unsynchronized gates
- `config/inventory.yaml` is a **tracked** symlink → `inventory.example.yaml`. An editor or `cp` without `rm` writes real
  hostnames into the tracked example (leak risk + merge conflicts). After `rm`+`cp` (HA_LIVE §3), git shows a typechange;
  `git stash` / `checkout .` / `reset --hard` during "Updating a box" restores the symlink.
- Then the executor reads REPLACE_ME → exit 2 on every Take, while the separately copied `/config/www/avaccess/inventory.json`
  still says ready → Live toggle enabled → with S0-1 every Take shows success and the wall never changes.
- `directv.yaml` has no placeholder gate: example IPs `192.168.10.151–160` pass `_directv_map_errors`.
- Fix direction: untrack `config/inventory.yaml` (gitignore like `directv.yaml`), executor refuses symlinked or
  example-identical configs, add a placeholder-IP check for directv, have the executor (not a manual cp) emit inventory.json.

## S2 — medium

- **S2-1 Report merge drops preflight failure even if S0-1 is fixed.** `mergeLiveReportIntoPlan()` with `{ok:false, slots:[]}`
  leaves slots `planned`, sets no `plan.error`; errors become yellow warnings only. Empty stdout → `null` (probe Q2).
  `returncode` is never read.
- **S2-2 UDP is single-shot, unacknowledged, session always restarts at 1** (`execute_plan(session_start=1)`, probe P4);
  no inter-message delay (Matrix `apply_preset.py` uses `--delay 0.15`). Device semantics of the session field unknown.
- **S2-3 SHEF success not verified.** `directv_shef.shef_get()` accepts any 2xx JSON; body `status.code`/`commandResult`
  ignored; live path never calls `/tv/getTuned`. UDP fires immediately after tune (brief old-channel flash).
  Timeout errors surface as bare `"timed out"` without host (probe P6).
- **S2-4 Sports refresh fragility.** Single 06:00 attempt (`avaccess_sports.yaml`), no retry/alert. Selenium worst-case
  budget in `fetch_window_via_selenium` ≈ 20+20+20+35+10 = 105 s > 60 s. A zero-game pull writes `sports: []` atomically
  over a good file (`main()` has no empty guard); fresh iPads then fall back to demo `SPORTS` (Yankees @ Red Sox …), which
  are Take-able and hit S0-2. No `generatedAt` staleness indicator; past games not filtered.
- **S2-5 EPG staleness.** `avaccess_guide.yaml` ships the shell_command but **no automation** (README has a commented
  example) → banner permanently 6 h after deploy. `now/next` is frozen at build time and `mergeGuideWithEpg()` ignores
  `stop`, so "Now" can be up to 6 h wrong. `build_guide_epg.main()` uses non-atomic `write_text` (panel reads during write
  → banner; benign). TV Passport fetch `timeout=30` per request within the 60 s HA limit.
- **S2-6 First exercise of the HA wrapper path is the first Live Take.** Panel never calls the shell_command in dry-run;
  HA_LIVE §7 smoke tests run CLIs directly, not `run_execute_route_plan.py` via HA. Mount/import faults appear only at
  Live and (S0-1) invisibly. Add a Developer Tools step: call the service with `live:false` + response.
- **S2-7 Docs drift.** README "Games do not tune" (they do when numbered); HA_LIVE §9 #7 / Rollback (S1-1);
  STAFF_TRAINING "manager turns Live on" (no gating); "TVs … turn off" (S1-2).
- **S2-8 Compose symlink overlap (unverified).** Tracked symlinks `homeassistant/config/avaccess/config → ../../../config`
  and `…/scripts` sit on the bind-mount destinations `/config/avaccess/config|scripts`. Inside the container the config
  symlink resolves to `/config`; runc's secure-join may mount the repo `config/` over HA's `/config` or refuse. Staging
  used a different compose. Needs one `docker compose up` on the host-network variant.

## S3 — low
- `inventory.json` fetched without `cache:"no-store"` (other feeds use it) → stale gate after export.
- Module imports pinned `?v=18/19` independently of `module_url ?v=30` → panel/planner version skew after partial updates.
- Inventory validation is shallow: no `IPE935-`/`IPD935-` role check, no duplicate hostnames, example IPs/MACs not flagged.
- TV sets: last-writer-wins `custom_tv_sets.json`; an iPad only reads it when its local key is missing → sets diverge.
- Dead legacy screens (`_renderScreen`, `_renderDestinationScreen`, program/content pickers) never rendered but still
  contain alternate send buttons — maintenance hazard.
- Preflight from `enrich_route_plan()` joins all errors into one string (runs before the live validator).

## S4 — info
- `/local/avaccess/inventory.json` is served unauthenticated (security cross-ref).
- `msg_b_reconnect` semantics (session id meaning, eviction of unlisted RXs, rate limits) are not documented in-repo.
- Executor partial-failure semantics are correct: SHEF failure raises before UDP for that slot; other slots continue;
  exit 1 with full per-slot report; preflight exit 2 with no network I/O (probes P2, P3).

## Partial failure — direct answer
Implemented correctly in `execute_plan()` (probe P2: ENC-01 SHEF fails → no UDP for ENC-01, ENC-02..04 SHEF+UDP, `ok:false`,
exit 1). **Not surfaced** (S0-1, S2-1). Two gaps in the semantics themselves: UDP failure after a successful tune leaves the
box retuned (affects any TVs already on that encoder), and a slot with no tune is treated as success (S0-2). The existing
unit test `test_continues_after_slot_error` does not assert that UDP was skipped for the failed slot.

## Preflight exit codes vs panel
| Exit | Executor meaning | Panel today | Panel with returnResponse but current merge |
|---|---|---|---|
| 0 | all slots ok | looks ok (no status) | slots `ok` |
| 1 | ≥1 slot error | looks ok | per-slot `error` shown ✔ |
| 2 | preflight / exception, no I/O | looks ok | warnings only; slots `planned`; no error ✘ |
| killed (60 s) | partial I/O | "Live execute failed: …" + occupancy saved | same |
| crash before print | no stdout | looks ok | `null` → looks ok ✘ |

## Uncovered risk list (not provable from repo)
1. What `msg_b_reconnect` does to RXs on the TX that are not listed (S1-2 hinges on it).
2. Whether the switch dedupes/ignores repeated `session=1` messages or needs spacing.
3. H25 SHEF responses for standby, invalid channel, Sunday Ticket `9554`-style majors, and HTTP 200 with error body.
4. Real SHEF latency per box under load (sets the 60 s budget).
5. Broadcast reachability from the actual HA host/NIC; multi-NIC routing.
6. ENC-n HDMI ↔ H25-n physical pairing (no automated check; `get-tuned` cross-check possible).
7. Companion behavior: does "reset frontend cache" clear `localStorage`; websocket drop mid-call.
8. DirecTV sports page / TV Passport markup stability and ToS; Selenium add-on uptime.
9. Docker compose symlink/mount interaction (S2-8).
10. HA version drift: `image: …:stable` unpinned; `shell_command` contract (timeout raise, response shape) could change.

## Suggested verification tests for the fix agent
JS (node:test, drive the real class as in `probe_panel.mjs`):
1. `_sendPlan` live calls `callService(..., undefined, true|notify, true)` (returnResponse) — assert 6th arg `true`.
2. Response `{response:{returncode:2, stdout:'{"ok":false,"slots":[],"errors":["X"]}'}}` → `lastPlan.error` set, every slot
   `status:"error"`, occupancy unchanged.
3. `returncode:1` with ENC-01 error, ENC-02 ok → occupancy contains only ENC-02's TVs.
4. Empty stdout / unparsable stdout with `returncode≠0` → error banner, occupancy unchanged.
5. Double-tap: two `send-destination` clicks while first promise pending → exactly one `callService`.
6. Game with `channelNumber:null` in Live → Take disabled or plan error; no `callService`.
7. HA boolean `off` → live toggle disabled / `_sendPlan` sends nothing live; boolean flips off mid-session → panel follows.
8. Shared encoder subset Take with free encoders available → allocates a free encoder (or routes `offTvs` explicitly).
9. Dry-run Take does not mutate live occupancy (or occupancy namespaced by commit mode).
10. Two panel instances sharing the server ledger mock → second allocation avoids the first's encoder.
11. `sports_schedule.json` `sports:[]` → no demo SPORTS in production config; staleness banner when `generatedAt` > 24 h.
Python (pytest):
12. `execute_plan` live with `tune:None` → slot error, no UDP call.
13. `test_continues_after_slot_error` additionally asserts `send_udp_reconnect` not called for ENC-01.
14. Executor refuses `--live` when the HA boolean (passed in or read) is off.
15. Overall deadline: 9 slots with SHEF stub sleeping 10 s → executor returns a report before 55 s, marking unfinished slots.
16. Concurrency: two `main()` processes on one lock file → serialized (second waits or returns busy).
17. Preflight: symlinked `inventory.yaml`, example-identical `directv.yaml`, placeholder IPs → exit 2.
18. Broadcast preflight: address not on any local interface → exit 2 with a clear message.
19. `directv_sports.main` with zero games → exit non-zero, existing file untouched.
20. `build_guide_epg.main` writes atomically (tmp + `os.replace`); HA package ships an hourly automation.
Site / integration:
21. Call `shell_command.avaccess_execute_route_plan` from Developer Tools with `live:false` and "return response" — verify
    JSON stdout and `returncode` from inside the real HA container.
22. Packet capture on the AV LAN during one Live Take (verifies S1-5 / host networking).
23. One-TV shared-encoder test to settle S1-2 physically.
