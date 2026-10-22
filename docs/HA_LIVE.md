# Make this live in Home Assistant

This is the **site go-live** runbook. It is not the cloud staging UI (`--ui-staging`). Staging never talks to DirecTV or the AVAccess switch.

There are two operator surfaces. You can enable both on one HA:

| Surface | Sidebar | What it does live |
|---------|---------|-------------------|
| **Sports Routing** | `Sports Routing` → `/panel-health` | Bar iPad panel. Hold it sideways. **Take** plans the route. The header banner reads **PRACTICE – TVs will not change** until the room inventory is filled in **and** `input_boolean.avaccess_live_commit` is on; then it reads **LIVE – TVs WILL change** and the same Take calls `script.avaccess_live_execute` (SHEF + UDP). |
| **AVAccess Matrix** | `AVAccess Matrix` | Lovelace favorites (FOX / NFL afternoon / all Sunday), DirecTV SHEF tune, contiguous Preset 1/2/3, route to specific TVs. **Always live** once the package is generated without `--ui-staging`: there is no Live commit switch, no PRACTICE banner, and no inventory gate on Matrix. |

**Which surface is live:** a Matrix tap changes the wall immediately. A Sports Routing Take changes the wall only while its banner says **LIVE**. The two screens look alike (same charcoal and blue), so during Soft Launch tell staff which one they are on.

Staff handouts for Sports Routing: [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf) _(PDFs pending rebuild; use [STAFF_TRAINING.md](STAFF_TRAINING.md) for the current UI.)_. Day-of-game taps for Matrix: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

---

## 0) Network (do this first)

The HA host must sit on the **AV LAN** (or have routes + broadcast into it).

| Traffic | Dest | Why |
|---------|------|-----|
| TCP **8080** | each H25 | DirecTV SHEF tune / now-playing |
| UDP **5010** broadcast | AVAccess switch | `msg_b_reconnect` presets and TV routes |
| TCP **8123** | iPads | HA Companion / Safari |

**Live UDP needs Home Assistant OS or host networking.** Use **Home Assistant OS**, a container with `network_mode: host`, or an HA VM that is a peer on `192.168.10.0/24`.

> **Warning — Docker bridge.** Both checked-in compose files (`homeassistant/docker-compose.yml` and `homeassistant/staging/docker-compose.yml`) use bridge networking with `ports: 8123:8123`. On a bridge, `sendto 255.255.255.255:5010` usually succeeds inside the container and never reaches the AV LAN. The executor sees no error, so the Live summary can report `ok` while the TVs do not switch. SHEF (TCP 8080) may still work, so the H25 changes channel and the wall does not follow. Do not run Live from a bridge container. Use the host-network compose in section 2.

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

Use the checked-in host-network compose (do **not** leave the test `ports:` bridge in `homeassistant/docker-compose.yml`):

```bash
docker compose -f homeassistant/docker-compose.host.yml up -d
```

That file is `homeassistant/docker-compose.host.yml`: `network_mode: host`, container `avaccess-ha`, TZ `America/New_York`, and the same bind mounts as below. Equivalent hand-written compose:

```yaml
services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: avaccess-ha
    restart: unless-stopped
    network_mode: host
    volumes:
      - ./config:/config
      - ../scripts/avaccess:/config/avaccess/scripts:ro
      - ../scripts/apply_preset.py:/config/avaccess/apply_preset.py:ro
      - ../scripts/directv_shef.py:/config/avaccess/directv_shef.py:ro
      - ../scripts/route_targets.py:/config/avaccess/route_targets.py:ro
      - ../scripts/generate_ha_bundle.py:/config/avaccess/generate_ha_bundle.py:ro
      - ../scripts/refresh_ha_weekly.py:/config/avaccess/refresh_ha_weekly.py:ro
      - ../scripts/sync_weekly_schedule.py:/config/avaccess/sync_weekly_schedule.py:ro
      - ../config:/config/avaccess/config
    environment:
      TZ: America/New_York
```

Run it from the repo root with `-f homeassistant/docker-compose.host.yml` so `./config` is `homeassistant/config` and `../scripts` is the repo `scripts/` tree.

