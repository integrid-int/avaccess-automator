# Review plan — DirecTV SHEF / no-IR cutover

Hand this file to **Opus for planning** and **Fable for execution**. Do not start a rewrite. This is a review of work that already landed on a branch.

| | |
|--|--|
| **Review branch** | `origin/cursor/ha-staging-lovelace-harden-3db1` |
| **Base** | `origin/main` (`017d004`) |
| **Commits in scope** | `1bd9c0c` Align live Track B and docs with DirecTV SHEF (no IR) · `02d991b` Add photo PDF operators guide |
| **Product** | 10 DirecTV H25s → 10 AVAccess encoders → 35 TVs, iPad in Home Assistant |
| **Claim to verify** | Live operator path is DirecTV SHEF + UDP only. iTach / Xumo / IR is unused leftover, not wired. |

```bash
git fetch origin
git checkout cursor/ha-staging-lovelace-harden-3db1
git log --oneline origin/main..HEAD
git diff --stat origin/main...HEAD
```

---

## Part A — Opus (planning)

You are the review planner. Do **not** implement fixes unless Fable’s report says a blocker is trivial and in-scope. Produce a short **review brief** Fable can follow without guessing.

### A1. What this change is

A **patch**, not a new product:

- AVAccess presets, sports pages, favorites, and one/many TV routing stay.
- Source control moved from iTach IR (Xumo/Spectrum) to DirecTV H25 SHEF HTTP `:8080`.
- Track B Live Send must SHEF-tune then UDP `msg_b_reconnect` (not IR digits).
- Operator docs, inventory labels, Guide heading, and the PDF playbook must say DirecTV. No IR on the live path.

Two operator surfaces (both valid):

| Surface | Path | Role |
|---------|------|------|
| **Sports Routing** | `/panel-health` | Production bartender iPad. Striped Track A/B/C. |
| **AVAccess Matrix** | Lovelace `avaccess-matrix` | Favorites + contiguous Preset 1/2/3 (`numeric_v1`) + SHEF tune. |

### A2. Planning questions (answer these, then freeze Fable’s scope)

1. Is the **live execute path** SHEF-only, including HA `shell_command` wrappers, not just Matrix bundle generation?
2. Could an operator still fire IR by following current docs or default YAML?
3. Do tests actually lock the new path (`send_directv_tune`, `--directv-config`), or only rename strings?
4. Are leftover iTach files clearly unused, or still imported/required?
5. Does Guide EPG / weekly sync still assume Spectrum channel numbers while the UI says DirecTV majors? (data vs labels)
6. Is staging (`--ui-staging`) still stubbed so Fable does not treat STAGING Now Playing as a product bug?
7. Any secret, token, or live H25 IP in git / PDF / screenshots?

Write a 10-line **risk register** with severity (blocker / should-fix / leftover). That register is Fable’s priority order.

### A3. Out of scope for this review

- Physical H25 probe/tune on the AV LAN (tests B–E in `docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md`) unless a live lab is explicitly provided.
- Rewriting historical `docs/superpowers/**` task text (status banners are enough).
- Replacing XMLTV / weekly sync with a DirecTV guide dump (SHEF has no future EPG).
- Designing a new UI. Screenshots already exist.

### A4. Planning output (give this to Fable)

A one-page brief with:

- Ordered review slices (code → tests → docs → staging UI).
- Commands to run.
- The risk register.
- Report template (Part C).
- Merge recommendation rule: **no merge** if live Track B still requires `--itach-config` or docs tell operators to use IR.

If this file already contains that (Part B–C), Opus should **confirm or tighten** it, not duplicate a second plan.

---

## Part B — Fable (do the review)

You are the reviewer. Stay on `cursor/ha-staging-lovelace-harden-3db1`. File findings with file:line and severity. Do not “fix while reviewing” unless a finding is a one-line proof error in the report.

### B0. Setup

```bash
git fetch origin
git checkout cursor/ha-staging-lovelace-harden-3db1
python3 -m pip install -q pytest pyyaml
python3 -m pytest -q --tb=line
node --test tests/js/*.test.js
```

Expect ~54 Python tests and 32 JS tests passing (counts may move slightly). Any failure is a **blocker**.

### B1. Live Track B execute (highest priority)

Read and trace:

- `scripts/avaccess/execute_route_plan.py`
- `homeassistant/config/avaccess/run_execute_route_plan.py`
- `homeassistant/config/packages/avaccess_routing.yaml`
- `scripts/directv_shef.py`
- `tests/test_execute_route_plan.py`

