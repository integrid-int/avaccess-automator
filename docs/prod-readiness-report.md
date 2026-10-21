# Phase 3 — Production readiness report

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Branch | `cursor/remediation-2026-10-21-af45` |
| Plan | `docs/prod-readiness-plan.md` (`bf7b5b6`) |
| Started at | `c02d617` |
| Verified at | `cf9c5e3` (code); this report and the log follow |
| Iterations | 2 of 5 (iteration 1 found 6 FAIL; all fixed; iteration 2 found none) |

## Verdict

| Posture | Ready? | Why |
|---------|--------|-----|
| **Soft Launch** (Sports Routing in PRACTICE on the real HA; Matrix or a person drives the wall) | **Yes, with conditions** | Every PRACTICE gate is in code and tested. Conditions: deploy with the placeholder `inventory.json` (`REPLACE_ME`) and the boolean off; train staff from `docs/STAFF_TRAINING.md`, not the two staff PDFs (still pending rebuild); run HA `check_config` on the site host at install (not runnable here); tell staff Matrix is always live. |
| **Live** (Sports Routing Take changes the wall) | **No — BLOCKED** | Code gates PASS, but the wall, `msg_b_reconnect`, AV-LAN broadcast, Sunday channel set, and a real HA `returnResponse` round trip are unproven (BLOCK-SITE-\*). Once those pass on site, Live is single-iPad only until the server occupancy ledger exists. |

**Remaining FAIL: none.** Everything left is BLOCKED with a reason (PR-09b, PR-10).

## Results

| ID | Criterion | Iter 1 | Final | Fix |
|----|-----------|--------|-------|-----|
| PR-01 | Build / config check | PASS (HA `check_config` N/A) | **PASS** (HA `check_config` N/A) | — |
| PR-02 | Automated tests | PASS | **PASS** | — |
| PR-03 | No secrets / hardcoded credentials | **FAIL** | **PASS** | `60477b8` |
| PR-04 | Config / env vars documented | **FAIL** | **PASS** | `cf9c5e3` |
| PR-05 | Live path error handling and logging | **FAIL** (logging) | **PASS** | `4bf42db`, `4de70d1` |
| PR-06 | Dependency vulnerabilities | **FAIL** (dev floors) | **PASS** (scanner caveat) | `cf9c5e3` |
| PR-07 | Critical path performance | **FAIL** | **PASS** | `4de70d1` |
| PR-08 | Rollback path | **FAIL** | **PASS** | `8bcee90` |
| PR-09a | Soft Launch go criteria | PASS (conditional) | **PASS** (conditional) | — |
| PR-09b | Live go criteria | BLOCKED | **BLOCKED** | site |
| PR-10 | Phase 2 BLOCKED items | BLOCKED | **BLOCKED** | see table |

---

## Evidence

### PR-01 — Build / config check: PASS

There is no build step: no bundler, no `package.json`; the panel ships as plain ES modules.

| Check | Result |
|-------|--------|
| `python3 -m py_compile $(git ls-files '*.py')` | 50 files OK |
| `node --check` every tracked `.js` / `.mjs` | 19 files OK |
| Every tracked YAML (HA-tag loader from `validate_panels.py`) and JSON | 24 YAML + 4 JSON, 0 errors |
| `python3 scripts/validate_panels.py --config-dir homeassistant/config` | `Panel validation passed.` |
| HA `check_config` | **N/A here**: no Docker (`which docker` empty) and no `homeassistant` package (PyPI unreachable). Run `scripts/run_ha_panel_validation.sh` or `python -m homeassistant --script check_config` on the site host before Soft Launch. |

The new `trace: stored_traces: 50` key on the script was checked against HA's script schema (`homeassistant/components/script/config.py` accepts `CONF_TRACE` → `TRACE_CONFIG_SCHEMA`, read via `gh api`).

### PR-02 — Automated tests: PASS

| Suite | Start (`c02d617`) | Final (`cf9c5e3`) |
|-------|-------------------|-------------------|
| `node --test tests/js/*.test.js` | 107 pass / 0 fail | **107 pass / 0 fail / 0 skipped** |
| `python3 -m unittest discover -s tests -p 'test_*.py'` | 151 OK | **164 OK, 0 skipped** |

