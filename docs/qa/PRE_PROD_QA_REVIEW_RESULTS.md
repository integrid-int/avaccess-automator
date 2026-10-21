# Pre-Production QA Review Results — AVAccess Automator

**Status:** PARTIAL — 7/10 specialist reports merged; 3 still running  
**Plan:** [PRE_PROD_QA_REVIEW_PLAN.md](./PRE_PROD_QA_REVIEW_PLAN.md)  
**Review branch:** `cursor/pre-prod-qa-review-af45`  
**Code under review:** `main` @ `e2f97d3`  
**Constraint:** No product code changes this pass  

---

## Executive verdict (interim — 7 specialists in)

| Question | Interim answer |
|----------|----------------|
| Enable **Live Send** on next game day? | **NO-GO** — S0 reuse/replace wall semantics + silent Live failure + per-iPad occupancy; Security S1s unfixed |
| Soft Launch (**dry-run only**) on iPad? | **Conditional GO** — fix scroll-jump if present on site; correct training “off” copy; PRACTICE label; visual token/logo/fold; Matrix off bartender iPads |
| Overall | Dry-run training only; `HA_LIVE.md` alone insufficient until S0/S1 ops gaps closed |

Strong convergence: reuse of a busy encoder blanks/retunes unintended TVs physically while UI says “off”; Live Take often looks successful without wall truth; occupancy is browser-local.

---

## Automated test gate (coordinator)

| Suite | Result | Evidence |
|-------|--------|----------|
| `node --test tests/js/*.test.js` | **39/39 pass** | `/opt/cursor/artifacts/node-test-results.txt` |
| `pytest tests/` | **BLOCKED** | PyPI HTTPS SSL failure in review VM |
| Snyk dependency scan | **BLOCKED** | MCP namespace error |
| Live HA / computerUse UI | **NOT RUN** | No AV-LAN HA in this environment |

---

## Specialist agent roster

| Workstream | Agent | Status |
|------------|-------|--------|
| Security | [Security pre-prod review](bc-4fe1d506-1809-5ca8-b2d9-f3f4c3d90243) | **merged** |
| Reliability | [Reliability failure-mode review](bc-5eb95651-bb29-5c1c-ad45-b2b9e4d3388c) | running |
| UI interaction | [UI interaction review](bc-99819c78-c158-53b9-b984-00e1d13dcaf3) | **merged** |
| Visual design | [Visual design review](bc-66c2e031-218f-512f-8cc1-66e105ce4588) | **merged** |
| Overall design | [Architecture overall design](bc-89a16bb0-f850-5cf8-a281-b693cccb3c34) | running |
| Codebase | [Codebase structure audit](bc-1fa21211-ce44-5de7-879c-8c7acfe0677e) | **merged** |
| Senior developer | [Senior developer ship review](bc-a29dd362-80ee-5ac7-aaba-d5d2f452b43e) | running |
| Owner persona | [Owner persona review](bc-9b5be436-b5b1-53c3-b713-f818d583b824) | **merged** |
| Bartender persona | [Bartender persona review](bc-8802d5da-4b0b-5150-a485-c06a9cfb4d6e) | **merged** |
| Ops runbook | [Ops runbook audit](bc-9baef8d3-bb96-5b62-b377-f795aa99cf2a) | **merged** |

---

## Coordinator seed findings (superseded where noted)

| ID | Severity | Status vs specialists |
|----|----------|----------------------|
| SEC-C1 unquoted `plan_b64` | S1 | **Confirmed** by Security as S1 |
| SEC-C2 client-only Live gate | S1/S2 | **Confirmed** — Security elevates boolean non-enforcement to S1 |
| REL-C1 occupancy before Live ack | S2 | Aligns with Owner S0 “Now vs wall” |
| REL-C2 SHEF-fail skips UDP | OK | Security/coordinator agree |
| OPS-C1 Docker bridge UDP | S1 ops | Still open (Ops agent pending) |
| OPS-C2 inventory example symlink | S1 deploy | Confirmed by Security/Owner |
| UI-C1 Spectrum vs DirecTV | S3 | Open (UI agent pending) |
| Visual tokens / logos | — | **Elevated** by Visual to Critical/High |
| CODE-C1/C2 monolith + dup trees | S2/S3 | Open (Codebase agent pending) |

---

## 1. Security review

