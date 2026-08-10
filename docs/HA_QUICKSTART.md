# Home Assistant Quickstart

This quickstart gives you an operator-ready iPad control surface for:

- Preset 1/2/3 AVAccess routing
- Program selector (A..I)
- One-tap Xumo channel buttons (IR-backed)

## 1) Put this project in Home Assistant config

On your HA host, place this repo under:

```text
/config/avaccess
```

## 2) Create your local config files

```bash
cd /config/avaccess
cp config/inventory.example.yaml config/inventory.yaml
cp config/channels.example.yaml config/channels.yaml
```

Edit:
- `config/inventory.yaml` → real TX/RX hostnames/MACs/IPs
- `config/channels.yaml` → program→encoder mapping, IR entities, favorite channels, and favorite macros
- `config/schedule_sync.yaml` (optional) → weekly auto-update + blackout-aware channel selection (ZIP 27403)

## 3) Generate HA package + dashboard YAML

```bash
cd /config/avaccess
python3 -m pip install pyyaml
python3 scripts/generate_ha_bundle.py \
  --inventory config/inventory.yaml \
  --channels config/channels.yaml \
  --out-package /config/packages/avaccess_matrix.yaml \
  --out-dashboard /config/dashboards/avaccess_matrix.yaml
```

## 4) Enable packages in `configuration.yaml`

```yaml
homeassistant:
  packages: !include_dir_named packages
```

## 5) Add dashboard YAML

Use one of these approaches:

- **YAML dashboard mode**: point a dashboard to `/config/dashboards/avaccess_matrix.yaml`
- **Raw config editor**: paste the generated dashboard YAML into a dashboard
- **Polished mockup version**: use `homeassistant/dashboards/avaccess_matrix_dashboard_pretty.example.yaml`
  as a starting point, then adjust entity IDs.

## 6) Restart Home Assistant

After restart you should see:
- scripts `script.avaccess_preset_*`
- scripts `script.avaccess_tune_*`
- `input_select.avaccess_program`
- `input_select.avaccess_channel`

## 7) iPad operation flow

1. Tap preset (1/2/3)  
2. Tap active program (A..I)  
3. Tap channel (ESPN/TNT/...)  

Or use one-tap favorites:
- **FOX** (Preset 1 + FOX tune)
- **NFL Afternoon Games** (Preset 2 + 4 program tunes)
- **All NFL Sunday Games** (Preset 3 + 9 program tunes)

For automated weekly NFL channel updates, see:
- `docs/WEEKLY_SCHEDULE_SYNC.md`

Optional maintenance shell commands (used by the pretty Settings tab buttons):

```yaml
shell_command:
  avaccess_weekly_refresh: >
    python3 /config/avaccess/scripts/refresh_ha_weekly.py
    --channels /config/avaccess/config/channels.yaml
    --sync-config /config/avaccess/config/schedule_sync.yaml
    --inventory /config/avaccess/config/inventory.yaml
    --out-package /config/packages/avaccess_matrix.yaml
    --out-dashboard /config/dashboards/avaccess_matrix.yaml
  avaccess_generate_bundle: >
    python3 /config/avaccess/scripts/generate_ha_bundle.py
    --inventory /config/avaccess/config/inventory.yaml
    --channels /config/avaccess/config/channels.yaml
    --out-package /config/packages/avaccess_matrix.yaml
    --out-dashboard /config/dashboards/avaccess_matrix.yaml
```

## Notes

- AVAccess preset switching uses UDP broadcast `:5010` (`msg_b_reconnect`).
- Xumo channel tune relies on IR commands via your HA remote entities.
- Keep `ENC-10` spare unless you intentionally map it in `channels.yaml` and presets.
