# Pre-Production QA Review Plan — AVAccess Automator

**Status:** Active — final pass before production deploy  
**Product:** iPad bartender Sports Routing panel + AVAccess Matrix (Home Assistant)  
**Repo:** `integrid-int/avaccess-automator`  
**Branch under review:** `main` (at plan creation)  
**Review mode:** Read-only analysis + automated tests; no product code changes  
**Audience for results:** Follow-up agent + human operators  

---

## 0. Mission

Exhaustively assess whether this system is safe and operable to put live on a bar/restaurant AV LAN: DirecTV H25 SHEF tunes, UDP switch reconnects, 35 TVs, encoder pool ENC-01…ENC-10, and bartender-facing iPad UI under game-day pressure.

This is a **go / no-go / go-with-conditions** review, not a feature brainstorm.

### Primary surfaces

| Surface | Path / package | Role |
|---------|----------------|------|
| Sports Routing panel | `homeassistant/config/www/panels/panel-health.js` (+ `panel-data.js`, `route-planner.js`, `assignment-store.js`) | Production iPad UI |
| Track B execute | `scripts/avaccess/execute_route_plan.py`, `udp_reconnect.py`, HA `packages/avaccess_routing.yaml` | Live SHEF + UDP |
| SHEF transport | `scripts/directv_shef.py` | H25 `/tv/tune` |
| Track C Guide EPG | `scripts/avaccess/build_guide_epg.py`, `tvpassport.py`, `guide_epg.json` | Now/next overlay |
| Sports schedule | `directv_sports.py`, `sports_schedule.json`, weekly sync | Game chips |
| Matrix Lovelace | `homeassistant/dashboards/*`, `packages/avaccess_matrix.example.yaml` | Favorites / presets / SHEF |
| Inventory gate | `config/inventory*.yaml`, `www/avaccess/inventory.json` | Live-ready gate |
| Ops docs | `docs/HA_LIVE.md`, staff PDFs, `OPERATIONS_GUIDE.md` | Go-live + training |

### Explicit non-goals of this review pass

- Implementing fixes (findings only)
- Telnet free-encoder discovery / zone mapping (documented out of scope)
- Cloud UI staging as a substitute for live AV LAN validation

---

## 1. Review workstreams (required + extensions)

Each workstream produces: severity-ranked findings, evidence (file/line or test output), blast radius, and a production recommendation.

### 1.1 Security (CRITICAL for go-live)

**Owner model:** Security-review specialist + IoT/network-aware senior pass  
**Scope:**

- AuthZ on Live Send path (`shell_command`, `input_boolean.avaccess_live_commit`, HA user roles)
- Secrets / credentials / gitignored site config leakage (`directv.yaml`, inventory hostnames, tokens)
- Unauthenticated network surfaces: SHEF TCP 8080, UDP 5010 broadcast, HA 8123
- SSRF / path traversal / command injection via `plan_b64`, shell wrappers, file paths
- XSS / prototype pollution / unsafe `innerHTML` in panel JS
- Supply chain: dependencies, pinned images, example configs that look live
- Privilege boundaries between dry-run and live; inventory gate bypass
- Logging of sensitive payloads (IPs, channel maps) in HA logs / panel summaries
- Local file write surfaces (`custom_tv_sets.json`, guide/sports JSON under `/config/www`)

**Pass criteria for production:** No Critical open; High items have documented compensating controls or deferred with owner sign-off.

### 1.2 Reliability / correctness under load

**Owner model:** Systems / reliability specialist  
**Scope:**

- Partial failure semantics (SHEF fail → no UDP for that slot; other slots continue)
- Preflight exit codes (0/1/2) and panel interpretation of missing stdout from `shell_command`
- Encoder pool exhaustion / replace-a-program path correctness
- Occupancy drift between panel local state and physical room
- EPG / sports schedule staleness, refresh failures, timezone America/New_York
- Docker bridge vs host network for UDP broadcast (documented failure mode)
- Concurrent Takes from multiple iPads
- Idempotency / double-tap Send
- Inventory symlink-to-example trap (REPLACE_ME still live-blocking)
- Automated test coverage gaps vs live paths

