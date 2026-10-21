# Make this live in Home Assistant

This is the **site go-live** runbook. It is not the cloud staging UI (`--ui-staging`). Staging never talks to DirecTV or the AVAccess switch.

There are two operator surfaces. You can enable both on one HA:

| Surface | Sidebar | What it does live |
|---------|---------|-------------------|
| **Sports Routing** | `Sports Routing` → `/panel-health` | Bar iPad panel. Hold it sideways. **Take** plans the route. **Live commit** stays off until the room inventory is filled in; then the same Take sends SHEF + UDP. |
| **AVAccess Matrix** | `AVAccess Matrix` | Lovelace favorites (FOX / NFL afternoon / all Sunday), DirecTV SHEF tune, contiguous Preset 1/2/3, route to specific TVs. |

Staff handouts for Sports Routing: [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf). Day-of-game taps for Matrix: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

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

`python3 /config/avaccess/apply_preset.py`

Track B Live Send calls:

`python3 avaccess/run_execute_route_plan.py` (cwd = HA `/config`)

So HA’s `/config/avaccess/scripts/` must contain the Track B package (`execute_route_plan.py`, …). Matrix CLIs (`apply_preset.py`, `directv_shef.py`, `route_targets.py`) live **next to** that directory, at `/config/avaccess/`.

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

# Matrix CLIs sit next to the scripts dir. Do not copy them into the
# scripts symlink: that writes into the git checkout.
cp /share/avaccess-automator/scripts/apply_preset.py /config/avaccess/
cp /share/avaccess-automator/scripts/directv_shef.py /config/avaccess/
cp /share/avaccess-automator/scripts/route_targets.py /config/avaccess/
cp /share/avaccess-automator/scripts/generate_ha_bundle.py /config/avaccess/
cp /share/avaccess-automator/scripts/refresh_ha_weekly.py /config/avaccess/
cp /share/avaccess-automator/scripts/sync_weekly_schedule.py /config/avaccess/
```

Do not commit those copies. If `/share` is not writable, use `/config/avaccess-automator` as the clone path and point the `ln -sfn` / `cp` sources there.

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
      - ./scripts/apply_preset.py:/config/avaccess/apply_preset.py:ro
      - ./scripts/directv_shef.py:/config/avaccess/directv_shef.py:ro
      - ./scripts/route_targets.py:/config/avaccess/route_targets.py:ro
      - ./scripts/generate_ha_bundle.py:/config/avaccess/generate_ha_bundle.py:ro
      - ./scripts/refresh_ha_weekly.py:/config/avaccess/refresh_ha_weekly.py:ro
      - ./scripts/sync_weekly_schedule.py:/config/avaccess/sync_weekly_schedule.py:ro
      - ./config:/config/avaccess/config
    environment:
      TZ: America/New_York
```

`network_mode: host` means HA is on `http://<host>:8123` with no port publish block. Matrix CLIs and `directv_shef.py` are mounted **beside** `/config/avaccess/scripts`, not inside that read-only directory. A file mount inside the scripts volume fails to start or hides the SHEF module.

The scripts mount is read-only. That is fine. Sports Routing writes `custom_tv_sets.json` and refreshed JSON under `/config/www`, which is the config volume, not the scripts mount.

---

## 2b) Sports Routing files the iPad loads

The `www` copy in step 2 is what the panel fetches. These files have to be present, and the panel ignores a file whose `source` is wrong:

| URL | `source` | What breaks if it is missing or wrong |
|-----|----------|----------------------------------------|
| `/local/panels/panel-health.js` | — | Sidebar item is blank. Cache-bust with `?v=30` in `configuration.yaml`. |
| `/local/avaccess/sports_schedule.json` | `directv-sports-info` | Sports rail stays empty. TV Passport must not be copied in as the sports file. |
| `/local/avaccess/guide_channels.json` | `tvpassport:5960D` | Guide has no Greensboro lineup. |
| `/local/avaccess/guide_epg.json` | fresh `generatedAt` | Guide still lists channels, with **Guide listings unavailable — channel list only**. |
| `/local/avaccess/inventory.json` | no `REPLACE_ME` | **Live commit** stays disabled. Take still plans. |
| `/local/avaccess/custom_tv_sets.json` | `tv-sets` | Optional. A new iPad has no Patio/Bar buttons until this file exists. |