New Python tests: `tests/test_live_time_budget.py` (8), `test_live_interlock.py` trace test (1), `test_ha_staging_config.py` onboarding password tests (4). Each was run against the pre-fix code first: time budget 8 errors, trace 1 error, onboarding 3 failures + 1 error. `pytest` is not installed (PyPI unreachable); every module runs under unittest.

### PR-03 — Secrets and hardcoded credentials: FAIL → PASS

**Found.** `scripts/complete_ha_onboarding.py` had `DEFAULT_PASSWORD = "avaccess-staging"` and applied it as the HA owner password when run with no flags. Six docs published the pair `operator` / `avaccess-staging`, two of them next to "port-forward 8123" / "bind `0.0.0.0:8123`" instructions (`HA_STAGING_A2_CHECKLIST.md`, `HA_STAGING_STATUS.md`, plus `HA_QUICKSTART.md`, `DIRECTV_H25_PATCH_AND_TEST_PLAN.md`, `OPERATIONS_GUIDE.md`). `prepare_ha_staging.py` printed it. Anyone who ran the helper against a reachable HA got a published owner password.

**Fix (`60477b8`).** The password comes from `--password`, else `AVACCESS_HA_OWNER_PASSWORD`, else `secrets.token_urlsafe(18)` printed once after onboarding succeeds (not printed on failure). Dry-run prints `"password": "<redacted>"`. All doc mentions removed; the staging docs say to rotate the old value on any instance onboarded with it.

**Final scan** (run artifact `secrets_scan.log`):

| Scan | Hits |
|------|------|
| `password/secret/api key/bearer/private key = <value>` | only `args.password = from_env`, `args.password = secrets.token_urlsafe(18)`, a test value `"from-flag"`, and the word "Bearer" in a doc table |
| `ghp_`, `gh?_`, `sk-`, `AKIA`, `xox?-`, JWT, `BEGIN … PRIVATE KEY` | none |
| Credentials in URLs | none |
| `avaccess-staging` | only the regression test asserting it is gone |
| Tracked `.a2_auth*`, `secrets.yaml`, `.env`, `directv.yaml`, `.storage/` | none. `homeassistant/staging/config/.a2_auth.json` and `config/directv.yaml` are gitignored (`git check-ignore -v`). |
| Staff/operator PDFs | no `avaccess-staging` in decoded streams; their builders never contained it |

**Residual:** the old password stays in git history (no history rewrite; force-push is out of scope). It only ever protected staging instances; rotate it wherever it was used. Hostnames and IPs in `*.example.yaml` are placeholders (`REPLACE_ME`, `192.168.10.x`), not secrets.

### PR-04 — Config files and env vars documented: FAIL → PASS

**Found.** Config files were documented across `HA_LIVE.md` section 3 and README Track B/C, but there was no single reference, and two env vars had no documentation: `AVACCESS_DIRECTV_BROWSER_PROFILE` (`directv_sports.py`) and the screenshot script's `HA_BASE_URL` / `HASS_TOKENS` / `SHOT_DIR` / `ART_DIR` / `CHROME_PATH`.

**Fix (`cf9c5e3`).** README "Configuration reference": every config file (who reads it, what it holds, symlink/gitignore notes), the `inventory.json` Live gate, `input_boolean.avaccess_live_commit`, and every env var with its default (`git grep os.environ|getenv|process.env` finds no others). `config/directv.example.yaml` now explains the `timeout_seconds` ceiling.

### PR-05 — Error handling and logging on the Live path: FAIL → PASS

**Error handling (PASS at start).** Traced panel → `script.avaccess_live_execute` → `shell_command` → `run_execute_route_plan.py` → `execute_route_plan.py` → `directv_shef.py` / `udp_reconnect.py`:

