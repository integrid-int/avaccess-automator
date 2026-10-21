# Pre-Production QA Review Results — AVAccess Automator

**Status:** IN PROGRESS — specialist agents running; coordinator evidence seeded  
**Plan:** [PRE_PROD_QA_REVIEW_PLAN.md](./PRE_PROD_QA_REVIEW_PLAN.md)  
**Review branch:** `cursor/pre-prod-qa-review-af45`  
**Code under review:** `main` @ `e2f97d3` (Restyle the Matrix dashboard with Sports Routing keys)  
**Constraint:** No product code changes this pass  

---

## Executive verdict (preliminary — finalize after specialist sections land)

| Question | Preliminary answer |
|----------|-------------------|
| Enable **Live Send** on next game day? | **Conditional / likely NO** until on-site inventory+network validation and S0/S1 from specialists are cleared |
| Soft Launch (**dry-run only**) on iPad? | **Likely YES** for staff training if panel JS tests stay green and staff docs match UI |
| Overall | Ship as **training / dry-run**; gate Live behind checklist in plan §6 |

> Final go/no-go will be rewritten once all specialist agent reports are merged below.

---

## Automated test gate (coordinator)

| Suite | Result | Evidence |
|-------|--------|----------|
| `node --test tests/js/*.test.js` | **39/39 pass** | `/opt/cursor/artifacts/node-test-results.txt` |
| `pytest tests/` | **BLOCKED** | PyPI HTTPS SSL failure in review VM; `apt` also blocked |
| Snyk dependency scan | **BLOCKED** | MCP namespace error at discovery |
| Live HA / computerUse UI | **NOT RUN** | No AV-LAN HA in this environment |

Follow-up must re-run pytest and (if available) Snyk before claiming full automated gate.

---

## Specialist agent roster

| Workstream | Agent ID | Model / type | Status |
|------------|----------|--------------|--------|
| Security | `bc-4fe1d506-1809-5ca8-b2d9-f3f4c3d90243` | security-review · Claude Opus high | running |
| Reliability | `bc-5eb95651-bb29-5c1c-ad45-b2b9e4d3388c` | generalPurpose · Claude Opus high | running |
| UI interaction | `bc-99819c78-c158-53b9-b984-00e1d13dcaf3` | generalPurpose · Claude Opus medium | running |
| Visual design | `bc-66c2e031-218f-512f-8cc1-66e105ce4588` | generalPurpose · Claude Opus medium | running |
| Overall design | `bc-89a16bb0-f850-5cf8-a281-b693cccb3c34` | generalPurpose · Claude Opus high | running |
| Codebase | `bc-1fa21211-ce44-5de7-879c-8c7acfe0677e` | generalPurpose · GPT-5.6 high | running |
| Senior developer | `bc-a29dd362-80ee-5ac7-aaba-d5d2f452b43e` | generalPurpose · Claude Opus xhigh | running |
| Owner persona | `bc-9b5be436-b5b1-53c3-b713-f818d583b824` | generalPurpose · Claude Sonnet high | running |
| Bartender persona | `bc-8802d5da-4b0b-5150-a485-c06a9cfb4d6e` | generalPurpose · Claude Sonnet high | running |
| Ops runbook | `bc-9baef8d3-bb96-5b62-b377-f795aa99cf2a` | generalPurpose · Claude Opus medium | running |

---

## Coordinator seed findings (pre-specialist)

These are evidence-backed observations from the coordinating agent; specialists may elevate, demote, or supersede.

### SEC-C1 — HA `shell_command` interpolates `plan_b64` / `sets_b64` unquoted — **S1 candidate**

**Evidence:** `homeassistant/config/packages/avaccess_routing.yaml` lines 18–28:

```yaml
avaccess_execute_route_plan: >-
  python3 avaccess/run_execute_route_plan.py
  ...
  --plan-b64 {{ plan_b64 }}
```

Base64 alphabet includes `+`, `/`, `=`. Unquoted Jinja into a shell line is a classic HA footgun (argument splitting / injection depending on HA templating and caller control). Any HA user allowed to call `shell_command.avaccess_execute_route_plan` can attempt Live.

**Why it matters:** Live path reaches SHEF + UDP broadcast on the AV LAN.

**Remediation direction:** Prefer writing plan JSON to a temp file via a constrained helper, or quote/validate `^[A-Za-z0-9+/=]+$` length-limit before exec; restrict service to trusted HA users / admin-only.

### SEC-C2 — Live gate is client-enforced + inventory JSON — **S2/S1**

