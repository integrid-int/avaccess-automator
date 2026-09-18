# Make this live in Home Assistant

This is the **site go-live** runbook. It is not the cloud staging UI (`--ui-staging`). Staging never talks to DirecTV or the AVAccess switch.

There are two operator surfaces. You can enable both on one HA:

| Surface | Sidebar | What it does live |
|---------|---------|-------------------|
| **Sports Routing** | `Sports Routing` → `/panel-health` | Bartender iPad panel. Striped presets, Guide now/next, Live Send (SHEF + UDP). |
| **AVAccess Matrix** | `AVAccess Matrix` | Lovelace favorites (FOX / NFL afternoon / all Sunday), DirecTV SHEF tune, contiguous Preset 1/2/3, route to specific TVs. |

Day-of-game taps for Matrix: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

---

## 0) Network (do this first)

The HA host must sit on the **AV LAN** (or have routes + broadcast into it).

| Traffic | Dest | Why |
|---------|------|-----|
| TCP **8080** | each H25 | DirecTV SHEF tune / now-playing |
| UDP **5010** broadcast | AVAccess switch | `msg_b_reconnect` presets and TV routes |
| TCP **8123** | iPads | HA Companion / Safari |

Docker **bridge** networking usually **cannot** send `255.255.255.255:5010`. For live matrix routing use **Home Assistant OS**, **host network**, or an HA VM that is a peer on `192.168.10.0/24`.

Do **not** use `scripts/prepare_ha_staging.py` on this box.

---

## 1) Enable SHEF on every H25

On each receiver: **Menu → Settings & Help → Settings → Whole Home → External Device**

- External Access: **Allow**
- Current Program: **Allow**
- DHCP reservation or static IP
- HDMI → the matching 4KIP200 encoder (H25-01 → ENC-01, …)

---

## 2) Put the repo on the HA machine

Use the **same path layout the Docker test stack uses**. Matrix shell commands call:

`python3 /config/avaccess/scripts/apply_preset.py`

Track B Live Send calls:

`python3 avaccess/run_execute_route_plan.py` (cwd = HA `/config`)

So HA’s `/config/avaccess/scripts/` must contain **both** the Track B package (`execute_route_plan.py`, …) **and** the Matrix CLIs (`apply_preset.py`, `directv_shef.py`, `route_targets.py`).

### Home Assistant OS / Supervised

SSH or the Terminal add-on. Keep the git clone **next to** HA config, not as a replacement for `/config`:

```bash
cd /share
git clone https://github.com/integrid-int/avaccess-automator.git avaccess-automator
cd avaccess-automator
git checkout main
python3 -m pip install pyyaml
```

Seed HA config from the repo (first time only — merge `configuration.yaml` by hand if HA already has one):

```bash
mkdir -p /config/packages /config/dashboards /config/www /config/avaccess

cp /share/avaccess-automator/homeassistant/config/packages/*.yaml /config/packages/
cp /share/avaccess-automator/homeassistant/config/avaccess/run_*.py /config/avaccess/
cp -a /share/avaccess-automator/homeassistant/config/www/. /config/www/

# Track B modules + live YAML
ln -sfn /share/avaccess-automator/scripts/avaccess /config/avaccess/scripts
ln -sfn /share/avaccess-automator/config /config/avaccess/config

# Matrix CLIs onto that same scripts dir (shell_command paths)
cp /share/avaccess-automator/scripts/apply_preset.py /config/avaccess/scripts/
cp /share/avaccess-automator/scripts/directv_shef.py /config/avaccess/scripts/
cp /share/avaccess-automator/scripts/route_targets.py /config/avaccess/scripts/
cp /share/avaccess-automator/scripts/generate_ha_bundle.py /config/avaccess/scripts/
cp /share/avaccess-automator/scripts/refresh_ha_weekly.py /config/avaccess/scripts/
cp /share/avaccess-automator/scripts/sync_weekly_schedule.py /config/avaccess/scripts/
```

Because `/config/avaccess/scripts` is a symlink into the repo, those `cp` files land in `scripts/avaccess/` in git. That is expected on the live box; do not commit them.

If `/share` is not writable, use `/config/avaccess-automator` as the clone path and point the `ln -sfn` / `cp` sources there.

### Docker Compose on an AV-LAN host

