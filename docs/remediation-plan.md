# Remediation Plan — AVAccess Automator

> **For agentic workers:** Execute work packages in order WP-A → WP-H. Commit per package on `remediation/2026-10-21`. Never merge or push to `main` until Phase 6.

**Goal:** Clear S0/S1 pre-prod QA findings so Soft Launch is honest and Live can be gated safely; then prod-readiness, Chrome, docs, videos.

**Architecture:** Keep dry-run default. Fix panel↔executor feedback, planner reuse/off semantics, and server-side Live interlocks before any Live enablement. Server occupancy ledger is a stretch for WP-A/B; minimum is success-only local occupancy + free-encoder preference + confirm dialog.

**Tech Stack:** Home Assistant custom panel (JS), `scripts/avaccess/*` (Python), HA `shell_command` / `input_boolean`, Node test runner, unittest/pytest.

**Branch:** `remediation/2026-10-21`  
**Source reviews:** `docs/qa/PRE_PROD_QA_REVIEW_RESULTS.md`, `docs/qa/RELIABILITY_REVIEW.md`, `docs/qa/PRE_PROD_QA_REVIEW_PLAN.md`  
**Loop cap:** 5 iterations per review/fix loop  
**Models:** Planning/acceptance = inherit / Grok high when Opus/GPT unavailable; core logic = Grok high or Composer; mechanical/docs = Composer fast / Sonnet if available.

---

## Findings table (deduplicated)

| ID | Sev | Area | Description | Acceptance criteria | WP | Pri |
|----|-----|------|-------------|---------------------|----|-----|
| S0-SILENT-LIVE | S0 | `panel-health.js`, HA shell_command | Live `callService` without response; occupancy saved first; failures look like success | Live call requests response; nonzero/missing report → error banner; occupancy only for slots with `status===ok`; test covers exit 1/2/empty | A | 1 |
| S0-NO-CHANNEL | S0 | `route-planner.js`, `panel-health.js`, `execute_route_plan.py` | Games with null channel still Take; UDP without SHEF marks ok | Take disabled / blocked when any selected program lacks channelNumber in Live; executor rejects live slots with empty tune; tests | C | 2 |
| S0-OCCUPANCY-IPAD | S0 | `assignment-store.js`, `panel-health.js` | Free encoder from per-iPad localStorage; multi-iPad / cache clear retunes busy box | Document single-iPad Live constraint; dry-run does not persist occupancy OR clear-on-load option; add “Clear room state” control; note server ledger as follow-up BLOCKED if not done | A,B | 1 |
| S0-REUSE-BAR | S0 | `route-planner.js` | `singleEncoderForTvs` before free encoders; patio after All-35 retunes whole bar | Prefer free encoder when any free; if must reuse shared box, require confirm listing off-count before Take; tests for patio-after-all35 | B | 1 |
| S0-OFF-FICTION | S0 | `execute_route_plan.py`, panel copy, staff docs | `replaced.offTvs` never acted on; UI/docs say “turn off” | Stop claiming Off/turn-off in UI+docs OR implement disconnect; summary uses “still on retuned box” language; training updated | B,G | 1 |
| S1-LIVE-BOOLEAN | S1 | `avaccess_routing.yaml`, panel, executor | Boolean not enforced; toggle local-only | Wrapper/script refuses `--live` unless boolean on; panel writes boolean on toggle; resync on every hass update | D | 2 |
| S1-B64-SHELL | S1 | `avaccess_routing.yaml` | Unquoted `plan_b64`/`sets_b64` | Quoted/validated base64 or stdin/temp-file path; reject non-b64 | D | 2 |
| S1-UDP-TRUST | S1 | `execute_route_plan.py` | Pre-filled `udp` hostnames trusted on live | Live always re-enrich from inventory (overwrite plan udp) | D | 2 |
| S1-SHEF-STATUS | S1 | `directv_shef.py`, executor | SHEF body status ignored; no getTuned | Reject non-success SHEF status; optional verify before UDP | E | 3 |
| S1-PRESET-PARTIAL | S1 | `apply_preset.py` | Partial UDP before full validation | Full preset preflight before any send | E | 3 |
| S1-DOUBLE-TAP | S1 | `panel-health.js` | Take enabled during in-flight Live | In-flight lock + disabled Take + spinner until settled | A | 1 |
| S1-DEMO-FALLBACK | S1 | `panel-data.js`, panel | Missing sports → demo games Takeable | Banner when using fallback; block Live Take on fallback/demo | C | 2 |
| S1-VIS-TOKENS | S1 | `panel-health.js` CSS | `:host` vars never resolve; Live/chip states wrong | Vars on `.routing` or shadowRoot; Live PRACTICE/LIVE banner unmistakable | F | 3 |
| S1-SCROLL-JUMP | S1 | `panel-health.js` | Full innerHTML on hass resets scroll | Preserve scroll positions on re-render or patch DOM | F | 3 |
| S1-MATRIX-CONFUSION | S1 | docs, Matrix | Matrix live vs Routing practice look alike | Staff docs + PRACTICE banner; OPERATIONS notes which surface is live | G | 3 |
| S1-INVENTORY-TRAP | S1 | `HA_QUICKSTART.md`, config | Symlink `cp` edits example | Fix Quickstart to `rm`/`--remove-destination`; note in HA_LIVE | G | 3 |
| S1-DOCKER-UDP | S1 | `HA_LIVE.md`, compose | Bridge compose silent UDP fail | HA_LIVE: HA OS/host-net only for Live; warn on bridge | G | 3 |
| S2-LOGO-FALLBACK | S2 | panel | Broken logos no initials | Initials tile onerror | F | 4 |
| S2-RAIL-FOLD | S2 | panel | Guide/Now/Sets below fold | Pin Guide/Now/Sets above sports list | F | 4 |
| S2-SPORTS-STALE | S2 | panel | No sports freshness banner | Banner if generatedAt older than N hours | C,F | 4 |
| S2-TESTS-SHALLOW | S2 | `tests/js` | Regex-only live path | Behavioral tests for WP-A/B/C | H | 2 |
| BLOCK-SITE-* | — | site | Real wall, H25, msg_b_reconnect, broadcast NIC | Remain BLOCKED pending on-site; listed in log | — | — |