**Source:** [Security pre-prod review](bc-4fe1d506-1809-5ca8-b2d9-f3f4c3d90243)  
**Verdict:** Dry-run **GO**; Live **NO-GO** without S1 fixes (or explicit acceptance of API-level risk + trusted-only HA users).

### S1 findings

1. **Live executor trusts caller-supplied UDP hostnames** when plan slots pre-populate `udp` (enrich only if any `udp: null`). Panel always sets `udp: null` (safe). Any `shell_command` caller with forged `udp` + valid `encoderId` can wrong-route on AV LAN.  
   - *Fix direction:* Always re-enrich from inventory on `--live`, or verify plan `udp` equals inventory.

2. **Unquoted `{{ plan_b64 }}` / `{{ sets_b64 }}` in `shell_command`** (`avaccess_routing.yaml`) → `/bin/sh -c` injection if arbitrary service data. Panel `btoa` alphabet is safe; API/Developer Tools is the vector.  
   - *Fix direction:* stdin/temp file, `| quote`, reject non-base64 in wrapper.

3. **No server-side enforcement of `input_boolean.avaccess_live_commit`.** Python/shell only honor `live:` service field. Panel toggle is local state; boolean is UX-only.  
   - *Fix direction:* HA script gate requiring boolean on, or equivalent server check.

### S2 findings

4. Panel `require_admin: false` + `shell_command` from panel widens who can Live-route.  
5. Client Live gate via public `inventory.json` is UX only (server YAML preflight still required — good).  
6. Writable `/config/www/avaccess/*.json` poisonable by shell_command callers.  
7. Logo `img src` escaped but not URL-allowlisted (`javascript:` conditional on JSON write).

### Cleared / low

XSS on normal paths largely escaped; SSRF not attacker-controlled from panel; `directv.yaml` gitignored; path traversal on TV sets bounded; SHEF/UDP unauthenticated is LAN design assumption.

### Security must-fix before Live (ordered)

1. Bind UDP from inventory on live  
2. Fix shell interpolation of b64  
3. Server-side live commit enforcement  
4. Lock HA AuthZ (admin Companion or deny shell_command to bartender users)  
5. Real inventory + directv on host; matching inventory.json  
6. AV VLAN segmentation  
7. HA 8123 auth/TLS if beyond trusted LAN  
8. Automate inventory JSON export  
9. Logo URL allowlist  
10. Host-network UDP proof  

---

## 2. Reliability review

_Pending — [Reliability failure-mode review](bc-5eb95651-bb29-5c1c-ad45-b2b9e4d3388c)._

---

## 3. UI review

**Source:** [UI interaction review](bc-99819c78-c158-53b9-b984-00e1d13dcaf3)  
**Verdict:** Soft Launch **conditional GO**; Live **NO-GO**. JS tests 39/39; planner simulation confirmed S0/S1.

### S0

1. **Pick one TV / named set can retune every TV on that box** — `singleEncoderForTvs` before free encoders; Take line does not warn; training presents as normal.

### S1

2. **“Off” in UI ≠ off on wall** — executor never disconnects `replaced`/`leftover` TVs; they keep showing retuned box. Training copy wrong.  
3. **Failed Live Take looks like success** — no `returnResponse`; occupancy saved first; Take stays tappable (double-send).  
4. **No-channel games still Takeable** — 212/552 games lack channel; Live routes to untuned box.  
5. **Scroll jump** — `hass` → full `innerHTML` re-render; risk wrong-row tap under HA state churn (verify on site).  
6. **Matrix looks like practice, fires live** — separate occupancy; undermines dry-run training.

### S2–S4

Guide/Now/Sets buried; 4/9 Programs lack order map; Replace impact hidden; Guide search empty/keyboard issues; weak Live commit control; demo sports fallback without banner; small TV cells; practice occupancy pollutes Live; Take/Send label mix; Spectrum/Xumo spec drift; dual-entry not exclusive; preset naming drift.

### Soft Launch conditions (UI)

- Confirm/fix scroll jump on site HA  
- Correct training “turn off / stay showing” lines  
- Keep Matrix off bartender iPads (or explicit live-surface training)  
- Clear practice occupancy each shift  

### Live blockers (UI)

Free-box preference or pre-Take warn; physical re-route or stop calling TVs “off”; Live report + post-success occupancy + busy state; block no-channel Take; HA-enforced Live gate + reset; single-TV wall proof.

---