`network_mode: host` means HA is on `http://<host>:8123` with no port publish block. Matrix CLIs and `directv_shef.py` are mounted **beside** `/config/avaccess/scripts`, not inside that read-only directory. A file mount inside the scripts volume fails to start or hides the SHEF module.

The scripts mount is read-only. That is fine. Sports Routing writes `custom_tv_sets.json` and refreshed JSON under `/config/www`, which is the config volume, not the scripts mount.

#### Raspberry Pi (`gaps`)

From a laptop that can SSH to the Pi (default `pi@gaps`):

```bash
# first time — prefer --rsync if the Pi has no GitHub credentials
./scripts/deploy_gaps_pi.sh --init --rsync

# later updates (keeps site YAML / inventory.json / custom_tv_sets.json)
./scripts/deploy_gaps_pi.sh --rsync
```

`--git` (default) runs `git clone` / `git pull` on the Pi instead. Override host/user/path with `--host`, `--user`, `--dir`, or `DEPLOY_HOST` / `DEPLOY_USER` / `DEPLOY_DIR`. The Pi needs Docker Engine + the `compose` plugin and an SSH key in `BatchMode`. After `--init`, edit `config/inventory.yaml` and `config/directv.yaml` on the Pi before any Live Take (section 3).

---

## 2b) Sports Routing files the iPad loads

The `www` copy in step 2 is what the panel fetches. These files have to be present, and the panel ignores a file whose `source` is wrong:

| URL | `source` | What breaks if it is missing or wrong |
|-----|----------|----------------------------------------|
| `/local/panels/panel-health.js` | — | Sidebar item is blank. Cache-bust with `?v=35` in `configuration.yaml`. |
| `/local/avaccess/sports_schedule.json` | `directv-sports-info` | Sports rail stays empty. TV Passport must not be copied in as the sports file. |
| `/local/avaccess/guide_channels.json` | `tvpassport:5960D` | Guide has no Greensboro lineup. |
| `/local/avaccess/guide_epg.json` | fresh `generatedAt` | Guide still lists channels, with **Guide listings unavailable — channel list only**. |
| `/local/avaccess/inventory.json` | no `REPLACE_ME` | **Live commit** stays disabled and the banner stays **PRACTICE**. Take still plans. Leaving the placeholders in is how Soft Launch keeps Live blocked (section 7b). |
| `/local/avaccess/custom_tv_sets.json` | `tv-sets` | Optional. A new iPad has no Patio/Bar buttons until this file exists. |

Copying `www` the first time is enough to boot the panel, including the checked-in sports and guide snapshots. Do not recopy `inventory.json` or `custom_tv_sets.json` on later updates. The repo inventory is still full of `REPLACE_ME`, and a recopy would turn Live commit back off and wipe saved TV sets.

Packages that have to land in `/config/packages` (the step 2 `cp` of `packages/*.yaml` does this):

- `avaccess_routing.yaml` — `input_boolean.avaccess_live_commit`, `script.avaccess_live_execute` (Live Take; refuses unless the boolean is on), Take’s executor, and `shell_command.avaccess_save_tv_sets`. The panel’s **Live commit** button turns that boolean on/off in HA, so every iPad shows the same state.
- `avaccess_sports.yaml` — morning sports pull
- `avaccess_guide.yaml` — now/next refresh

### How Live is gated (Sports Routing only)

There is one Live switch for the whole room: `input_boolean.avaccess_live_commit` (starts **off** after every HA restart, `initial: false`).

