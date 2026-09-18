# Home Assistant Channel Buttons (DirecTV SHEF)

Tune DirecTV H25 boxes over IP (SHEF HTTP `:8080`). There is **no IR** on the live operator path.

Current project default transport:
- **DirecTV H25 SHEF IP** (`ir_transport` / `source_transport`: `directv_shef`)
- iTach / HA remote IR generators remain in `generate_ha_bundle.py` only as unused leftovers

## 1) Prerequisites

1. Each H25: **Menu → Settings & Help → Settings → Whole Home → External Device**
   - External Access: **Allow**
   - Current Program: **Allow**
2. Fill [`config/directv.example.yaml`](../config/directv.example.yaml) with H25 IPs (`ENC-xx` → `H25-xx`).
3. Optional: official HA **DirecTV** integration for Now Playing cards (`encoder_media_player`).

## 2) Data model

Use [`config/channels.example.yaml`](../config/channels.example.yaml) as your source of truth:

- Program → Encoder
- Encoder → H25 (`config/directv.yaml`)
- Named channels (label + DirecTV major)

## 3) Script pattern

The generated package calls SHEF via `shell_command.avaccess_directv_tune`:

```yaml
shell_command:
  avaccess_directv_tune: >
    python3 /config/avaccess/scripts/directv_shef.py
    --config /config/avaccess/config/directv.yaml
    tune --encoder "{{ encoder }}" --channel "{{ channel }}"
```

CLI equivalent:

```bash
python3 scripts/directv_shef.py --config config/directv.yaml \
  tune --encoder ENC-01 --channel 206 --verify
```

## 4) Dashboard pattern

- Top row: Preset 1 / Preset 2 / Preset 3
- Channel row: ESPN / TNT / FOX / CBS
- Program selector: A / B / C / D (for Preset 2) or A..I (for Preset 3)

This keeps operations simple:
1) Select preset  
2) Pick program tile  
3) Tap channel

## 5) Guide information options

If you want guide context (what's on now/next), use XMLTV/EPG (`scripts/avaccess/build_guide_epg.py`) and display:

- Current program per favorite channel
- Upcoming program
- Search card for program titles

SHEF `getTuned` is now-playing on a live box, not a future guide dump.

## 6) Favorite macros (recommended for sports ops)

You can define one-tap favorites in `channels.yaml` that:
1) optionally apply a preset, then  
2) tune one or many program slots.

Included examples:
- `fox`
- `nfl_afternoon_games`
- `all_nfl_sunday_games`

This is ideal for weekly game-day operation: update only the NFL channel numbers in `channels.yaml`, regenerate the HA bundle, and keep the same operator buttons.

For blackout-aware weekly automation (local channel preferred over Sunday Ticket when both carry the same game), see:
- `docs/WEEKLY_SCHEDULE_SYNC.md`

## 7) Phase 2: route to one or many TVs

Generated package includes:
- `input_text.avaccess_target_rxs` (comma-separated receiver IDs, e.g. `RX-01,RX-02,RX-10`)
- `script.avaccess_route_selected_program_to_tvs`

Flow:
1. Select/tune the source program  
2. Enter target TVs  
3. Run route script to push that program to those TVs only

This enables sports-page workflows where you can send the same game to a full preset or to ad-hoc subsets of TVs.