- Boolean off → script returns `returncode` 3 and a JSON refusal without running the shell; wrapper refuses `--live` unless `--live-commit on` (exit 3).
- Preflight (inventory, H25 map, missing tune, bad base64) → `PreflightError` → JSON `ok:false`, exit 2, nothing sent.
- Per slot: SHEF HTTP error, connection failure, timeout, non-200 body status, nonzero `commandResult`, or `/tv/getTuned` mismatch → slot `error` before UDP; other slots continue; exit 1. Any other exception → JSON report, exit 2.
- Panel (`live-execute.js`): missing report, `ok:false`, nonzero exit, rejected `callService`, or no HA connection → error summary; occupancy only for `ok` slots.

**Logging (FAIL at start).** From HA source (`shell_command/services.py`, `trace/const.py`, via `gh api`): stdout/stderr are logged only at **debug**; a nonzero exit is logged at error; a 60 s timeout raises `HomeAssistantError` and discards the output; scripts keep **5** traces. So the only readable record of what a Live Take did was the last 5 script traces, and a timed-out Take left nothing.

**Fix.** `4bf42db`: `trace: stored_traces: 50` on `script.avaccess_live_execute`; each trace holds the executor's JSON report. `4de70d1`: report and every attempted slot carry `elapsedMs`; Takes no longer hit the 60 s kill (PR-07). `HA_LIVE.md` "How Live is gated" items 7–8 say where to read traces.

### PR-06 — Dependency vulnerabilities: FAIL → PASS (scanner caveat)

**Scanners.** Snyk MCP: namespace status `error` ("failed during live tool discovery"). `pip-audit` / PyPI: unreachable (`SSLEOFError`). Used the GitHub Advisory Database through `gh api graphql securityVulnerabilities` for every third-party import (full output in the run artifact `dependency_advisories.txt`).

| Package | Where | Spec | Advisories in range | Result |
|---------|-------|------|---------------------|--------|
| PyYAML | runtime (`requirements.txt`) | `>=6.0` | none (all fixed by 5.4) | PASS. All loads use `safe_load` or a `SafeLoader` subclass. |
| jinja2 | tests only (HA bundles its own) | was unlisted → `>=3.1.6` | ≤3.1.5 sandbox breakouts (moderate) | Fixed. Unlisted meant `test_live_interlock`'s HA template tests silently skip without it. |
| pytest | dev | was unpinned → `>=9.0.3` | <9.0.3 tmpdir (moderate) | Fixed |
| reportlab | PDF builders only | unlisted → `requirements-docs.txt >=3.6.13` | ≤3.6.12 RCE (high) | Fixed |
| pillow | PDF builders only | unlisted → `requirements-docs.txt >=13.0.0` | ≤12.3.0 several (critical/high) | Fixed |
| playwright | optional PC sports pull | unlisted | none | PASS |
| puppeteer-core (npm) | docs screenshot script | no `package.json` | none | PASS |

The panel has no npm dependencies. Caveat: the floors could not be installed here (PyPI blocked), and the PyYAML/jinja2 actually used on site come from the Home Assistant image, which this scan does not cover.

### PR-07 — Performance of critical paths: FAIL → PASS

**HA limit.** `COMMAND_TIMEOUT = 60` in `homeassistant/components/shell_command/services.py`; on timeout HA kills the process and raises `HomeAssistantError` (no stdout). The panel then marks every slot `error` and saves no occupancy, even for TVs that switched.

**SHEF worst case per slot.** `timeout_seconds` 4 × (1 tune + 3 `/tv/getTuned` polls) + 2 × 0.5 s = **17 s**. Nine slots could take 153 s.

**Measurement.** `python3 tests/bench_live_latency.py` runs the real wrapper (`--live --live-commit on`) against one local fake H25 per receiver and counts the UDP reconnects actually sent. 9 slots unless noted.

| Scenario | Before (`c02d617`) | After (`4de70d1`) |
|----------|--------------------|-------------------|
| healthy | 1.91 s, report, 9 ok, 9 UDP | 1.91 s, same |
| healthy, 10 slots | — | 2.12 s, 10 ok |
| one H25 hung | 5.72 s, 8 ok / 1 error | 5.71 s, same |
| all H25 hung | 36.13 s, 9 errors | 36.13 s, same (10 slots: 36.13 s, 10th "Not attempted") |
| slow verify, matches on 3rd poll | **killed at 60 s, no report, 5 TV groups switched** | 35.22 s, report: 3 ok + 6 "Not attempted", 3 UDP |
| slow verify, never matches | **killed at 60 s, no report** | 35.22 s, report: 9 errors, 0 UDP |