## 4. Visual design review

**Source:** [Visual design review](bc-66c2e031-218f-512f-8cc1-66e105ce4588)  
**Verdict:** Soft Launch **conditional GO** after three visual fixes; Live **NO-GO** until Live-state clarity + occupancy contrast + spec governance.

### Critical

1. **Approved Graphite+Cyan spec vs shipped Charcoal+Blue** — product restyled (`97a274b`); spec still “Approved”; Operations guide shows old screenshots; Staff training shows new UI. Governance blocker for Live.  
2. **CSS custom properties never resolve** — styles via `innerHTML` without shadow root; `:host { --cyan… }` unused. Active chip / Live toggle states wrong (active chip can look less active). Highest staff-error consequence once Live exists.

### High

3. Team logos broken; no initials fallback (spec required).  
4. Guide / Now / Sets and TVs 22–35 below fold at iPad landscape ~1024×637.  
5. Occupied vs empty TV contrast ~1.26:1.  
6. Selection relies on hue alone (~2.14:1).

### Medium / Low

Competing accents; dual dead CSS systems in `panel-health.js`; duplicated status lines; chip clutter vs 6-sport spec; Matrix action keys always lit; pretty dashboard install trap; leftover orange test theme; typography inconsistency.

### Soft Launch must-fix (visual)

- Make tokens resolve (shadow root or move vars to `.routing`)  
- Logo initials fallback  
- Keep Guide/Now/Sets + all 35 TVs reachable without critical scroll loss  

### Live must-fix (visual)

All Soft Launch items + unmistakable PRACTICE/LIVE banner; occupied TV ≥3:1 or pattern; non-hue selected cue; Matrix action-key latch; re-approve or rewrite spec + refresh Operations screenshots.

---

## 5. Overall design review

_Pending — [Architecture overall design](bc-89a16bb0-f850-5cf8-a281-b693cccb3c34)._

---

## 6. Codebase review

**Source:** [Codebase structure audit](bc-1fa21211-ce44-5de7-879c-8c7acfe0677e)  
**Verdict:** Live **NO-GO**. Dry-run reasonable. Senior code-health **4/10**. Symlink layout is canonical (not duplicated source); UDP logic still duplicated across Matrix CLIs.

### S0

1. Reuse/replace changes unselected physical TVs (`offTvs` browser-only; executor ignores `replaced`).  
2. Free-encoder authority is per-browser `localStorage` — empty/stale iPad can retune ENC-01 in use.

### S1

3. Live boolean not server interlock; `require_admin: false`.  
4. Matrix `apply_preset` partially routes before full validation fails.  
5. Track B trusts caller-supplied UDP hostnames (confirmed runtime).  
6. SHEF JSON without success `status.code` still proceeds to UDP.  
7. Untunable games Live-routable (`tune: null` still reconnects).  
8. Browser state committed before physical outcome.  
9. No single-flight / idempotency.

### S2–S4

`panel-health.js` monolith; panel-shell tests are regex-only; `validate_panels.py` shallow; inventory symlink + Quickstart `cp` trap; sports no freshness guard; iTach dead path broken in deploy topology; staging misses `avaccess_routing.yaml`; Spectrum naming drift; unpinned deps / floating `:stable`.

### Coverage gaps (high)

`panel-health` workflows, concurrency, Live auth, pre-enriched UDP rejection, SHEF status/verify, physical reuse/replace, Matrix preset atomicity, sports staleness, full HA deploy CI.

### Positives

Canonical symlink tree; pure planner/assignment tests; placeholder defaults; strong sports/guide fixture tests; detailed ops docs.

---

## 7. Senior developer perspective

_Pending — [Senior developer ship review](bc-a29dd362-80ee-5ac7-aaba-d5d2f452b43e)._

---

## 8. Bar / restaurant owner perspective

**Source:** [Owner persona review](bc-9b5be436-b5b1-53c3-b713-f818d583b824)  
**Verdict:** **Do not** make Live the default for opening weekend. Approve limited Live only after controlled real-wall tests + manager controls.

### S0 (owner blockers)

1. Live never proven on real wall; inventory still example/`REPLACE_ME`; staging was echo-only.  
2. **“Now” can disagree with the wall** — panel applies plan locally before Live ack; HA often returns no stdout; occupancy is per-iPad. Silent wrong-TV is the worst guest outcome.  
3. Any bartender can flip Live — no confirm, no manager PIN.