| Check | Pass if |
|-------|---------|
| CLI requires `--directv-config`, not `--itach-config` | argparse + HA YAML + wrapper inject |
| Per slot: SHEF `/tv/tune` then UDP reconnect | `send_directv_tune` then `send_udp_reconnect` |
| Dry-run default; `--live` gated on inventory validation | hybrid posture unchanged |
| Slot errors continue; report JSON `ok` / `errors` | tests cover continue-after-failure |
| SHEF import works in repo **and** HA overlay (`directv_shef.py` next to executor) | `_load_shef_module` / wrapper `_ensure_directv_shef` |
| `SystemExit` from SHEF becomes per-slot error, not process abort | no whole-plan crash on one bad H25 |
| `ir_itach.send_ir_digits` is **not** called from execute | grep the executor |
| Docker compose overlays `scripts/directv_shef.py` onto `/config/avaccess/scripts/` | `homeassistant/docker-compose.yml` |

Fail this slice → **do not recommend merge**.

### B2. Matrix / bundle generator

Read `scripts/generate_ha_bundle.py`, `config/channels.example.yaml`, `tests/test_directv_shef.py`.

| Check | Pass if |
|-------|---------|
| Default transport is `directv_shef` | missing `ir_transport` does not fall back to `ha_remote` |
| Generated package emits `shell_command.avaccess_directv_tune` | not `avaccess_itach_send_channel` |
| `itach_tcp` / `ha_remote` still exist only as unused generators | leftover OK if unused by example YAML |
| Example channels keep `ir_transport: directv_shef` and `directv_config_path` | |

### B3. Operator-facing strings (no IR on the live path)

Grep the review branch (ignore `docs/superpowers/**` task bodies and `config/itach*.yaml` leftovers):

```bash
rg -n 'Xumo|Spectrum · ZIP|Live Send \(IR|iTach IR|--itach-config|send_ir_digits|source_label: "Xumo' \
  README.md docs scripts homeassistant/config config tests \
  --glob '!docs/superpowers/**' --glob '!config/itach*' --glob '!scripts/send_xumo*' --glob '!scripts/avaccess/ir_itach.py'
```

| Surface | Must say | Must not say (live path) |
|---------|----------|--------------------------|
| Guide heading `panel-health.js` | `DirecTV · ZIP 27403` | Spectrum · Xumo |
| Inventory `source_label` | `H25-01` … `H25-10 Spare` | `Xumo-*` |
| README Track B | SHEF then UDP | iTach IR then UDP |
| `docs/HA_LIVE.md` Sports Routing row | Live Send (SHEF + UDP) | Live Send (IR + UDP) |
| `docs/HA_QUICKSTART.md` | SHEF HTTP 8080 | “Xumo channel tune relies on IR” |
| `docs/HOME_ASSISTANT_CHANNELS.md` | DirecTV SHEF | Xumo + IR as current default |
| `docs/GLOBAL_CACHE_ITACH_SETUP.md` | unused leftover | “this project now supports iTach” as live |
| `homeassistant/config/www/avaccess/inventory.json` | H25 labels | Xumo labels |
| Operators PDF / `OPERATIONS_GUIDE.md` | DirecTV, no IR | IR blaster steps |

`panel-data.js` may keep the constant name `SPECTRUM_ZIP` (= `"27403"`) if the **visible** heading is DirecTV. Call that out as leftover naming, not a blocker.

### B4. Leftover IR files (allowed if quarantined)

These may remain:

- `scripts/send_xumo_ir_itach.py`
- `scripts/avaccess/ir_itach.py`
- `config/itach.example.yaml`
- generator branch `ir_transport: itach_tcp`

Pass only if **nothing on the live operator path requires them** (executor, routing YAML, HA_LIVE copy list, example channels). First lines should say unused / not live.

### B5. Docs vs code traps

| Trap | What to verify |
|------|----------------|
| Dual mapping profiles | Bartender uses `striped_v1` (inventory `active`). Matrix generator uses `--profile numeric_v1`. Both intentional. |
| HA path collision | `/config/avaccess/scripts` is Track B package **plus** overlay copies of `directv_shef.py`, `apply_preset.py`. `docs/HA_LIVE.md` must still describe that. |
| Staging vs live | `prepare_ha_staging.py --ui-staging` stubs shell to `echo STAGING`. Photos showing `STAGING - DirecTV not connected` are correct for staging, wrong for site HA. |
| Patch plan §F rollback | Older text told operators to set `itach_tcp`. Review branch should **not** restore IR as the documented rollback. Rollback = Live commit off / restore previous package. |
| Guide EPG numbers | `config/guide_epg.example.yaml` maps majors like `206`, `4`. Confirm comments say DirecTV, and flag if XMLTV map is still Spectrum IDs with DirecTV labels (data debt, not necessarily blocker). |
| Weekly sync | `docs/WEEKLY_SCHEDULE_SYNC.md` should say DirecTV majors, not Spectrum package numbers. |
| Panel cache bust | `configuration.yaml` `module_url` `?v=15` matches `panel-health.js` import query strings. |

