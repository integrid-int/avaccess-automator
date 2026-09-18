# DirecTV H25 Patch + Testing Plan

This is a **structured patch**, not a rewrite. AVAccess presets, sports pages, and one/many TV routing stay. Source-control transport is DirecTV H25 IP (SHEF). There is **no IR** on the live operator path.

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
| `docs/HA_QUICKSTART.md` | Copy `directv.yaml`, probe/tune steps, cloud HA UI staging |
| `scripts/prepare_ha_staging.py` | **New** stubbed HA config + Docker compose for cloud UI testing |
| `homeassistant/staging/docker-compose.yml` | Cloud/VM Home Assistant on port 8123 |
| iTach files | Unused leftovers (`itach_tcp` generator still exists, not live) |

## Cutover sequence

1. **Cloud HA UI staging** (no AV LAN required) — catch Lovelace/layout bugs
2. **Commission H25 LAN**
   - DHCP reservations for all 10 boxes
   - Enable External Access + Current Program on each H25
3. **Fill `config/directv.yaml`** with real IPs
4. **Lab probe** (`probe-all`) before touching the matrix
5. **Single-box tune+verify** on ENC-01 only
6. Point staging HA (or site HA) at live package (no `--ui-staging`) and retest UI against hardware
7. Retire IR emitters from the operator path (done: Track B Live Send is SHEF + UDP)
8. Keep `config/itach.example.yaml` in git only as unused leftover

## Testing plan

### A. Offline (no receivers required)
```bash
python3 -m unittest tests/test_directv_shef.py
python3 scripts/directv_shef.py --config config/directv.example.yaml probe --encoder ENC-01 --dry-run
python3 scripts/directv_shef.py --config config/directv.example.yaml tune --encoder ENC-02 --channel 206 --dry-run
python3 scripts/generate_ha_bundle.py \
  --inventory config/inventory.example.yaml \
  --channels config/channels.example.yaml \
  --profile numeric_v1 \
  --out-package /tmp/avaccess_matrix.yaml \
  --out-dashboard /tmp/avaccess_dash.yaml
```
Pass criteria: generated package includes `shell_command.avaccess_directv_tune` and `script.avaccess_tune_channel` calls it.

### A2. Cloud Home Assistant UI staging (required before live hardware)

Stand up a **cloud or VM Home Assistant** with this repo mounted so we can fix live Lovelace bugs (layout, missing entities, iPad tap targets, tab overflow) without DirecTV/AVAccess on the network.

```bash
python3 scripts/prepare_ha_staging.py
docker compose -f homeassistant/staging/docker-compose.yml up -d
```

Open `http://<cloud-host>:8123`:
1. Complete HA onboarding once (create owner account; staging default is `operator` / `avaccess-staging`).
2. Confirm sidebar shows **AVAccess Matrix**.
3. Walk the UI checklist below on **desktop** and **iPad Safari / HA Companion**.

`--ui-staging` stubs every `shell_command` to `echo` and emits modern `template:` dummy Now Playing sensors (HA 2026.9), so taps should not fail because H25s are unreachable. Scripts and helpers still load.

#### UI bug checklist
| Check | Pass |
|-------|------|
| Control tab loads without red "entity not found" for program/channel/target helpers | |
| Favorites row: FOX / NFL Afternoon / All Sunday are large enough to tap on iPad | |
| Preset 1/2/3 buttons visible without horizontal scroll | |
| Program A–I grid fits portrait iPad | |
| Channel buttons wrap; NFL S1–S9 readable | |
| **NFL / College Football / Basketball** tabs switch and keep destination card | |
| Now Playing card: unavailable entities are acceptable in staging; must not break the view | |
| Tap Favorite FOX → script runs (log shows STAGING echo, no traceback) | |
| Tap Route Program → TVs with `RX-01,RX-02` → script runs | |
| Settings/Guide views on pretty dashboard (if used) do not 404 | |
| Browser console / HA logs: no YAML parse errors after restart | |

Fix YAML/layout in git, regenerate staging bundle, **reload Lovelace** (or restart HA), retest. Do not skip this gate.

#### Cloud deployment notes
- Use a small VM (2 vCPU / 2 GB) or the same Docker compose on a cloud box with port 8123 (or a reverse proxy + TLS).
- This staging instance is **UI-only**. Do not attach it to production AV VLAN until section D.
- After UI sign-off, regenerate **without** `--ui-staging` on the site HA that can reach H25s and the AV switch.

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
Turn bartender **Live commit** off. Dry-run Send stays occupancy-only. Matrix routing is unchanged. Do not switch `ir_transport` back to `itach_tcp` — IR is not on the live path.

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
