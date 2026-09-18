# AVAccess Automator

Plan and tooling to drive **10× 4KIP200 encoders + 35× receivers** with iPad-friendly presets and DirecTV H25 IP control (iTach IR remains as rollback).

## Docs

- **[docs/PLAN.md](docs/PLAN.md)** — architecture, preset math, Home Assistant vs alternatives, Xumo strategy
- **[docs/HOME_ASSISTANT_CHANNELS.md](docs/HOME_ASSISTANT_CHANNELS.md)** — one-tap channel buttons and guide options
- **[docs/HA_QUICKSTART.md](docs/HA_QUICKSTART.md)** — generate package/dashboard and run in Home Assistant
- **[docs/WEEKLY_SCHEDULE_SYNC.md](docs/WEEKLY_SCHEDULE_SYNC.md)** — weekly EPG sync with local-blackout preference
- **[docs/PHASE2_SPORTS_PAGES.md](docs/PHASE2_SPORTS_PAGES.md)** — sport tabs + daily updates + one/many TV routing
- **[docs/GLOBAL_CACHE_ITACH_SETUP.md](docs/GLOBAL_CACHE_ITACH_SETUP.md)** — iTach IP2IR-P x4 setup and testing (rollback)
- **[docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md](docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md)** — DirecTV IP cutover + test plan (includes cloud HA UI staging)
- **[docs/HA_STAGING_STATUS.md](docs/HA_STAGING_STATUS.md)** / **[docs/HA_STAGING_A2_CHECKLIST.md](docs/HA_STAGING_A2_CHECKLIST.md)** — cloud HA 2026.9 staging boot + A2 UI walk
- **`homeassistant/dashboards/avaccess_matrix_dashboard_pretty.example.yaml`** — polished iPad-style Lovelace mockup

## Quick start (after inventory is filled)

```bash
cp config/inventory.example.yaml config/inventory.yaml
# edit hostnames / MACs / preset RX lists

python3 -m pip install pyyaml
python3 scripts/apply_preset.py --inventory config/inventory.yaml --preset 1_all --dry-run
python3 scripts/apply_preset.py --inventory config/inventory.yaml --preset 1_all
# optional when using mapping_profiles:
# python3 scripts/apply_preset.py --inventory config/inventory.yaml --profile numeric_v1 --preset 2_four_programs
```

Presets are applied with AVAccess UDP bulk reconnect (`255.255.255.255:5010`).

## Home Assistant bundle generator

```bash
python3 scripts/generate_ha_bundle.py \
  --inventory config/inventory.yaml \
  --channels config/channels.yaml \
  --out-package homeassistant/packages/avaccess_matrix.yaml \
  --out-dashboard homeassistant/dashboards/avaccess_matrix_dashboard.yaml
```

Generated outputs:
- package YAML with shell commands, scripts, and selectors
- dashboard YAML with preset/program/channel buttons
- sports-specific views (from `sports_pages` in `channels.yaml`)
- one/many TV routing via `input_text.avaccess_target_rxs` + route scripts

Cloud UI staging (no AV LAN): `python3 scripts/prepare_ha_staging.py` then `docker compose -f homeassistant/staging/docker-compose.yml up -d`. Optional owner: `python3 scripts/complete_ha_onboarding.py` (`operator` / `avaccess-staging`).

## Tests

```bash
python3 -m unittest tests.test_directv_shef tests.test_ha_staging_config tests.test_offline_plan -v
```
