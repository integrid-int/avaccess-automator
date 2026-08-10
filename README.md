# avaccess-automator

Home Assistant panel validation playground for high-availability style test runs.

## What this repository now provides

- A runnable Home Assistant container test environment at `homeassistant/docker-compose.yml`.
- A sample custom panel (`panel_custom`) registered in
  `homeassistant/config/configuration.yaml`.
- A panel validation utility at `scripts/validate_panels.py`.
- Automated tests for the validator in `tests/test_validate_panels.py`.

## Python setup for local validation

Create an isolated virtual environment for reproducible checks:

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt homeassistant
```

## Home Assistant test environment

1. Start Home Assistant:

   ```bash
   docker compose -f homeassistant/docker-compose.yml up -d
   ```

2. Validate Home Assistant configuration:

   ```bash
   docker exec ha_panel_test python -m homeassistant --script check_config --config /config
   ```

3. Open Home Assistant:
   - URL: `http://localhost:8123`
   - Panel path: `/panel-health`

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