---

## Work packages

### WP-A — Live feedback & occupancy honesty
- **Depends on:** none  
- **Findings:** S0-SILENT-LIVE, S1-DOUBLE-TAP, part of S0-OCCUPANCY-IPAD  
- **Files:** `panel-health.js`, possibly `assignment-store.js`, `tests/js/*`  
- **Model:** Grok high / Composer  
- **Steps:**
  1. Add failing tests for returnResponse + occupancy-after-ok + double-tap  
  2. Call `callService` with `returnResponse: true` (HA frontend arity)  
  3. Parse returncode/report; error banner on failure  
  4. Move `_saveAssignments` to after successful live slots only (dry-run may keep local plan apply for training OR stop writing — prefer: dry-run applies for training but label PRACTICE; Live only success slots)  
  5. `_sending` lock disables Take  
  6. Commit  
- **Verify:** `node --test tests/js/*.test.js`; manual code review of `_sendPlan`  
- **Done when:** Acceptance for S0-SILENT-LIVE and S1-DOUBLE-TAP met  

### WP-B — Encoder reuse & “off” semantics
- **Depends on:** none (can parallel A)  
- **Findings:** S0-REUSE-BAR, S0-OFF-FICTION, S0-OCCUPANCY-IPAD (partial)  
- **Files:** `route-planner.js`, `panel-health.js`, staff training snippets  
- **Model:** Grok high  
- **Steps:**
  1. Change planner: prefer free encoder; reuse shared only if no free OR explicit replace  
  2. Pre-Take confirm when `replaced.offTvs.length > 0`  
  3. Replace UI copy “turn off” → “will keep showing the retuned box until reassigned”  
  4. Add “Clear room state” button  
  5. Tests for patio-after-all35 uses free ENC  
  6. Commit  
- **Done when:** S0-REUSE-BAR and S0-OFF-FICTION acceptance met  

### WP-C — No-channel & demo guard
- **Depends on:** none  
- **Findings:** S0-NO-CHANNEL, S1-DEMO-FALLBACK, S2-SPORTS-STALE  
- **Files:** `panel-health.js`, `route-planner.js`, `execute_route_plan.py`, tests  
- **Model:** Grok high  
- **Done when:** Live Take blocked without channel; executor live rejects empty tune; demo/fallback banner + Live blocked  