In every "after" run the UDP count equals the `ok` count, so the panel's occupancy matches the wall.

**Fix (`4de70d1`).** `execute_plan(live=True)` starts a slot only if elapsed + worst case ≤ 50 s (`--time-budget`, default 50; 10 s left for start-up and HA). Skipped slots: `Not attempted: the Live Take reached its 50 s time limit before this slot. Nothing was sent; these TVs keep their previous source.` A `timeout_seconds` whose worst case exceeds the budget fails preflight. SHEF verify latency on healthy boxes is ~0.2 s per slot (1.9 s for 9 including Python start-up).

### PR-08 — Rollback path: FAIL → PASS

**Found.** Rollback had two bullets (boolean off; restore `avaccess_matrix.yaml`). The HA OS update steps did not recopy `run_*.py` or `directv_shef.py`, which are copies there, not symlinks. Running the pre-WP-D wrapper from git history with today's arguments: `error: unrecognized arguments: --live-commit on`, exit 2, no report, so every Live Take fails. No backup step, so no code rollback.

**Fix (`8bcee90`), `HA_LIVE.md`.** Updating: turn Live commit off, back up panels/packages/dashboards/`configuration.yaml`/`avaccess/*.py` plus the git SHA, then recopy wrappers and Matrix CLIs; PRACTICE Take and one-TV smoke test before re-arming. Rollback, in order:

1. Live commit off: every iPad PRACTICE at once; a running Take finishes within 50 s; HA restart also leaves it off (`initial: false`).
2. Back to Soft Launch: put the placeholder `inventory.json` back; the button is disabled even if the boolean is turned on in Developer Tools (the script and shell check only the boolean, so keep it off too).
3. Restore the backup and the recorded SHA; restart HA; force-quit Companion.
4. Matrix has no switch: restore or `--ui-staging`-regenerate its package, or run the wall from VDirector and remotes.

### PR-09a — Soft Launch go criteria: PASS (conditional)

| Condition (`HA_LIVE.md` 7b) | Enforced by | Evidence |
|-----------------------------|-------------|----------|
| `REPLACE_ME` in `inventory.json` keeps Live off | `liveCommitFromStates` requires inventory ready | repo `inventory.json` has 90 `REPLACE_ME`; tests "panel never arms Live when inventory is not ready, even if the boolean is on", "banner stays PRACTICE when the boolean is on but inventory is not Live-ready" |
| Boolean off by default | `initial: false` | `avaccess_routing.yaml` line 25; script/wrapper refusal tests in `test_live_interlock.py` |
| PRACTICE banner on every iPad | `commitModeBanner`, resync on every `hass` update | `panel-render.test.js` banner tests; `live-commit-sync.test.js` |
| Practice never touches Live occupancy | separate stores, Clear wipes both | 6 `panel-send.test.js` store tests |
| No-channel / demo fallback blocked for Live | `takeBlockReason`, executor preflight | `panel-send.test.js`, `test_execute_route_plan_live_tune.py` |
| Staff instructions current | `STAFF_TRAINING.md` | Phase 2 S0-OFF-FICTION Markdown PASS; PDF links say "pending rebuild" |

Conditions that are not code: deploy with the placeholder `inventory.json`; train from `STAFF_TRAINING.md`; HA `check_config` on the site host; staff know Matrix is always live.

### PR-09b — Live go criteria: BLOCKED

Code-side gates all PASS (interlock, b64 safety, UDP re-enrich, SHEF status + verify, time budget, success-only occupancy, in-flight lock). Live still needs, on site: BLOCK-SITE-WALL, -RECONNECT, -BROADCAST, -SUNDAY-CH, and one real Live Take showing the script's `returnResponse` reaching the panel. Then Live is single-iPad (BLOCK-SERVER-LEDGER). The first-Live checklist is `HA_LIVE.md` 7b and section 9.

### PR-10 — Remaining BLOCKED items

