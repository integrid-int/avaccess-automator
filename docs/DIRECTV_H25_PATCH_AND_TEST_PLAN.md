# DirecTV H25 Patch + Testing Plan

This is a **structured patch**, not a rewrite. AVAccess presets, sports pages, and one/many TV routing stay. Only the source-control transport changes from iTach IR (Xumo/Spectrum) to DirecTV H25 IP (SHEF).

## What stays
- Encoder/receiver inventory and UDP `msg_b_reconnect` presets
- Numeric mapping profile (`numeric_v1`) with ENC-10 spare
- Favorites (FOX / NFL afternoon / all Sunday games)
- Sports pages + `input_text.avaccess_target_rxs` routing
- Blackout-aware weekly channel slot updates (ZIP 27403 local-first)

## What changes
- `ir_transport` / `source_transport` now supports `directv_shef`
- Channel tune uses HTTP SHEF (`/tv/tune`) instead of IR digits
- Now-playing comes from `/tv/getTuned` (and optional HA DirecTV media_player entities)

## File patch map

| File | Change |
|------|--------|
| `config/directv.example.yaml` | **New** H25 IP map (`ENC-xx` → `H25-xx`) |
| `scripts/directv_shef.py` | **New** SHEF client: probe / get-tuned / tune / send-key |
| `scripts/generate_ha_bundle.py` | Add `directv_shef` tune path + shell command |
| `config/channels.example.yaml` | Default transport `directv_shef`, provider `directv` |
| `tests/test_directv_shef.py` | Offline parse/tune URL tests |
| `docs/HA_QUICKSTART.md` | Copy `directv.yaml`, probe/tune steps |
| iTach files | **Keep** as rollback transport (`itach_tcp`) |

## Cutover sequence

1. **Commission H25 LAN**
   - DHCP reservations for all 10 boxes
   - Enable External Access + Current Program on each H25
2. **Fill `config/directv.yaml`** with real IPs
3. **Lab probe** (`probe-all`) before touching the matrix
4. **Single-box tune+verify** on ENC-01 only
5. Flip `channels.yaml` to `ir_transport: directv_shef` and regenerate HA bundle
6. Keep iTach config on disk until a full game-day rehearsal passes
7. Then retire IR emitters from the operator path

## Testing plan

### A. Offline (no receivers required)
```bash
python3 -m unittest tests/test_directv_shef.py
python3 scripts/directv_shef.py --config config/directv.example.yaml probe --encoder ENC-01 --dry-run
python3 scripts/directv_shef.py --config config/directv.example.yaml tune --encoder ENC-02 --channel 206 --dry-run
python3 scripts/generate_ha_bundle.py \
  --inventory config/inventory.example.yaml \
  --channels config/channels.example.yaml \
  --out-package /tmp/avaccess_matrix.yaml \
  --out-dashboard /tmp/avaccess_dash.yaml
```
Pass criteria: generated package includes `shell_command.avaccess_directv_tune` and `script.avaccess_tune_channel` calls it.

### B. Per-receiver SHEF smoke (on AV LAN)
For each ENC-01..ENC-10:
```bash
python3 scripts/directv_shef.py --config config/directv.yaml probe --encoder ENC-01
python3 scripts/directv_shef.py --config config/directv.yaml get-tuned --encoder ENC-01
python3 scripts/directv_shef.py --config config/directv.yaml tune --encoder ENC-01 --channel 206 --verify
```
Pass criteria:
- `/info/getOptions` returns JSON status 200
- `get-tuned` returns `title` + `major`
- after tune, `major` matches requested channel

Then:
```bash
python3 scripts/directv_shef.py --config config/directv.yaml probe-all
```

### C. Matrix still works (unchanged protocol)
```bash
python3 scripts/apply_preset.py --inventory config/inventory.yaml --preset 1_all --dry-run
python3 scripts/route_targets.py --inventory config/inventory.yaml --encoder ENC-01 --targets RX-01 --dry-run
```
Live (one TV first): Preset 1, then route ENC-01 → a single RX.

### D. HA operator path
1. Restart / reload scripts after regenerating the package
2. Tune ESPN on Program A from dashboard
3. Confirm H25-01 changed and `get-tuned` / HA media_player title updates
4. Favorite **FOX Local**: all TVs show ENC-01, H25-01 on local FOX
5. Favorite **NFL Afternoon Games**: four H25s tune, Preset 2 applied
6. Route Program A to `RX-01,RX-02` only

### E. Blackout / ZIP 27403
1. Pick a game listed on both local affiliate and Sunday Ticket
2. Confirm weekly sync still prefers local channel number
3. Tune that slot and verify `callsign` is the local station, not ST

### F. Rollback
Set `ir_transport: itach_tcp` in `channels.yaml`, regenerate bundle, restart HA. Matrix routing is unchanged.

## Receiver settings checklist (each H25)
- External Access: Allow
- Current Program: Allow
- Static/reserved IP
- Reachable from HA host on TCP **8080**
- HDMI out to corresponding 4KIP200E

## Known limits
- SHEF is current-program + tune/keys, not a full future guide dump
- Keep XMLTV/schedule sync for daily sports-page labels
- Do not poll `getTuned` too aggressively (1s+ between commands)