**Evidence:** `panel-health.js` `_sendPlan` (~1065–1104): Live service call only if `liveRequested && liveReady`. Inventory readiness from `/local/avaccess/inventory.json` (`isInventoryLiveReady`). Separate HA `input_boolean.avaccess_live_commit`.

Bypass vectors: direct Developer Tools service call with `live: true` + crafted `plan_b64`, ignoring panel gate. CLI `--live` still validates inventory for plan-referenced devices (narrower than panel’s all ENC/RX rule).

**Why it matters:** Panel gate is UX safety, not hard AuthZ.

### REL-C1 — Local occupancy updates even when Live fails / blocked — **S2**

**Evidence:** `applyRoutePlan` / `_saveAssignments` run **before** live `callService` (~1090–1113). On Live failure, warnings append but local assignments already reflect success intent.

**Why it matters:** Bartender sees panel badges that disagree with physical TVs → wrong follow-up Takes.

### REL-C2 — SHEF-fail skips UDP for that slot — **confirmed OK (S4 info)**

**Evidence:** `execute_route_plan.py` `execute_plan` single try-block: tune then UDP; exception → slot error, no UDP for that slot; loop continues. Matches README.

### OPS-C1 — Docker bridge vs host network — **S1 if ignored at deploy**

**Evidence:** `docs/HA_LIVE.md` §0 explicitly warns Docker bridge usually cannot send `255.255.255.255:5010`.

### OPS-C2 — `config/inventory.yaml` → example symlink in repo — **S1 deploy trap**

**Evidence:** `config/inventory.yaml` → `inventory.example.yaml` with `REPLACE_ME` hostnames. Live gate should block; if someone edits example in place or weakens gate, Live could target placeholders.

### UI-C1 — Spec drift Spectrum vs DirecTV — **S3**

**Evidence:** UI design spec still mentions Spectrum/Xumo in places; production is DirecTV ZIP 27403 + TV Passport. Staff training may be newer than spec.

### CODE-C1 — `panel-health.js` ~3247 lines monolith — **S3 maintainability**

JS unit tests are string/contract heavy (good smoke) but limited behavioral DOM coverage.

### CODE-C2 — Duplicate script trees — **S2 drift risk**

`scripts/avaccess/*` and `homeassistant/config/avaccess/scripts/*` (symlinks/mounts). HA wrappers at `run_*.py`. On-call must know which path is live on HA OS vs compose.

---

## 1. Security review

_Pending specialist output — will paste verbatim summary + normalize severities here._

## 2. Reliability review

_Pending._

## 3. UI review

_Pending._

## 4. Visual design review

_Pending._

## 5. Overall design review

_Pending._

## 6. Codebase review

_Pending._

## 7. Senior developer perspective

_Pending._

## 8. Bar / restaurant owner perspective

_Pending._

## 9. Bartender / server perspective

_Pending._

## 10. Ops / go-live runbook audit

_Pending._

---

## Aggregated must-fix backlog (seed — will rebuild after merge)

### Before Live Send

1. Confirm real `inventory.yaml` + `directv.yaml` (not examples); export `inventory.json`; verify Live gate  
2. HA host network / UDP 5010 broadcast proof  
3. Restrict who can call Live `shell_command`  
4. Resolve specialist S0/S1  
5. On-site single-TV Live proof  

### Before Soft Launch (dry-run training)

1. Staff PDF labels match **Take** / Live commit / named sets  
2. 10-minute bartender dry-run drill  
3. Keep Live commit **off**  

---

## Handoff for next agent

1. Read this file fully after specialist sections are filled  
2. Open remediation branch from `main` (not this docs-only branch unless preferred)  
3. Fix S0/S1 first; re-run `node --test tests/js` + full pytest  
4. Update verdict table only with new evidence  
5. Do not treat coordinator seed findings as final if specialists contradict with stronger evidence  

---

## Appendix A — Artifact paths

- Plan: `docs/qa/PRE_PROD_QA_REVIEW_PLAN.md`  
- Results: `docs/qa/PRE_PROD_QA_REVIEW_RESULTS.md` (this file)  
- Node test log: `/opt/cursor/artifacts/node-test-results.txt`  
- Test gate notes: `/opt/cursor/artifacts/automated-test-gate.md`  

## Appendix B — Change log

| When | What |
|------|------|
| Review start | Plan authored; 10 specialist agents dispatched; node tests 39/39; pytest/Snyk blocked |
| (next) | Merge specialist reports; finalize verdict |