| Item | Status | Reason now | Blocks |
|------|--------|-----------|--------|
| PDF rebuild / S0-OFF-FICTION | BLOCKED | `pip download reportlab` → SSL EOF to pypi.org; no apt package. `STAFF_QUICK_START.pdf` / `STAFF_FULL_GUIDE.pdf` still say "turn off" / "DRY-RUN". Rebuild: `pip install -r requirements-docs.txt && python3 scripts/build_staff_pdfs.py`. | Handing out PDFs. Soft Launch OK using `STAFF_TRAINING.md`. |
| BLOCK-SERVER-LEDGER | BLOCKED | Occupancy is per-iPad `localStorage`. Design work, not a small fix. | Multi-iPad Live |
| Real HA `returnResponse` | Gate path observed after this report | Live-off call returned `returncode` 3 through `return_response`. A Live Take that reaches the panel is still unproven. | Live |
| BLOCK-SITE-WALL | BLOCKED | No wall | Live |
| BLOCK-SITE-RECONNECT | BLOCKED | `msg_b_reconnect` eviction unknown | Live |
| BLOCK-SITE-BROADCAST | BLOCKED | Needs AV-LAN NIC / host network | Live |
| BLOCK-SITE-SUNDAY-CH | BLOCKED | 9554–9563 vs 705–713 | Live (Sunday) |
| HA `check_config` | Partial, after this report | Shipped config exits 0. Only warning is the missing frontend wheel. See the follow-up below. | Re-run on the site host |

---

## Iteration log

**Iteration 1** (at `c02d617`): PASS PR-01, PR-02, PR-09a; FAIL PR-03, PR-04, PR-05, PR-06, PR-07, PR-08; BLOCKED PR-09b, PR-10. All six FAILs were small (one module or doc section each), so all were fixed in this pass:

| Commit | Fix |
|--------|-----|
| `4de70d1` | PR-07/PR-05: 50 s Live budget, `elapsedMs`, timeout preflight, bench, 8 tests |
| `4bf42db` | PR-05: 50 stored Live traces, 1 test, `HA_LIVE.md` items 7–8 |
| `60477b8` | PR-03: no built-in owner password, 4 tests, 6 docs |
| `8bcee90` | PR-08: backup + recopy on update, ordered rollback |
| `cf9c5e3` | PR-04/PR-06: configuration reference, dev/doc requirement floors |

**Iteration 2** (at `cf9c5e3`): re-ran PR-01, PR-02, PR-03, the bench, and the criteria each fix touched. 0 FAIL. Stop.

## Commands run

```bash
python3 -m py_compile $(git ls-files '*.py')                       # 50 OK
for f in $(git ls-files '*.js' '*.mjs'); do node --check "$f"; done # 19 OK
python3 scripts/validate_panels.py --config-dir homeassistant/config
node --test tests/js/*.test.js                                     # 107 / 0
python3 -m unittest discover -s tests -p 'test_*.py' -v             # 164 OK
python3 tests/bench_live_latency.py                                # before/after table
git grep … (secret patterns above); git check-ignore -v …
gh api repos/home-assistant/core/contents/homeassistant/components/shell_command/services.py
gh api graphql -f query='{ securityVulnerabilities(ecosystem: PIP, package: "…") … }'
python3 -m pip download --no-deps reportlab                       # SSL EOF (BLOCKED)
```

## Follow-up after Home Assistant was running

`python -m homeassistant --script check_config` was not runnable when this report was written. With Core 2026.10.2 available it was run on the shipped directory:

| Config | Exit | Result |
|--------|------|--------|
| `homeassistant/config` | 0 | Successful config (partial). Warnings are only `frontend` and `panel_custom` missing `home-assistant-frontend==20260930.4` (no `uv`, GitHub release assets blocked). No failed config. |
| `homeassistant/staging/config` | 0 | Those frontend warnings, `default_config` missing stream wheels, and package `avaccess_matrix` (`template` is a list, so it cannot merge). |

The Live-off `return_response` call against the running instance returned `returncode` 3 and `Live Commit is off - refusing Live Send.` That covers the gate. It does not cover a Live Take whose report reaches the panel, and it does not clear BLOCK-SITE-\*. Run `check_config` again on the site host, where the frontend package is installed.