### S1

4. Two surfaces (Sports Routing practice vs Matrix real) + docs disagree; staff PDFs cover Routing only.  
5. No named game-day owner / on-call.  
6. Manual update risk mid-season; no freeze rule.  
7. Docker bridge UDP trap.  
8. Single HA + single iPad SPOF; no panic “all to local FOX” independent of Routing.

### S2–S4

Sports list morning scrape fragility; blackout/feed guidance missing; training retention; named sets sync silent fail; zone TBD; staging passwords must never hit bar HA; jargon (“commit”).

### Owner conditions before Live (abbreviated)

1. Written one-TV → 10 → 35 real-wall pass  
2. Completed inventory, physical TV map  
3. Manager-only Live + persistent PRACTICE/LIVE banner  
4. “Now” reflects reality or shows last-verified; human wall check after big switches  
5. One-button all-to-local-FOX fallback  
6. Named on-call + Sunday window  
7. No updates Thu–Mon game weekends  
8. Two trained staff/shift with sign-off; docs say which screen is real  
9. Failure rehearsal (unplug box / kill net / restart HA)  
10. Spare iPad + config backup + one-page down card  

---

## 9. Bartender / server perspective

**Source:** [Bartender persona review](bc-8802d5da-4b0b-5150-a485-c06a9cfb4d6e)  
**Verdict:** Soft Launch only. Not Live. Unusable as a rush tool until Take moves TVs (or is unmistakably labeled practice).

### Tap counts (code/docs)

| Goal | Approx taps |
|------|-------------|
| Game on every TV | 4–6 (sport→game→All 35→Take→Dismiss) |
| Game on Patio | ~5 |
| Game on 4 specific TVs | ~9 + Dismiss |
| Guide channel | Guide buried in rail + keyboard + row + dest + Take |

Best case ~3 once on the right sport; Take clears selection so multi-zone same-game needs two full passes.

### S0

1. **Take is practice** — Live off, inventory `REPLACE_ME`; PDFs say wall will not change. Unusable mid-rush.  
2. **Matrix actually fires** while handouts steer staff to Sports Routing only — wrong app is the real one.

### S1

3. **Silent box takeover** — Patio after All-35 can reuse ENC-01 and report `replaced: … off 32 TVs` even with free encoders; Take line does not warn.  
4. Fixing one TV can retune whole shared box.  
5. **Now = planned localStorage**, not picture truth; stale plans feed Replace choices.  
6. No undo / tap-Now-to-fix; only full re-pick.  
7. Same labels, different layouts: Matrix contiguous vs Routing striped “4 Programs”; FOX naming drift across dashboards.

### S2–S4

Guide/Now/Sets buried under ~17 rail buttons; jargon (Take, Live commit, Dry-run, ENC-01); Delete set no confirm; named set can’t tweak grid in place; no live double-tap guard; sets per-iPad; small grey text / dense TV grid / portrait unverified; stale PDFs; unreachable old screens in `panel-health.js`.

### Top 5 bartender demands

1. Label PRACTICE on Take until Live; then per-box Sending/On/Failed + block double-tap  
2. Never silently blank other TVs — free box first, or red “turns OFF N TVs” + second confirm  
3. Recovery: tappable Now, Undo, panic restore; confirm All-35  
4. One vocabulary / one staff app; zone-first (Patio); drop Preset/Programs/commit jargon  
5. Pin Guide/Now/Sets; larger TV targets; Delete confirm; glare-friendly contrast; real iPad test  

---

## 10. Ops / go-live runbook audit

**Source:** [Ops runbook audit](bc-9baef8d3-bb96-5b62-b377-f795aa99cf2a)  
**Verdict:** `HA_LIVE.md` **not sufficient alone** for production. Integrator can boot HA OS path and one-TV smoke; missing emergency/fallback, freeze, solid rollback; Docker path broken/contradictory.

### S0

1. **Failed Live Take looks successful** — `callService` without `returnResponse`; nonzero exit not surfaced; occupancy saved pre-call; runbook never requires HA log/wall check after Live Take (only step-7 one-TV visual).

### S1

