# Task 3 Report: Rebuild panel shell (Graphite + Cyan screen state machine)

## Status

Implemented and validated.

## Changes

- Replaced `homeassistant/config/www/panels/panel-health.js` with an import-backed shell that consumes `assignment-store.js` and `panel-data.js`.
- Added internal screen state for:
  - `browse-sport`
  - `browse-guide`
  - `browse-tvs`
  - `destination`
  - `content-picker`
- Added required state fields: `sportId`, `guideQuery`, `selectedContent`, `selectedTvs`, `destMode`, `contentMode`, and `entryPath`.
- Rendered the chip row for all sports plus `Guide` and `TVs`.
- Wired chip clicks to switch the shell among sports, guide, and TVs screens.
- Added temporary shell paths to reach `destination` and `content-picker`.
- Rendered Graphite and Cyan styling from `TOKENS`, including the `#0e7490` cyan marker.
- Kept `hass` and `panel` setters.
- Guarded `customElements.define` with `customElements.get("panel-health")`.
- Bumped `homeassistant/config/configuration.yaml` `module_url` to `/local/panels/panel-health.js?v=5`.
- Added `tests/js/panel-shell.test.js`.

## TDD Evidence

Red step:

- `node --test tests/js/panel-shell.test.js`
- Result: failed as expected against the old panel because `assignment-store.js`, `panel-data.js`, cyan token, and new screen/action markers were absent.

Green step:

- `node --test tests/js/panel-shell.test.js`
- Result: 2 tests passed.

## Verification

Required validation commands:

```text
node --test tests/js/*.test.js
.venv/bin/python scripts/validate_panels.py --config-dir homeassistant/config
.venv/bin/python -m pytest tests/test_validate_panels.py -q
```

Result:

```text
node --test: 6 pass, 0 fail
validate_panels: Panel validation passed.
pytest: 5 passed in 0.03s
```

Additional syntax check:

```text
node --check homeassistant/config/www/panels/panel-health.js
```

Result: exit code 0.

## Self-review

- Confirmed `panel-health.js` imports both required modules.
- Confirmed all required screen names exist in state and render routing.
- Confirmed sports, Guide, and TVs chip actions exist and switch `screen`.
- Confirmed `destination` and `content-picker` are reachable through temporary shell hooks.
- Confirmed `module_url` is `?v=5`.
- Confirmed custom element registration is guarded.
- Confirmed no whitespace errors with `git diff --check`.

## Commits

- `52c49ac feat: rebuild bartender panel shell with screen state machine`

## Concerns

- Full Task 4/5 content-first and TV-first assignment flows remain intentionally skeletal; this task only builds the shell and temporary navigation hooks.