### WP-D — Server Live interlock & plan safety
- **Depends on:** none  
- **Findings:** S1-LIVE-BOOLEAN, S1-B64-SHELL, S1-UDP-TRUST  
- **Files:** `avaccess_routing.yaml`, `run_execute_route_plan.py`, `execute_route_plan.py`, `panel-health.js`  
- **Model:** Grok high  
- **Done when:** Live requires boolean on (documented HA script/condition or python check via env/file flag written by automation — prefer HA `script` wrapping shell_command); b64 safe; live always enrich udp  

### WP-E — SHEF + Matrix preflight
- **Depends on:** D optional  
- **Findings:** S1-SHEF-STATUS, S1-PRESET-PARTIAL  
- **Files:** `directv_shef.py`, `execute_route_plan.py`, `apply_preset.py`, tests  
- **Model:** Grok high  
- **Done when:** Non-success SHEF fails slot before UDP; apply_preset validates all routes first  

### WP-F — Visual / UX Soft Launch blockers
- **Depends on:** A helpful  
- **Findings:** S1-VIS-TOKENS, S1-SCROLL-JUMP, S2-LOGO-FALLBACK, S2-RAIL-FOLD  
- **Files:** `panel-health.js`  
- **Model:** Composer / Grok  
- **Done when:** Tokens resolve; PRACTICE/LIVE banner; logos fallback; Guide/Now/Sets pinned; scroll preserved  

### WP-G — Docs corrections
- **Depends on:** B,C copy choices  
- **Findings:** S1-MATRIX-CONFUSION, S1-INVENTORY-TRAP, S1-DOCKER-UDP, S0-OFF-FICTION docs  
- **Files:** `docs/STAFF_TRAINING.md`, `docs/HA_QUICKSTART.md`, `docs/HA_LIVE.md`, `docs/OPERATIONS_GUIDE.md`, rebuild PDFs if scripts exist  
- **Model:** Composer fast  
- **Done when:** Docs match behavior; Soft Launch conditions documented  

### WP-H — Test hardening
- **Depends on:** A–E  
- **Findings:** S2-TESTS-SHALLOW  
- **Files:** `tests/js/*`, `tests/test_execute_route_plan.py`, etc.  
- **Model:** Grok / Composer  
- **Done when:** New tests fail on pre-fix behavior and pass on branch  

---

## Out of scope / BLOCKED pending site

| ID | Reason |
|----|--------|
| BLOCK-SITE-WALL | Live never proven on real wall |
| BLOCK-SITE-RECONNECT | `msg_b_reconnect` eviction semantics unknown |
| BLOCK-SITE-BROADCAST | Host NIC / Docker UDP reachability |
| BLOCK-SITE-SUNDAY-CH | 9554–9563 vs 705–713 channel set |
| BLOCK-SERVER-LEDGER | Full multi-iPad server occupancy (partial mitigation in A/B only) |

Mark WON'T FIX only with reason in log.

---

## Phase gates (user pipeline)

| Phase | Exit criteria |
|-------|---------------|
| 1 Remediate | WP-A…H done or BLOCKED; log updated |
| 2 Re-verify original review | Each findings-table row PASS / BLOCKED / WON'T FIX; loop ≤5 |
| 3 Prod readiness | `docs/prod-readiness-plan.md` + report satisfied |
| 4 Chrome | Full primary flows pass; bugs fixed or BLOCKED |
| 5 Final pre-merge | Diff review PASS |
| 6 Merge main | Only after 5; post-merge tests |
| 7 Docs cleanup | Stale removed; matrix/bar instructions rebuilt; PDFs reviewed |
| 8 Videos | One video per instruction doc |

---

## Execution notes for sub-agents

- Branch: `remediation/2026-10-21` only  
- After each WP: commit + append `docs/remediation-log.md`  
- Do not push to `main`  
- Prefer TDD: failing test → fix → pass  
- If model unavailable, use `inherit` or `cursor-grok-4.6-high` / `composer-2.5`  
