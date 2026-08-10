# avaccess-automator

Home Assistant panel validation playground for high-availability style test runs.

## What this repository now provides

- A runnable Home Assistant container test environment at `homeassistant/docker-compose.yml`.
- A sample custom panel (`panel_custom`) registered in
  `homeassistant/config/configuration.yaml`.
- A panel validation utility at `scripts/validate_panels.py`.
- Automated tests for the validator in `tests/test_validate_panels.py`.

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
python scripts/validate_panels.py --config-dir homeassistant/config
```

### End-to-end validation (static + Home Assistant config check)

```bash
bash scripts/run_ha_panel_validation.sh
```

### Run automated tests

```bash
pytest tests/test_validate_panels.py -q
```