### B6. Tests to read, not just run

- `tests/test_execute_route_plan.py` — sequence is `shef` then `udp`; CLI uses `--directv-config`; dry-run against `directv.example.yaml` needs no network.
- `tests/test_directv_shef.py` — parse_channel, tune URL, bundle emits SHEF not iTach.
- `tests/js/panel-shell.test.js` — Guide heading regex is DirecTV; import URLs allow `?v=N`.
- Confirm **no** test still mocks `send_ir_digits` on the executor.

### B7. Operators PDF / screenshots (commit `02d991b`)

- `docs/AVACCESS_OPERATORS_GUIDE.pdf` exists and matches `docs/OPERATIONS_GUIDE.md`.
- Photos show Sports Routing Guide **DirecTV · ZIP 27403**, Matrix **Now Playing (DirecTV)**, sidebar both surfaces.
- PDF does not embed credentials. Staging login `operator` / `avaccess-staging` may appear in markdown as the known staging owner — OK. Must **not** appear in screenshots of filled password fields.
- Capture scripts (`scripts/capture_operator_screenshots.mjs`, `scripts/build_operator_guide_pdf.py`) must not commit `/tmp/hassTokens.json`.

### B8. Staging / UI (if HA is up)

If `http://127.0.0.1:8123` is running with staging config:

- Sidebar: AVAccess Matrix **and** Sports Routing.
- Matrix Control: FOX Local, presets, Program A–I, DirecTV Now Playing.
- Sports Routing → Guide heading DirecTV.
- Activity after favorite/route shows scripts **Ran** (STAGING echo is OK).

If HA is down, skip this slice and say so. Do not fail the review solely for a stopped container.

### B9. Security / safety

- No long-lived HA tokens in git.
- Example H25 IPs are placeholders (`192.168.10.151`–`.160`), not a customer secret.
- SHEF is HTTP (not HTTPS) on the AV LAN — note as known limit, not a new finding unless the patch made it worse.
- `execute_route_plan` `--live` must not run from staging stubs against real gear.

---

## Part C — Fable report template

Return **one** markdown report with these sections.

```markdown
# Review report — DirecTV SHEF / no-IR

**Branch:** cursor/ha-staging-lovelace-harden-3db1
**Base:** origin/main (017d004)
**Tests:** Python N passed / JS N passed
**Merge recommendation:** approve | approve-with-nits | block

## Blockers
- [ ] file:line — …

## Should-fix before prod
- [ ] file:line — …

## Leftover / non-blocking
- [ ] SPECTRUM_ZIP constant name, historical superpowers docs, quarantined iTach files, …

## Live-path verdict
Track B execute: SHEF then UDP / still IR / mixed
Matrix bundle default: directv_shef / other
Docs tell operators to use IR: no / yes (cite)

## Open product risks (not this patch)
- Guide EPG / weekly sync lineup IDs vs DirecTV majors
- Site go-live still needs real H25 IPs, host-net UDP 5010, SHEF External Access
```

### Merge rule

- **Block** if live execute still requires iTach, or operator docs still instruct IR as the live path, or tests fail.
- **Approve-with-nits** if live path is SHEF and leftovers are clearly quarantined.
- **Approve** only if B1–B6 are clean and leftover IR cannot be reached from example config + HA_LIVE steps.

---

## File map (reviewers)

| Area | Files |
|------|--------|
| Live execute | `scripts/avaccess/execute_route_plan.py`, `homeassistant/config/avaccess/run_execute_route_plan.py`, `homeassistant/config/packages/avaccess_routing.yaml` |
| SHEF client | `scripts/directv_shef.py`, `config/directv.example.yaml`, `config/directv.yaml` (symlink) |
| Matrix bundle | `scripts/generate_ha_bundle.py`, `config/channels.example.yaml` |
| Bartender UI | `homeassistant/config/www/panels/panel-health.js`, `panel-data.js` |
| Inventory labels | `config/inventory.example.yaml`, `homeassistant/config/www/avaccess/inventory.json` |
| Go-live / ops | `docs/HA_LIVE.md`, `docs/HA_QUICKSTART.md`, `docs/OPERATIONS_GUIDE.md`, `docs/AVACCESS_OPERATORS_GUIDE.pdf` |
| Tests | `tests/test_execute_route_plan.py`, `tests/test_directv_shef.py`, `tests/js/panel-shell.test.js` |
| Quarantine IR | `scripts/avaccess/ir_itach.py`, `scripts/send_xumo_ir_itach.py`, `config/itach.example.yaml`, `docs/GLOBAL_CACHE_ITACH_SETUP.md` |

Related context (not the diff, but needed to judge intent): `docs/PLAN.md`, `docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md`, `docs/HA_STAGING_A2_CHECKLIST.md`.