**Pass criteria:** Documented failure modes match code; no silent wrong-TV routing on common failures; dry-run default cannot accidentally live-send without inventory + toggle.

### 1.3 UI review (interaction / usability)

**Owner model:** Product UI + iPad Companion focus  
**Scope vs specs:** `docs/superpowers/specs/2026-08-10-bartender-panel-ui-design.md`, `docs/STAFF_TRAINING.md`

- Dual entry paths (content-first vs TV-first) still exclusive and coherent
- Preset 1 / 2 / 3 and named TV sets / replace-a-program flows
- Target sizes, thumb reach, landscape iPad assumptions
- Error / warning surfacing (`Live blocked: inventory not ready`, Live summary)
- Guide search debounce / focus steal
- Matrix vs Sports Routing conceptual overlap for staff
- Accessibility: contrast, focus, reduced motion where applicable

### 1.4 Visual design review

**Owner model:** Visual / brand systems reviewer  
**Scope:**

- Adherence to approved Graphite + Cyan system vs drift in `panel-health.js` / Matrix styles
- Hierarchy: one primary action; no dashboard clutter on bartender panel
- Logo / game card density under fluorescent bar lighting
- Consistency between Sports Routing and Matrix “pretty” dashboard
- Theme packages under `homeassistant/config/themes/`

### 1.5 Overall product / systems design review

**Owner model:** Staff engineer / architect  
**Scope:**

- Track A/B/C separation and whether Live gate is the right safety model
- Striped `RoutePlan` vs Matrix contiguous presets — operator confusion risk
- Data pipeline: TV Passport / DirecTV sports scrape resilience and legal/ToS risk notes
- Deploy topology (`HA_LIVE.md`) complexity vs operator skill
- Rollback / freeze strategy on game day
- Observability: what staff see when a slot fails mid-Sunday

### 1.6 Codebase review

**Owner model:** Senior codebase auditor  
**Scope:**

- Structure: duplicate mounts (`scripts/avaccess` vs `homeassistant/config/avaccess/scripts`)
- Dead code / Spectrum vs DirecTV naming drift in older specs
- Test suite quality (`tests/`, `tests/js/`)
- Panel monolith size (`panel-health.js` ~3.2k lines)
- Config examples vs production traps
- CI / validation scripts (`validate_panels.py`, staging checks)

### 1.7 Senior developer perspective

**Owner model:** Principal / senior engineer persona  
**Lens:** Maintainability, on-callability, “would I ship this Friday before NFL kickoff?”, debt interest rate, missing invariants, docs↔code drift.

### 1.8 Bar / restaurant owner perspective

**Owner model:** Business / ops persona (non-engineer)  
**Lens:**

- Guest experience when wrong game is on a TV
- Staff training burden (quick start vs full guide)
- Downtime risk during peak (Sunday NFL, March Madness)
- Cost of mis-route (complaints, comps, lost reputation)
- Who owns the HA box / network / updates
- Clarity of dry-run vs live for a GM who is not technical

### 1.9 Bartender / server perspective

**Owner model:** Front-of-house operator persona  
**Lens:**

- Speed: taps to put game X on patio TVs during a rush
- Mental model: Presets vs Pick TVs vs named sets
- Recoverability when Take “worked” but TV still wrong
- Glare, gloves, wet hands, shared iPad
- Language: Take / Live commit / encoder jargon vs plain English
- Alignment of staff PDFs with actual UI labels

### 1.10 Extended workstreams (recommended)

| Workstream | Why |
|------------|-----|
| **Ops / go-live runbook audit** | `HA_LIVE.md` is the production procedure; gaps cause silent live failures |
| **Network & physical AV validation checklist** | Host network, SHEF enablement, ENC↔H25 HDMI pairing |
| **Data freshness & content pipeline** | Sports JSON + EPG must be fresh on game day |
| **Regression / automated test gate** | Run full pytest + JS tests; map uncovered live paths |
| **Documentation & training fidelity** | Staff PDF labels vs current UI (`Take`, Live commit, named sets) |
| **Dependency & image hygiene** | HA image tag, Python deps, no Snyk this pass if MCP unavailable |
| **Disaster recovery / game-day playbook** | Who flips Live off; how to freeze; manual SHEF fallback |

---

