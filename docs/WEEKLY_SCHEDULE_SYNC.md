# Weekly Schedule Sync (Blackout-Aware)

This adds automatic weekly updates for:
- `nfl_afternoon_game_1..4`
- `nfl_sunday_game_1..9`

using XMLTV guide data and local blackout preference rules.

## Why this matters for ZIP 27403

Some NFL Sunday Ticket feeds are blacked out when the same game is available on local affiliates.  
The sync supports **prefer local over Sunday Ticket** when duplicate game listings are detected.

## Files

- `scripts/sync_weekly_schedule.py` — updates channel numbers in `channels.yaml`
- `scripts/refresh_ha_weekly.py` — runs schedule sync then regenerates HA package/dashboard
- `config/schedule_sync.example.yaml` — blackout-aware config template

## 1) Create your sync config

```bash
cp /config/avaccess/config/schedule_sync.example.yaml /config/avaccess/config/schedule_sync.yaml
```

Edit:
- XMLTV source (`source.url` or `source.file`)
- `channel_number_map` (map XMLTV channel IDs/names → Spectrum channel numbers)
- local/ticket classification rules

## 2) Dry run

```bash
cd /config/avaccess
python3 scripts/sync_weekly_schedule.py \
  --channels config/channels.yaml \
  --sync-config config/schedule_sync.yaml \
  --dry-run
```

Check output:
- candidate channels found
- selected games with class (`local` or `nfl_ticket`)
- proposed channel slot changes

## 3) Full refresh

```bash
cd /config/avaccess
python3 scripts/refresh_ha_weekly.py \
  --channels config/channels.yaml \
  --sync-config config/schedule_sync.yaml \
  --inventory config/inventory.yaml \
  --out-package /config/packages/avaccess_matrix.yaml \
  --out-dashboard /config/dashboards/avaccess_matrix.yaml
```

Then reload scripts/shell commands or restart Home Assistant.

## 4) Weekly Home Assistant automation

Example automation to run early every Tuesday:

```yaml
shell_command:
  avaccess_weekly_refresh: >
    python3 /config/avaccess/scripts/refresh_ha_weekly.py
    --channels /config/avaccess/config/channels.yaml
    --sync-config /config/avaccess/config/schedule_sync.yaml
    --inventory /config/avaccess/config/inventory.yaml
    --out-package /config/packages/avaccess_matrix.yaml
    --out-dashboard /config/dashboards/avaccess_matrix.yaml

automation:
  - alias: AVAccess Weekly Schedule Refresh
    trigger:
      - platform: time
        at: "06:00:00"
    condition:
      - condition: time
        weekday:
          - tue
    action:
      - service: shell_command.avaccess_weekly_refresh
```

## Notes

- Keep fallback channel lists populated for weeks where EPG data is incomplete.
- Initial channel mapping is the key dependency: once the XMLTV channel map is right, weekly updates are low-touch.
- Local channel numbers vary by Spectrum package and region; verify once and keep in config.