Use `homeassistant/docker-compose.yml` **with host networking** (edit, do not leave the test `ports:` bridge):

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: avaccess-ha
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./homeassistant/config:/config
      - ./scripts/avaccess:/config/avaccess/scripts:ro
      - ./scripts/apply_preset.py:/config/avaccess/scripts/apply_preset.py:ro
      - ./scripts/directv_shef.py:/config/avaccess/scripts/directv_shef.py:ro
      - ./scripts/route_targets.py:/config/avaccess/scripts/route_targets.py:ro
      - ./scripts/generate_ha_bundle.py:/config/avaccess/scripts/generate_ha_bundle.py:ro
      - ./scripts/refresh_ha_weekly.py:/config/avaccess/scripts/refresh_ha_weekly.py:ro
      - ./scripts/sync_weekly_schedule.py:/config/avaccess/scripts/sync_weekly_schedule.py:ro
      - ./config:/config/avaccess/config
    environment:
      TZ: America/New_York
```

`network_mode: host` means HA is on `http://<host>:8123` with no port publish block. Overlay file mounts on top of `/config/avaccess/scripts` so both Track B modules and Matrix CLIs exist.

---

## 3) Fill live YAML (break the example symlinks)

From the **git clone** (`/share/avaccess-automator` or repo root):

```bash
rm -f config/inventory.yaml config/directv.yaml config/channels.yaml config/schedule_sync.yaml
cp config/inventory.example.yaml config/inventory.yaml
cp config/directv.example.yaml config/directv.yaml
cp config/channels.example.yaml config/channels.yaml
cp config/schedule_sync.example.yaml config/schedule_sync.yaml
```

Edit:

1. **`config/inventory.yaml`** — every encoder/receiver `hostname` and `mac` (no `REPLACE_ME`). Discover via VDirector or UDP 3335/3336. `network.broadcast` must be the AV LAN broadcast (often `192.168.10.255`, not `255.255.255.255`, if the HA host has multiple NICs).
2. **`config/directv.yaml`** — real H25 IPs. Example placeholders are `192.168.10.151`–`.160`.
3. **`config/channels.yaml`** — keep `ir_transport: directv_shef` and `directv_config_path: /config/avaccess/config/directv.yaml`. After adding the HA DirecTV integration (step 6), set `encoder_media_player` to the real `media_player.*` entity IDs.

Export the bartender Live gate:

```bash
python3 scripts/avaccess/export_inventory_json.py --input config/inventory.yaml
```

On HA OS, copy the JSON to the panel’s URL:

```bash
cp homeassistant/config/www/avaccess/inventory.json /config/www/avaccess/inventory.json
```

(The exporter writes `homeassistant/config/www/avaccess/inventory.json` from repo root.)

---

## 4) Generate the **live** Matrix package (no staging stubs)

```bash
cd /share/avaccess-automator   # repo root
python3 scripts/generate_ha_bundle.py \
  --inventory config/inventory.yaml \
  --channels config/channels.yaml \
  --profile numeric_v1 \
  --inventory-ha-path /config/avaccess/config/inventory.yaml \
  --out-package /config/packages/avaccess_matrix.yaml \
  --out-dashboard /config/dashboards/avaccess_matrix.yaml
```

**Do not** pass `--ui-staging`. Open the package and confirm `shell_command.avaccess_directv_tune` contains `python3 /config/avaccess/scripts/directv_shef.py`, not `echo STAGING`.

`numeric_v1` is the Lovelace favorite/preset map (Preset 1 = all TVs on ENC-01, Preset 2 = 9/9/9/8, Preset 3 = 4×8+3). The bartender panel still uses **`striped_v1`** via `mapping_profiles.active` in inventory.

---

## 5) Wire `configuration.yaml`

Keep default Lovelace (UI-managed). Add the extra YAML dashboard and packages. Merge — do not wipe an existing `default_config:`.

```yaml
homeassistant:
  packages: !include_dir_named packages
  time_zone: America/New_York
  unit_system: us_customary
  currency: USD

lovelace:
  dashboards:
    avaccess-matrix:
      mode: yaml
      title: AVAccess Matrix
      icon: mdi:video-input-component
      show_in_sidebar: true
      filename: dashboards/avaccess_matrix.yaml

panel_custom:
  - name: panel-health
    sidebar_title: Sports Routing
    sidebar_icon: mdi:trophy
    url_path: panel-health
    module_url: /local/panels/panel-health.js?v=15
    require_admin: false
    config:
      environment: live
```