2. **Docker live path self-contradicts** — relative paths from wrong cwd; checked-in compose is bridge test stack; UDP silent-fail; `/config` as checkout vs “don’t clone over `/config`”.  
3. **Tracked placeholder inventory symlink** — `git pull` / reset restores `REPLACE_ME`; panel JSON gate can disagree with YAML; gate never checks `directv.yaml`.  
4. **`HA_QUICKSTART.md` `cp` without `--remove-destination`** edits example via symlink (HA_LIVE correct).  
5. **Live commit ownership unclear** — per-iPad memory; one-way sync from boolean; staff guides say can’t turn on; no live-ops handout.  
6. **No emergency procedure** — HA/iPad/Wi-Fi down, frozen H25, black wall, VDirector only in PLAN.md.  
7. **Rollback incomplete** — no backup step before Matrix overwrite; Matrix always-live no kill switch.  
8. **No change freeze** — scripts symlink means `git pull` hot-swaps executor; tracks `main` not tag.

### S2–S4

Stale CLI copies on update; network L2/broadcast underspecified; 60s shell timeout on multi-SHEF; two occupancy truths; staging/live confusion + published staging creds; test plan vs ops guide live-pointing contradiction; unowned daily data jobs; `:stable` unpinned; missing backup/timezone/iPad Guided Access checklist items.

### Game-day emergency checklist gaps (none exist today)

Pre-game probe; Live Take wall/log confirm; manual fallback; H25 reboot/spare ENC; black-wall UDP/FOX reset; Live kill procedure; freeze window; escalation contacts; rollback artifacts; staff vs manager vs integrator ownership split.

---

## Aggregated must-fix backlog (interim — 7 specialists)

### Block Live Send

1. **S0 UI/CODE/FOH** Prefer free encoder or hard warn+confirm before shared-box reuse; physical detach/black for “off” TVs or stop claiming off  
2. **S0 CODE** Centralize occupancy (or single-iPad + hard reset SOP) — no per-browser free-ENC authority for Live  
3. **S0 OPS/UI** Surface Live failures (`returnResponse` / job entity); save occupancy only after success; busy/double-tap guard  
4. **SEC** Always bind live UDP from inventory; quote/validate b64; server-enforce live boolean  
5. **SEC/OWN** Manager-only Live AuthZ  
6. **CODE** Validate SHEF status before UDP; block no-channel Live Take; Matrix `apply_preset` full preflight  
7. **OPS/OWN** Real inventory+directv; host-network UDP; written one-TV→35 proof  
8. **OPS** Emergency/freeze/rollback addendum to HA_LIVE; fix Docker path or document HA OS only  
9. **OWN/FOH/VIS** PRACTICE/LIVE on Take; Matrix vs Routing staff story  
10. **VIS** Resolve CSS tokens for Live/chip state  

### Soft Launch (dry-run) gate

1. **UI** Confirm/fix scroll jump on site HA  
2. **UI/FOH** Correct training “off/stay showing” copy; clear practice occupancy each shift  
3. **VIS** CSS tokens; logo fallback; Guide/Now/Sets + TV fold  
4. **FOH** PRACTICE on Take; Live off; Matrix off bartender iPads (or explicit training)  
5. Fix Quickstart inventory `cp` trap; mark stale Operations screenshots  

### Before first big event

- Change freeze + HA backup before pulls  
- Panic all-to-FOX + spare iPad  
- Sports freshness banner; Delete confirm  
- Re-approve visual system; deepen panel behavioral tests / CI  
- Staging must include routing package if used for Live rehearsal  

---

## Handoff for next agent

1. Wait for remaining 7 specialist merges into this file, then freeze verdict  
2. Remediation branch from `main`; fix S0/S1 first  
3. Re-run `node --test tests/js` + full pytest after fixes  
4. Do not enable Live on opening weekend without Owner conditions 1–6  

---

## Appendix A — Artifact paths

- Plan: `docs/qa/PRE_PROD_QA_REVIEW_PLAN.md`  
- Results: `docs/qa/PRE_PROD_QA_REVIEW_RESULTS.md`  
- Node test log: `/opt/cursor/artifacts/node-test-results.txt`  
- Test gate notes: `/opt/cursor/artifacts/automated-test-gate.md`  

## Appendix B — Change log

| When | What |
|------|------|
| Review start | Plan authored; 10 agents dispatched; node 39/39; pytest/Snyk blocked |
| Partial merge | Security, Visual, Owner reports merged; interim NO-GO for Live |
| +Bartender | FOH Soft Launch only; silent encoder-reuse blanking elevated; Matrix vs Routing staff trap |
