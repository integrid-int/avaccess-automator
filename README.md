# avaccess-automator

Home Assistant test environment for validating the **iPad bartender Sports Routing** panel.

## Goals (aligned with AVAccess plan)

This panel is designed for Home Assistant Companion on iPad and mirrors the Phase 2 sports-routing workflow:

- Games listed under **sport tabs** (NFL / College Football / Basketball)
- Each game shows **team logos + team names**
- **Groups = project presets**:
  - Preset 1 — ALL (all 35 TVs)
  - Preset 2 — 4 Programs (encoder blocks)
  - Preset 3 — 9 Programs (encoder blocks)
- **Individuals = TVs 1–35**, with adhoc multi-select
- Clean, large-target UI for bartender speed

## What this repository provides

- Runnable Home Assistant test environment: `homeassistant/docker-compose.yml`
- Custom panel registered in `homeassistant/config/configuration.yaml`
- Bartender panel module: `homeassistant/config/www/panels/panel-health.js`
- Panel validator: `scripts/validate_panels.py`
- Automated tests: `tests/test_validate_panels.py`

## Python setup for local validation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt homeassistant
```

## Home Assistant test environment

1. Start Home Assistant:

   ```bash
   docker compose -f homeassistant/docker-compose.yml up -d
   ```

   If Docker is unavailable, run Core from the venv:

   ```bash
   .venv/bin/python -m homeassistant --config homeassistant/config
   ```

2. Validate configuration:

   ```bash
   docker exec ha_panel_test python -m homeassistant --script check_config --config /config
   ```

   or local fallback:

   ```bash
   .venv/bin/python -m homeassistant --script check_config --config homeassistant/config
   ```

3. Open Home Assistant:
   - URL: `http://localhost:8123`
   - Panel path: `/panel-health`
   - Sidebar title: `Sports Routing`

## Panel validation workflows

### Static panel validation

```bash
.venv/bin/python scripts/validate_panels.py --config-dir homeassistant/config
```

### End-to-end validation (static + Home Assistant config check)

```bash
bash scripts/run_ha_panel_validation.sh
```

Notes:
- If Docker is available, the script validates inside a Home Assistant container.
- If Docker is not available, it falls back to local `homeassistant --script check_config`.
- The script auto-prefers `.venv/bin/python` when present.

### Run automated tests

```bash
.venv/bin/python -m pytest tests/test_validate_panels.py -q
```