Copying `www` the first time is enough to boot the panel, including the checked-in sports and guide snapshots. Do not recopy `inventory.json` or `custom_tv_sets.json` on later updates. The repo inventory is still full of `REPLACE_ME`, and a recopy would turn Live commit back off and wipe saved TV sets.

Packages that have to land in `/config/packages` (the step 2 `cp` of `packages/*.yaml` does this):

- `avaccess_routing.yaml` — `input_boolean.avaccess_live_commit`, `script.avaccess_live_execute` (Live Take; refuses unless the boolean is on), Take’s executor, and `shell_command.avaccess_save_tv_sets`. The panel’s **Live commit** button turns that boolean on/off in HA, so every iPad shows the same state.
- `avaccess_sports.yaml` — morning sports pull
- `avaccess_guide.yaml` — now/next refresh

### Sports list

DirecTV refuses a plain Python download from the Home Assistant machine. Do not paste Cookie or XSRF values into a script.

On Home Assistant OS, install and start the [Selenium Standalone add-on](https://github.com/davida72/selenium-homeassistant) so port **4444** is listening. `avaccess_sports.yaml` then runs `shell_command.avaccess_refresh_sports` every morning at 06:00 (HA local time) and writes `www/avaccess/sports_schedule.json`. The pull is ZIP **27403**, customer type Bars and Restaurants (`bundles=20`), eight days. Greensboro locals **2, 8, 12, and 45** stay. NBA League Pass feeds stay. “NBA mobile” does not.

Home Assistant stops a `shell_command` at 60 seconds. If the morning run is killed, pull the file on a PC that can already open the DirecTV sports page, then copy it to the HA host:

```bash
pip install playwright
python3 scripts/avaccess/directv_sports.py --pull --ahead 8 \
  --out homeassistant/config/www/avaccess/sports_schedule.json
# copy that file to /config/www/avaccess/sports_schedule.json
```

### Guide list and now/next

The channel list is TV Passport lineup **5960D** (DirecTV, Greensboro). Music audio, pay-per-view, barkers, and channels that are not in the package are left out. Music video networks stay. Refresh from the git clone when the lineup changes:

```bash
python3 scripts/avaccess/directv_lineup.py \
  --out /config/www/avaccess/guide_channels.json
```

Now/next for the main locals and sports channels is separate. From the HA host, cwd = `/config`:

```bash
python3 avaccess/run_build_guide_epg.py \
  --config avaccess/config/guide_epg.yaml \
  --out www/avaccess/guide_epg.json
```

Or Developer Tools → Actions → `shell_command.avaccess_refresh_guide_epg`. The panel reloads both JSON files on connect and about every 15 minutes. Listings older than 6 hours fall back to the channel list.

### Named TV sets

**Sets** on the iPad (Patio, Bar) is saved in that iPad’s `localStorage` (`avaccess-tv-sets-v1`). When Companion is connected, Save also calls `shell_command.avaccess_save_tv_sets`, which writes `/config/www/avaccess/custom_tv_sets.json`. A replacement iPad loads that file only when its own key is missing. `/config/www/avaccess/` must be writable by Home Assistant. The scripts directory can stay read-only.

---

## 3) Fill live YAML (break the example symlinks)

From the **git clone** (`/share/avaccess-automator` or repo root):

`config/directv.yaml` is gitignored. `rm -f` drops a symlink first; `cp --remove-destination` will not follow one into `directv.example.yaml`. Then edit real H25 IPs. Do not leave the placeholder `192.168.10.151`–`.160` addresses in place.

```bash
rm -f config/inventory.yaml config/directv.yaml config/channels.yaml config/schedule_sync.yaml
cp --remove-destination config/inventory.example.yaml config/inventory.yaml
cp --remove-destination config/directv.example.yaml config/directv.yaml
cp --remove-destination config/channels.example.yaml config/channels.yaml
cp --remove-destination config/schedule_sync.example.yaml config/schedule_sync.yaml
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

**Do not** pass `--ui-staging`. Open the package and confirm `shell_command.avaccess_directv_tune` contains `python3 /config/avaccess/directv_shef.py`, not `echo STAGING`.

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

frontend:
  extra_module_url:
    - /local/avaccess/matrix-style.js?v=1

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
    module_url: /local/panels/panel-health.js?v=30
    require_admin: false
    config:
      environment: live
```

If `packages:` is already set, only add the dashboard, the `frontend` module, and `panel_custom`. The module paints Matrix keys in the same charcoal and blue as Sports Routing. Copy `www/avaccess/matrix-style.js` with the rest of `www`.

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

Leave **Live commit** off. On Sports Routing, pick one game, tap **All 35 TVs** or a single TV, and tap **Take**. The summary is a dry run: it names the DirecTV box and the channel, and the wall does not change. The yellow line reads **Live commit is off until the room inventory is set up** until `inventory.json` has real hostnames. After one TV routes from the command line, turn Live commit on and Take that same one-TV plan before using All 35.

---

## 8) iPad

1. Install **Home Assistant Companion**.
2. Connect to `http://<ha-host>:8123` (or your TLS proxy).
3. Sidebar: **Sports Routing** for the bar, **AVAccess Matrix** for favorites.
4. Hold the iPad **sideways** for Sports Routing. Below 900px wide the three columns stack and the buttons get small. Matrix favorites still fit portrait.
5. After a panel update, force-quit Companion (or clear its cache) so it does not keep an old `panel-health.js`. The `?v=` on `module_url` is the cache buster; it is `v=30` in this repo. Bump it when you copy a new `panel-health.js`, then restart Home Assistant.

Staff handouts: [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf). Matrix cheat sheet: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

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
| 7 | `input_boolean.avaccess_live_commit` is **off** except during a live Take |
| 8 | Sports Routing is landscape. Take shows a dry-run summary. The wall does not change while the yellow line is up |
| 9 | `sports_schedule.json` source is `directv-sports-info`. `guide_channels.json` source is `tvpassport:5960D` |
| 10 | Selenium add-on is up on port 4444, or a PC pull has replaced `sports_schedule.json` |
| 11 | Saving a named set writes `www/avaccess/custom_tv_sets.json` (`source` `tv-sets`) |

---

## Updating a box that is already live

```bash
cd /share/avaccess-automator
git pull
cp -a homeassistant/config/www/panels/. /config/www/panels/
cp homeassistant/config/packages/avaccess_routing.yaml /config/packages/
cp homeassistant/config/packages/avaccess_sports.yaml /config/packages/
cp homeassistant/config/packages/avaccess_guide.yaml /config/packages/
```

Copy `sports_schedule.json` or `guide_channels.json` only when the HA host is not already refreshing them. Do not copy `inventory.json` or `custom_tv_sets.json` over the live files. If `panel-health.js` changed, bump `module_url` `?v=` in `configuration.yaml`, restart Home Assistant, and force-quit Companion.

---

## Rollback

- **Tune only:** leave **Live commit** off. Take stays a dry run. Matrix still tunes via SHEF.
- **Whole UI:** keep the previous `/config/packages/avaccess_matrix.yaml` copy and restore it.
- iTach IR is **not** on the operator path. `config/itach.example.yaml` and `scripts/send_xumo_ir_itach.py` remain in the repo only as unused leftovers.

---

## Related docs

- [HA_QUICKSTART.md](HA_QUICKSTART.md) — generator flags and helpers
- [DIRECTV_H25_PATCH_AND_TEST_PLAN.md](DIRECTV_H25_PATCH_AND_TEST_PLAN.md) — tests B–F
- [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf) — Sports Routing handouts
- [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) — Matrix taps (older Sports Routing pictures)
- [WEEKLY_SCHEDULE_SYNC.md](WEEKLY_SCHEDULE_SYNC.md) — ZIP 27403 local-first NFL slots