## 2. Severity rubric

| Severity | Definition | Production impact |
|----------|------------|-------------------|
| **S0 Critical** | Wrong TVs live-routed, remote code exec, auth bypass to Live, silent live with placeholders | Block deploy |
| **S1 High** | Likely wrong content under common failure; inventory gate bypass; data loss of occupancy | Block or conditional with active mitigation |
| **S2 Medium** | Usability/reliability issues that slow staff or confuse modes; docs drift | Fix soon; may ship with owner acknowledgment |
| **S3 Low** | Polish, naming, minor a11y, non-blocking debt | Backlog |
| **S4 Info** | Observations, assumptions, out-of-scope notes | Record only |

---

## 3. Execution model (this pass)

| Workstream | Agent / model assignment | Method |
|------------|--------------------------|--------|
| Security | `security-review` subagent | Diff/repo audit for auth, injection, network |
| Reliability | Cloud/local generalPurpose — Claude Opus high | Failure modes, tests, execute_route_plan semantics |
| UI interaction | generalPurpose — Claude Sonnet/Opus | Spec vs `panel-health.js` + staff docs |
| Visual design | generalPurpose — Claude Opus | Design tokens, hierarchy, Matrix vs panel |
| Overall design | generalPurpose — Claude Opus high | Architecture / Track A/B/C / deploy |
| Codebase | explore + generalPurpose — GPT or Claude Opus | Structure, tests, duplication |
| Senior developer | generalPurpose — Claude Opus xhigh | Ship readiness judgment |
| Owner persona | generalPurpose — Claude Sonnet | Business risk narrative |
| Bartender persona | generalPurpose — Claude Sonnet | FOH workflow narrative |
| Automated tests | Shell in parent | `pytest` + JS tests if runnable |
| Live UI walkthrough | `computerUse` if HA staging available | Optional; note blockers |

Results land in:

1. `docs/qa/PRE_PROD_QA_REVIEW_RESULTS.md` — canonical handoff for the next agent  
2. `/opt/cursor/artifacts/` copies / logs as needed  
3. Optional Canvas summary for human skimming  

---

## 4. Evidence requirements

Every finding must include:

1. **Title** + severity  
2. **Evidence** (path, symbol, test name, or doc quote)  
3. **Why it matters in production** (guest / staff / network)  
4. **Suggested remediation direction** (not an implementation)  
5. **Verification idea** for the fix agent  

---

## 5. Go-live decision framework

After aggregation, the coordinating agent must answer:

1. **Can Live Send be enabled on game day?** (Y / N / conditional)  
2. **Can dry-run-only Soft Launch be recommended?**  
3. **Top 10 must-fix-before-Live** ordered by severity  
4. **Top 10 should-fix-before-first-big-event**  
5. **Explicit residual risks** accepted if shipping  

---

## 6. Out of band checks the next agent should still do on site

These cannot be fully proven from repo alone:

- [ ] Every H25 External Access Allow + reserved IP  
- [ ] ENC-n HDMI ↔ H25-n physical pairing  
- [ ] UDP 5010 broadcast reachable from HA host (not Docker bridge)  
- [ ] Real `config/inventory.yaml` and `config/directv.yaml` (not examples)  
- [ ] iPad Companion landscape dry-run with staff for 10 minutes  
- [ ] One Live Send to a single known TV then verify picture  
- [ ] Guide EPG refresh within last N hours before doors  

---

## 7. Deliverable checklist for this review agent

- [x] This plan committed under `docs/qa/`  
- [ ] Parallel specialist reviews executed  
- [ ] Automated tests run (or blockers recorded)  
- [ ] Results doc with executive verdict + full findings  
- [ ] No product code changes beyond review artifacts  

---

## 8. Handoff contract for the next agent

The follow-up agent should:

1. Read `PRE_PROD_QA_REVIEW_RESULTS.md` end-to-end  
2. Treat S0/S1 as the backlog for a remediation branch  
3. Not re-litigate persona narrative unless contradictory evidence appears  
4. Re-run the automated test gate after fixes  
5. Update the go-live verdict only with new evidence  

---

*Plan authored for exhaustive pre-production review of AVAccess Automator Sports Routing / Matrix stack.*