1. The panel’s **Live commit: ON / OFF** button calls `input_boolean.turn_on` / `turn_off`. Every iPad re-reads the boolean on each Home Assistant update, so turning it on from one iPad turns it on for all of them. The button is disabled while `inventory.json` still has `REPLACE_ME`.
2. A Take is Live only when the boolean is on **and** `inventory.json` is Live-ready. The banner follows the same rule. Otherwise the Take is a practice plan and the summary is headed **PRACTICE summary**.
3. Live Take calls `script.avaccess_live_execute` with the plan (base64) and waits for its response. The script (`mode: single`) runs `shell_command.avaccess_execute_route_plan` with `live: true` only while the boolean is on. If it is off, the script returns `returncode` 3 and *Live Commit is off in Home Assistant. Nothing was sent.* without running the shell command.
4. The shell command passes `--live-commit on|off` from the boolean at call time, and `run_execute_route_plan.py` refuses `--live` unless it reads `on`. Calling the shell command directly from Developer Tools cannot bypass the switch.
5. On Live, UDP hostnames are always re-read from `config/inventory.yaml`; hostnames inside the plan are ignored. A program with no DirecTV channel blocks Take, and the executor rejects a live slot with no tune. A SHEF tune that fails or does not verify (`/tv/getTuned`) fails that slot before any UDP is sent.
6. The panel saves occupancy only for slots that come back `ok`. A nonzero `returncode`, a missing report, or `ok: false` shows an error in the summary. Take is locked (**Sending…**) until the response arrives.
7. Home Assistant kills a shell command after 60 seconds, and the panel then gets no report even for TVs that already switched. The executor therefore starts a slot only if that slot can finish inside 50 seconds at its worst case (SHEF tune plus three `/tv/getTuned` polls, each up to `timeout_seconds`: 17 s at the default 4 s). Slots it does not start come back as errors that read *Not attempted: the Live Take reached its 50 s time limit before this slot. Nothing was sent; these TVs keep their previous source.* A healthy 9-box Take takes about 2 seconds. Keep `timeout_seconds` at 4 in `directv.yaml`; a value whose worst case exceeds 50 s fails Live preflight.
8. Each Live Take is kept as a trace of `script.avaccess_live_execute` (last 50 runs, `stored_traces: 50`): **Settings → Automations & Scenes → Scripts → AVAccess Live Execute → Traces**. The trace holds the executor's JSON report (per-slot `status`, `error`, `elapsedMs`). Failed runs (nonzero exit) are also logged as errors in the Home Assistant log.

With `mode: single`, a second Live Take from another iPad while one is running gets no report and shows a failure. Nothing is sent for that second Take.

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

A fresh clone ships `config/inventory.yaml` as a symlink to `inventory.example.yaml`. A plain `cp` onto that symlink writes through it and edits the tracked example. Always `rm -f` first; `cp --remove-destination` will not follow a symlink either. `config/directv.yaml` is gitignored. Then edit real H25 IPs. Do not leave the placeholder `192.168.10.151`–`.160` addresses in place.

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
    module_url: /local/panels/panel-health.js?v=35
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

Leave **Live commit** off. On Sports Routing, pick one game, tap **All 35 TVs** or a single TV, and tap **Take**. The banner reads **PRACTICE – TVs will not change** and the summary is headed **PRACTICE summary**: it names the DirecTV box and the channel, and the wall does not change. The yellow line reads **Live commit is off until the room inventory is set up** until `inventory.json` has real hostnames. After one TV routes from the command line, follow section 7b before the first Live Take.

---

## 7b) Soft Launch, then the first Live Take

**Soft Launch** is staff using Sports Routing for practice on the real HA while the wall is still driven by Matrix or by hand.

Conditions while in Soft Launch:

- Leave `REPLACE_ME` in `/config/www/avaccess/inventory.json` (do not export the real inventory to `www` yet). The **Live commit** button stays disabled, the banner stays **PRACTICE – TVs will not change**, and even a boolean turned on from Developer Tools cannot make a panel Take live.
- Keep `input_boolean.avaccess_live_commit` **off**.
- Check that every iPad shows the slate **PRACTICE** banner at the top. If any iPad shows the red **LIVE – TVs WILL change** banner, stop and turn the boolean off.
- Matrix is **not** in practice mode. Anyone tapping AVAccess Matrix changes the wall. Say so in training.
- Practice and Live occupancy are separate stores in each iPad’s `localStorage`. Practice Takes write only the practice store (`avaccess-bartender-panel-practice-v1`); it is per-iPad and it is fiction: no box was tuned. Live Takes read and write only the Live store (`avaccess-bartender-panel-v2`). When Live commit flips, the panel reloads the store for the new mode (no merge), so practice routes never count as busy boxes in Live and a practice Take never changes Live occupancy.

Leaving Soft Launch (first Live Take):

