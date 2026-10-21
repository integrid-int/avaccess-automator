# Phase 3 — Production readiness plan

| Field | Value |
|-------|-------|
| Date | 2026-10-21 |
| Branch | `cursor/remediation-2026-10-21-af45` (never `main`) |
| Starting HEAD | `c02d617` (Phase 2 iteration 2: 20 PASS, 0 FAIL, 2 BLOCKED) |
| Report | `docs/prod-readiness-report.md` |
| Loop cap | 5 fix/re-verify iterations |

**Target posture.** Soft Launch now: staff use Sports Routing in PRACTICE on the real HA while Matrix or a person drives the wall. Live (Sports Routing Take changes the wall) stays gated on site proof (BLOCK-SITE-\*). This plan grades both postures separately.

**Status values.** PASS: criterion met with evidence from this run. FAIL: not met and fixable in the repo. BLOCKED: not met and cannot be fixed or proven from this environment; the reason is recorded. N/A: does not apply, with the reason.

---

## Criteria

| ID | Criterion | Method | PASS when |
|----|-----------|--------|-----------|
| PR-01 | Build / config check passes clean | `python3 -m py_compile` on every tracked `.py`; `node --check` on every tracked `.js`/`.mjs`; parse every tracked YAML (HA tag-tolerant loader from `validate_panels.py`) and JSON; `scripts/validate_panels.py --config-dir homeassistant/config`; HA `check_config` if Docker or a local `homeassistant` install exists | All static checks clean. HA `check_config` either clean or recorded N/A with the reason (no Docker, no HA package). There is no build step (no bundler, no `package.json`). |
| PR-02 | All automated tests pass | `node --test tests/js/*.test.js`; `python3 -m unittest discover -s tests -p 'test_*.py' -v` | 0 fail, 0 error; record counts and any skips |
| PR-03 | No secrets or hardcoded credentials in tracked files | `git grep` over tracked files for password / token / secret / api key / bearer / private key patterns, known token prefixes (`ghp_`, `sk-`, `AKIA`, `xox*-`, JWT `eyJ…`), credentials in URLs, and the staging owner credentials; list symlinks and check what gitignored files hold (`.a2_auth.json`, `config/directv.yaml`) | No real secret, and no default password in code or docs that a script would apply to an HA instance |
| PR-04 | Config files and env vars documented | List every config file the code reads and every `os.environ` / `process.env` lookup; check each is described in `README.md` or `docs/HA_LIVE.md` | Every runtime config file and env var is documented with its purpose |
| PR-05 | Error handling and logging on the Live path | Read panel → `script.avaccess_live_execute` → `shell_command` → `run_execute_route_plan.py` → `execute_route_plan.py` → `directv_shef.py` / `udp_reconnect.py`; confirm against HA `shell_command` and `script` source (via `gh api`) what is logged and kept | Every failure becomes a slot or report error the panel shows; nothing marks a slot `ok` without SHEF success; a Live Take leaves a record an operator can read after the fact |
| PR-06 | Dependency vulnerabilities | Snyk MCP if reachable; else GitHub Advisory Database (`gh api graphql securityVulnerabilities`) for every third-party import; `pip-audit` if PyPI reachable | Runtime deps have no open advisory in the allowed range; dev/doc-tool floors exclude known-vulnerable versions; scanner gaps recorded as BLOCKED with reason |
| PR-07 | Performance of critical paths | Read HA `shell_command` source for its timeout; time the real executor CLI (via `run_execute_route_plan.py --live --live-commit on`) against a local fake SHEF server for healthy, offline, hung, and slow-verify H25 cases, 9 slots | Worst-case Live Take finishes and prints its report inside HA's 60 s `shell_command` timeout, so the panel never loses a report for TVs that did switch. Healthy 9-slot Take well under 10 s |
| PR-08 | Rollback path | Read `docs/HA_LIVE.md` rollback, Soft Launch (7b), update procedure, and the gating code | Documented, ordered rollback for: Live boolean off; back to Soft Launch (inventory gate); code/panel rollback; Matrix vs Sports Routing. Update procedure does not leave stale copies that break Live |
| PR-09a | Soft Launch go criteria | Check the 7b conditions are enforced in code (inventory gate, boolean default off, PRACTICE banner, separate occupancy stores) and that staff docs exist | All enforced by code + tests; staff instructions current in Markdown |
| PR-09b | Live go criteria | Same, plus site proof | Code gates PASS **and** BLOCK-SITE-\* proven on site |
| PR-10 | Remaining BLOCKED items from Phase 2 | Re-check each: PDF rebuild / S0-OFF-FICTION, BLOCK-SERVER-LEDGER, real HA `returnResponse`, BLOCK-SITE-WALL / RECONNECT / BROADCAST / SUNDAY-CH | Each either cleared or still BLOCKED with a current reason and the posture it blocks |

## Commands

```bash
git checkout cursor/remediation-2026-10-21-af45
python3 -m py_compile $(git ls-files '*.py')
for f in $(git ls-files '*.js' '*.mjs'); do node --check "$f"; done
python3 scripts/validate_panels.py --config-dir homeassistant/config
node --test tests/js/*.test.js
python3 -m unittest discover -s tests -p 'test_*.py' -v
git grep -nIiE '(password|passwd|secret|token|api[_-]?key|bearer|private[_-]?key)'
git grep -nIE '(eyJ[A-Za-z0-9_-]{10,}\.|ghp_|gh[ousr]_|sk-[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16}|xox[baprs]-|BEGIN [A-Z ]*PRIVATE KEY)'
gh api graphql -f query='{ securityVulnerabilities(ecosystem: PIP, package: "pyyaml", first: 30) { … } }'
python3 tests/bench_live_latency.py          # fake SHEF latency scenarios
```

## Fix loop

1. Run every criterion; write the report.
2. For each remediable FAIL: fix now if it is small (one module or doc section, with a test where code changes). Larger fixes become listed tasks; implement the ones that affect Live safety or Soft Launch.
3. Re-run PR-01, PR-02, and the criteria the fix touched. Update the report.
4. Stop when no remediable FAIL remains (max 5 iterations). Everything left is BLOCKED with a reason.

## Known going in

- PDF rebuild BLOCKED: `reportlab` not installable (PyPI SSL EOF).
- BLOCK-SERVER-LEDGER: occupancy is per-iPad `localStorage`; Live is single-iPad.
- BLOCK-SITE-\*: no real wall, H25, AVAccess switch, or AV-LAN NIC here.
- No Docker and no `homeassistant` package in this VM, so HA `check_config` and a real `returnResponse` round trip cannot run here.