If `packages:` is already set, only add the dashboard + `panel_custom` blocks.

Restart Home Assistant (**Developer tools → YAML → Restart**, or reboot the container).

---

## 6) Official DirecTV integration (Now Playing)

1. **Settings → Devices & services → Add integration → DirecTV**
2. Add **each** H25 by IP (port 8080).
3. Note the entity IDs (often `media_player.living_room` etc., not `media_player.directv_h25_01`).
4. Put those IDs in `config/channels.yaml` under `encoder_media_player`.
5. Re-run `generate_ha_bundle.py` (step 4) and **reload Lovelace** (or restart).

Until this is done, Matrix Now Playing cards will be red “entity not found”. Tuning still works via SHEF.

---

## 7) Smoke test on the AV LAN (before the iPad)

From the HA host (or `docker exec` with host net):

```bash
cd /share/avaccess-automator

# SHEF — one box
python3 scripts/directv_shef.py --config config/directv.yaml probe --encoder ENC-01
python3 scripts/directv_shef.py --config config/directv.yaml get-tuned --encoder ENC-01
python3 scripts/directv_shef.py --config config/directv.yaml tune --encoder ENC-01 --channel 206 --verify

python3 scripts/directv_shef.py --config config/directv.yaml probe-all

# Matrix — dry-run then ONE TV
python3 scripts/apply_preset.py --inventory config/inventory.yaml --profile numeric_v1 --preset 1_all --dry-run
python3 scripts/route_targets.py --inventory config/inventory.yaml --encoder ENC-01 --targets RX-01 --dry-run

# Live: one TV only
python3 scripts/route_targets.py --inventory config/inventory.yaml --encoder ENC-01 --targets RX-01
```

Pass: probe JSON 200, `get-tuned` has `title` + `major`, after tune `major` is 206, that one TV shows ENC-01.

Then in HA **Activity**, tap **FOX Local** on AVAccess Matrix and confirm scripts **Ran** (not STAGING echo). All TVs should show local FOX.

Leave bartender **Live commit** **off** until the same one-TV route works from **Sports Routing → Dry-run Send**, then enable Live for one Send.

---

## 8) iPad

1. Install **Home Assistant Companion**.
2. Connect to `http://<ha-host>:8123` (or your TLS proxy).
3. Sidebar: **AVAccess Matrix** (favorites) and **Sports Routing** (bartender planner).
4. Add Matrix (or Sports Routing) to the home screen / default dashboard.

Operator cheat sheet: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

---

## 9) Go-live checklist

| # | Check |
|---|--------|
| 1 | No `--ui-staging` in `/config/packages/avaccess_matrix.yaml` |
| 2 | `directv.yaml` IPs ping; `probe-all` succeeds |
| 3 | ENC/RX hostnames are real `IPE935-…` / `IPD935-…`, not `REPLACE_ME` |
| 4 | UDP reconnect from HA host changes **one** TV first |
| 5 | FOX Local: all TVs + H25-01 on WGHP |
| 6 | Now Playing entities match the DirecTV integration |
| 7 | `input_boolean.avaccess_live_commit` is **off** except during a live Send |
| 8 | iPad Companion opens both sidebars; tap targets work in portrait |

---

## Rollback

- **Tune only:** leave bartender **Live commit** off (Dry-run Send stays occupancy-only). Matrix still tunes via SHEF.
- **Whole UI:** keep the previous `/config/packages/avaccess_matrix.yaml` copy and restore it.
- iTach IR is **not** on the operator path. `config/itach.example.yaml` and `scripts/send_xumo_ir_itach.py` remain in the repo only as unused leftovers.

---

## Related docs

- [HA_QUICKSTART.md](HA_QUICKSTART.md) — generator flags and helpers
- [DIRECTV_H25_PATCH_AND_TEST_PLAN.md](DIRECTV_H25_PATCH_AND_TEST_PLAN.md) — tests B–F
- [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) — bartender-facing Matrix taps
- [WEEKLY_SCHEDULE_SYNC.md](WEEKLY_SCHEDULE_SYNC.md) — ZIP 27403 local-first NFL slots