1. Confirm the host is HA OS or host-network (section 0). Do not go Live from a Docker bridge container.
2. Run the section 7 smoke test from the command line, one TV first.
3. **Start from an empty Live store.** Practice routes stay in the practice store and are not seen in Live, but a Live store left from an earlier Live session or test is. Tap **Clear room state** (next to Live commit) on the Live iPad, or clear Companion’s data. Clear room state wipes **both** stores (practice and Live). It does not delete named TV sets (`avaccess-tv-sets-v1`).
4. Export the real inventory to `/config/www/avaccess/inventory.json` (section 3) and reload the panel. The **Live commit** button becomes enabled.
5. Turn **Live commit: ON**. Every iPad banner turns red: **LIVE – TVs WILL change**.
6. Take one game to one TV. The summary is headed **Live summary** and each slot shows `ok`. Check the wall. Then try All 35.
7. Use one iPad for Live. Occupancy is still per-iPad (no server ledger), so a second iPad does not know which boxes the first one tuned.

To go back to practice at any time, turn **Live commit** off. Every iPad returns to **PRACTICE** and loads its practice store. Practice Takes from then on do not touch Live occupancy, and turning Live back on reloads the Live store as it was.

---

## 8) iPad

1. Install **Home Assistant Companion**.
2. Connect to `http://<ha-host>:8123` (or your TLS proxy).
3. Sidebar: **Sports Routing** for the bar, **AVAccess Matrix** for favorites.
4. Hold the iPad **sideways** for Sports Routing. Below 900px wide the three columns stack and the buttons get small. Matrix favorites still fit portrait.
5. After a panel update, force-quit Companion (or clear its cache) so it does not keep an old `panel-health.js`. The `?v=` on `module_url` is the cache buster; it is `v=35` in this repo (`homeassistant/config/configuration.yaml`). Bump it when you copy a new `panel-health.js`, then restart Home Assistant. The panel’s own imports (`live-execute.js`, `panel-view.js`, …) carry separate `?v=` values inside `panel-health.js`; copy the whole `www/panels/` directory so they stay in step.

Staff handouts: [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf) _(PDFs pending rebuild; use [STAFF_TRAINING.md](STAFF_TRAINING.md) for the current UI.)_. Matrix cheat sheet: [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md).

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
| 8 | Sports Routing is landscape. Banner reads **PRACTICE – TVs will not change**. Take shows a **PRACTICE summary**. The wall does not change while the yellow line is up |
| 8b | HA runs on HA OS or `network_mode: host` (not a Docker bridge) before any Live Take |
| 8c | **Clear room state** tapped on the Live iPad before the first Live Take; it wipes both the practice and Live stores (section 7b) |
| 8d | Staff know Matrix taps are always live; Sports Routing is live only under the red **LIVE** banner |
| 9 | `sports_schedule.json` source is `directv-sports-info`. `guide_channels.json` source is `tvpassport:5960D` |
| 10 | Selenium add-on is up on port 4444, or a PC pull has replaced `sports_schedule.json` |
| 11 | Saving a named set writes `www/avaccess/custom_tv_sets.json` (`source` `tv-sets`) |

---

## Updating a box that is already live

Turn **Live commit** off first. Then back up what you are about to overwrite and note the commit you are leaving, so the rollback below has something to restore:

```bash
cd /share/avaccess-automator
BACKUP=/config/avaccess-backup/$(date +%Y%m%d-%H%M)
mkdir -p "$BACKUP"
git rev-parse HEAD > "$BACKUP/git-sha.txt"
cp -a /config/www/panels /config/packages /config/dashboards /config/configuration.yaml "$BACKUP/"
cp -a /config/avaccess/*.py "$BACKUP/"

git pull
cp -a homeassistant/config/www/panels/. /config/www/panels/
cp homeassistant/config/packages/avaccess_routing.yaml /config/packages/
cp homeassistant/config/packages/avaccess_sports.yaml /config/packages/
cp homeassistant/config/packages/avaccess_guide.yaml /config/packages/
cp homeassistant/config/avaccess/run_*.py /config/avaccess/
cp scripts/apply_preset.py scripts/directv_shef.py scripts/route_targets.py /config/avaccess/
cp scripts/generate_ha_bundle.py scripts/refresh_ha_weekly.py scripts/sync_weekly_schedule.py /config/avaccess/
```

On HA OS the `run_*.py` wrappers and `directv_shef.py` are **copies**, not symlinks, so `git pull` alone leaves them stale. A stale `run_execute_route_plan.py` does not understand `--live-commit`, and a stale `directv_shef.py` has no `tune_and_verify`; either one makes every Live slot fail. Copy them every time. (The Docker host-network compose bind-mounts these files, so a `git pull` there is enough.)

Copy `sports_schedule.json` or `guide_channels.json` only when the HA host is not already refreshing them. Do not copy `inventory.json` or `custom_tv_sets.json` over the live files. If `panel-health.js` changed, bump `module_url` `?v=` in `configuration.yaml`, restart Home Assistant, and force-quit Companion. Run one PRACTICE Take and the section 7 one-TV smoke test before turning Live commit back on.

---

## Rollback

Use the first step that fixes the problem. Each one is safe to do mid-service.

1. **Stop Live Takes (seconds, every iPad):** turn **Live commit** off on any iPad or in Settings → Helpers. Every iPad returns to **PRACTICE** and Take only plans. A Live Take already running finishes its current slots (at most 50 seconds). Restarting Home Assistant also leaves the boolean off (`initial: false`).
2. **Back to Soft Launch (Live cannot be armed):** copy the repo's placeholder `homeassistant/config/www/avaccess/inventory.json` (still `REPLACE_ME`) over `/config/www/avaccess/inventory.json` and reload the panel. The **Live commit** button is disabled and the banner stays **PRACTICE** even if someone turns the boolean on from Developer Tools. Keep the boolean off too: the script and shell command check only the boolean, not `inventory.json`. Keep your real inventory export somewhere else so you can put it back.
3. **Roll back the code:** restore the backup taken before the update, then restart Home Assistant and force-quit Companion on every iPad:

   ```bash
   BACKUP=/config/avaccess-backup/<timestamp>
   cd /share/avaccess-automator && git checkout "$(cat "$BACKUP/git-sha.txt")"
   cp -a "$BACKUP/panels/." /config/www/panels/
   cp -a "$BACKUP/packages/." /config/packages/
   cp -a "$BACKUP/dashboards/." /config/dashboards/
   cp "$BACKUP/configuration.yaml" /config/configuration.yaml
   cp "$BACKUP"/*.py /config/avaccess/
   ```

   The restored `configuration.yaml` brings back the old `?v=`; Companion still needs a force-quit to drop the newer cached panel. Go back to `main` with `git checkout main` once fixed.
4. **Matrix:** Matrix has no Live switch and no practice mode, so steps 1–2 do not stop it. To stop Matrix taps, restore the previous `/config/packages/avaccess_matrix.yaml` (and its dashboard YAML) from the backup or regenerate it with `--ui-staging` stubs, then restart Home Assistant. To run the wall without either surface, use VDirector or the AVAccess switch's own control and the DirecTV remotes.

iTach IR is **not** on the operator path. `config/itach.example.yaml` and `scripts/send_xumo_ir_itach.py` remain in the repo only as unused leftovers.

---

## Related docs

- [HA_QUICKSTART.md](HA_QUICKSTART.md) — generator flags and helpers
- [DIRECTV_H25_PATCH_AND_TEST_PLAN.md](DIRECTV_H25_PATCH_AND_TEST_PLAN.md) — tests B–F
- [STAFF_QUICK_START.pdf](STAFF_QUICK_START.pdf) and [STAFF_FULL_GUIDE.pdf](STAFF_FULL_GUIDE.pdf) — Sports Routing handouts _(PDFs pending rebuild; use [STAFF_TRAINING.md](STAFF_TRAINING.md) for the current UI.)_
- [OPERATIONS_GUIDE.md](OPERATIONS_GUIDE.md) — Matrix taps (older Sports Routing pictures)
- [WEEKLY_SCHEDULE_SYNC.md](WEEKLY_SCHEDULE_SYNC.md) — ZIP 27403 local-first NFL slots
