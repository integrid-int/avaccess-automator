# avaccess-automator

Home Assistant test environment for validating the **iPad bartender Sports Routing** panel.

## Goals (aligned with AVAccess plan)

This panel is designed for Home Assistant Companion on iPad and implements **Track A** (striped group/program `RoutePlan` planner), **Track B** (hybrid dry-run / live DirecTV SHEF + UDP execute when inventory validates), and **Track C** Guide now/next EPG overlay from XMLTV.

- Games listed under **sport chips** (NFL, CFB, NBA, NHL, MLB, WNBA)
- Each game shows **team logos + team names**
- **TV Passport guide** for the ZIP **27403** DirecTV lineup, with **now/next** on the main channels from `guide_epg.json`
- **Groups / Programs** (not whole-TV-set shortcuts for Preset 2/3):
  - **Preset 1 — ALL** — one program → `ENC-01` → all 35 TVs
  - **Preset 2 — 4 Programs** — pick up to 4 programs; striped across `ENC-01`…`ENC-04`; unused encoder slots omitted / left unchanged
  - **Preset 3 — 9 Programs** — pick up to 9 programs; striped across `ENC-01`…`ENC-09`; unused encoder slots omitted / left unchanged
- **Pick TVs (adhoc)** and **named TV sets** — multi-select TVs 1–35, or a saved set such as Patio; planner claims the lowest free encoder (`ENC-01`…`ENC-10`). Only when none are free does it reuse a box the selected TVs already share (with a **Confirm** step listing leftover TVs), or ask staff to choose a program to replace.
- **Hybrid Take (Track B)** — the on-screen button is **Take**. With the header banner at **PRACTICE – TVs will not change** (default), Take builds a `RoutePlan`, shows a **PRACTICE summary**, and updates local occupancy; under **LIVE – TVs WILL change** it calls `script.avaccess_live_execute`, which SHEF-tunes the matching H25 then UDP-reconnects
- Dual entry paths remain for Preset 1 and adhoc; Preset 2/3 are **group-first → multi-program picker → Take**
- Clean, large-target UI for bartender speed

**Still out of scope:** telnet free-encoder discovery and zone mapping profiles.

## What this repository provides

- Runnable Home Assistant test environment: `homeassistant/docker-compose.yml`
- Custom panel registered in `homeassistant/config/configuration.yaml`
- Bartender panel module: `homeassistant/config/www/panels/panel-health.js`
- Panel validator: `scripts/validate_panels.py`
- Automated tests: `tests/test_validate_panels.py`
- DirecTV H25 SHEF transport + Lovelace **AVAccess Matrix** dashboard (favorites / presets / sports tabs)
- **[docs/HA_LIVE.md](docs/HA_LIVE.md)** — site go-live. SHEF, the matrix package, Sports Routing (`panel-health.js?v=35`), DirecTV sports JSON, the TV Passport guide, and named TV sets. Do not clone the repo over `/config`.
- Raspberry Pi host-network deploy (default SSH `pi@gaps`): `scripts/deploy_gaps_pi.sh` (`--init` once, then plain updates) and `homeassistant/docker-compose.host.yml`
- iPad picture playbook: **[docs/OPERATIONS_GUIDE.md](docs/OPERATIONS_GUIDE.md)** and printable **[docs/AVACCESS_OPERATORS_GUIDE.pdf](docs/AVACCESS_OPERATORS_GUIDE.pdf)**
- Sports Routing staff handouts: **[docs/STAFF_QUICK_START.pdf](docs/STAFF_QUICK_START.pdf)** and **[docs/STAFF_FULL_GUIDE.pdf](docs/STAFF_FULL_GUIDE.pdf)** _(PDFs pending rebuild; use [docs/STAFF_TRAINING.md](docs/STAFF_TRAINING.md) for the current UI.)_ Source text: **[docs/STAFF_TRAINING.md](docs/STAFF_TRAINING.md)**
- Cloud HA UI staging: `scripts/prepare_ha_staging.py` (port 8123, `--ui-staging` stubs)

The bartender **Sports Routing** panel is the production iPad UI (`/panel-health`, striped `RoutePlan`). Lovelace Matrix is the SHEF/favorites surface; generate it with `--profile numeric_v1` so Preset 1/2/3 match the operations guide (contiguous splits). Inventory `mapping_profiles.active` stays `striped_v1` for Track B. Matrix has no Live commit gate: on the site HA (no `--ui-staging`) every Matrix tap is live SHEF + UDP. Only Sports Routing has the PRACTICE / LIVE switch.

## Python setup for local validation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt homeassistant
```

The staff/operator PDF builders (`scripts/build_*_pdf*.py`) also need `pip install -r requirements-docs.txt`.

## Configuration reference

Runtime behavior comes from config files and Home Assistant entities, not environment variables. Copy each `*.example.yaml` with `rm -f` + `cp --remove-destination` (see [docs/HA_LIVE.md](docs/HA_LIVE.md) section 3).

| File | Read by | Purpose |
|------|---------|---------|
| `config/inventory.yaml` | executor, `apply_preset.py`, `export_inventory_json.py` | ENC-01…10 / RX-01…35 hostnames, `network.broadcast`, `network.udp_switch_port`, mapping profiles. Ships as a symlink to the example. |
| `config/directv.yaml` (gitignored) | executor, `directv_shef.py` | H25 IPs per encoder, `timeout_seconds` (keep 4), `verify_tune` (default true) |
| `config/channels.yaml` | `generate_ha_bundle.py`, `sync_weekly_schedule.py` | Matrix favorites, presets, `encoder_media_player`, SHEF transport |
| `config/guide_epg.yaml` | `build_guide_epg.py` | Guide now/next grabber and channels |
| `config/schedule_sync.yaml` | `refresh_ha_weekly.py` | Weekly NFL slot sync |
| `www/avaccess/inventory.json` | Sports Routing panel | Live gate. Any `REPLACE_ME` keeps Live commit disabled (Soft Launch) |
| `www/avaccess/sports_schedule.json`, `guide_channels.json`, `guide_epg.json`, `custom_tv_sets.json` | Sports Routing panel | Sports list, Guide, now/next, named TV sets |
| `input_boolean.avaccess_live_commit` (HA) | panel, `script.avaccess_live_execute`, shell command | The one Live switch; `initial: false` |

| Environment variable | Used by | Default |
|----------------------|---------|---------|
| `AVACCESS_HA_OWNER_PASSWORD` | `scripts/complete_ha_onboarding.py` (staging) | none: a random password is generated and printed once |
| `AVACCESS_DIRECTV_BROWSER_PROFILE` | `scripts/avaccess/directv_sports.py` PC pull | `~/.cache/avaccess/directv-sports-browser` (`%LOCALAPPDATA%\avaccess\directv-sports-browser` on Windows) |
| `PYTHON_BIN` | `scripts/run_ha_panel_validation.sh` | `.venv/bin/python`, else `python3` |
| `HA_BASE_URL`, `HASS_TOKENS`, `SHOT_DIR`, `ART_DIR`, `CHROME_PATH` | `scripts/capture_operator_screenshots.mjs` (docs screenshots) | `http://127.0.0.1:8123`, `/tmp/hassTokens.json`, `docs/images/operations`, `/opt/cursor/artifacts/screenshots`, first Chrome found |
| `TZ` | Docker compose | `UTC` in `homeassistant/docker-compose.yml`; `America/New_York` in the staging and Live host-network compose |

## Home Assistant test environment

1. Start Home Assistant:

   ```bash
   docker compose -f homeassistant/docker-compose.yml up -d
   ```

   If Docker is unavailable, run Core from the venv:

   ```bash
   .venv/bin/python -m homeassistant --config homeassistant/config
   ```

2. Validate configuration:

   ```bash
   docker exec ha_panel_test python -m homeassistant --script check_config --config /config
   ```

   or local fallback:

   ```bash
   .venv/bin/python -m homeassistant --script check_config --config homeassistant/config
   ```

3. Open Home Assistant:
   - URL: `http://localhost:8123`
   - Panel path: `/panel-health`
   - Sidebar title: `Sports Routing`

### Track B — live routing setup (operators)

Canonical Python lives at `scripts/avaccess/`; device YAML at `config/`.

Compose binds these into the HA config tree (see `homeassistant/docker-compose.yml`):

- `../scripts/avaccess` → `/config/avaccess/scripts` (ro)
- `../scripts/directv_shef.py` → `/config/avaccess/directv_shef.py` (ro; not inside the scripts mount)
- `../config` → `/config/avaccess/config` (ro)

For local Core (no Docker), the same paths are available via checked-in symlinks under `homeassistant/config/avaccess/`. The HA package `packages/avaccess_routing.yaml` exposes:

- `input_boolean.avaccess_live_commit` (default **off**)
- `script.avaccess_live_execute` — Live Take entry point; runs the executor only while the boolean is on
- `shell_command.avaccess_execute_route_plan` → `avaccess/run_execute_route_plan.py` (renders `--live-commit on|off` from the boolean; the wrapper refuses `--live` unless it is `on`)

#### 1. Inventory hostnames

The repo ships `config/inventory.yaml` as a **symlink** to `inventory.example.yaml`. Remove it (or use `--remove-destination`) before copying so `cp` does not follow the symlink and overwrite the example:

```bash
rm config/inventory.yaml
cp config/inventory.example.yaml config/inventory.yaml
# edit config/inventory.yaml — real TX/RX hostnames, broadcast/port
#
# equivalent: cp --remove-destination config/inventory.example.yaml config/inventory.yaml
```

Fill every `REPLACE_ME` hostname for encoders (`ENC-01`…`ENC-10`) and receivers (`RX-01`…`RX-35`), plus non-empty `network.broadcast` and `network.udp_switch_port`.

#### 2. DirecTV H25 SHEF map

`config/directv.yaml` is gitignored. It is not a tracked symlink. Copy the example, then put in real H25 IPs. If an old checkout left a symlink, remove it first so `cp` does not follow it and overwrite `directv.example.yaml`. Do not leave the placeholder `192.168.10.151`–`.160` addresses in place.

```bash
rm -f config/directv.yaml
cp --remove-destination config/directv.example.yaml config/directv.yaml
# edit config/directv.yaml — H25 IPs, ENC-01…ENC-10 → H25-01…H25-10
```

#### 3. Export inventory JSON (panel Live gate)

After editing inventory YAML, refresh the browser-readable gate file:

```bash
.venv/bin/python scripts/avaccess/export_inventory_json.py \
  --input config/inventory.yaml
```

Output: `homeassistant/config/www/avaccess/inventory.json` (served as `/local/avaccess/inventory.json`). The panel Live gate requires **all** `ENC-01`…`ENC-10` and `RX-01`…`RX-35` hostnames filled (no `REPLACE_ME`) plus non-empty `network.broadcast` and `network.udp_switch_port`. CLI `--live` is narrower: it validates only devices referenced by the plan (and the same network fields).

#### 4. PRACTICE vs LIVE toggle

| Mode | How | Behavior |
|------|-----|----------|
| **PRACTICE** (default; dry-run) | Panel **Live commit: OFF**; HA `input_boolean.avaccess_live_commit` off, or inventory not live-ready | Banner **PRACTICE – TVs will not change**. Builds/summarizes `RoutePlan` (**PRACTICE summary**), updates local occupancy only — no SHEF/UDP |
| **LIVE** | HA `input_boolean.avaccess_live_commit` on **and** inventory JSON live-ready | Banner **LIVE – TVs WILL change** (red). Calls `script.avaccess_live_execute` (`plan_b64`), which refuses unless the boolean is on, then SHEF `/tv/tune` (verified) → UDP reconnect per slot (UDP hostnames always re-read from inventory). Summary is **Live summary** |

The panel's **Live commit** button turns `input_boolean.avaccess_live_commit` on/off in HA and re-reads it on every state update, so all iPads agree. If Live is requested but inventory is not ready, Take still applies locally and records a warning: `Live blocked: inventory not ready`. The on-screen button is **Take**, not Send (it reads **Confirm** before reusing a shared box, **Replace** after choosing a program to retune, and **Sending…** while a Live call is in flight).

Live Take calls the script with `returnResponse`, so the panel gets the executor's stdout/returncode back. A missing report, `ok: false`, or a nonzero `returncode` shows an error in the Live summary; occupancy is saved only for slots that returned `ok`. Take is blocked when a selected program has no DirecTV channel, and Live Take is blocked on the demo sports fallback. Soft Launch conditions and the first-Live checklist (practice and Live occupancy are separate stores; **Clear room state** wipes both) are in [docs/HA_LIVE.md](docs/HA_LIVE.md) section 7b.

#### 5. CLI execute (offline / ops)

```bash
# Dry-run (prints SHEF/UDP payloads; no network) — default hybrid posture
.venv/bin/python scripts/avaccess/execute_route_plan.py \
  --inventory config/inventory.yaml \
  --directv-config config/directv.yaml \
  --plan-file /tmp/plan.json \
  --dry-run

# Live (validates plan-referenced ENC/RX, H25 map, and network; exit 2 on preflight fail)
.venv/bin/python scripts/avaccess/execute_route_plan.py \
  --inventory config/inventory.yaml \
  --directv-config config/directv.yaml \
  --plan-b64 '<base64-RoutePlan-json>' \
  --live
```

Per slot: DirecTV SHEF `/tv/tune` then UDP `msg_b_reconnect`. If SHEF tune fails, UDP is **not** sent for that slot, so those TVs stay on the previous source. Other slots still run. Failures set slot `status` / `error`. Final JSON report on stdout (`ok` / per-slot status / `errors` / `elapsedMs`). Exit `0` all ok, `1` slot errors, `2` preflight (bad inventory or a slot's encoder has no H25 mapping).

Live stops starting slots once a slot could run past 50 s (`--time-budget`, default 50), because Home Assistant kills a shell command at 60 s and the panel would then get no report. Slots it skips come back as `Not attempted: …` errors and nothing is sent to them. `python3 tests/bench_live_latency.py` times the real CLI against fake H25s (healthy, offline, and slow-verify cases).

#### 6. Still out of scope after Track B

Telnet truth for free-encoder discovery and zone mapping profiles are **not** part of Track B (or Track C Guide EPG).

### Track C — Guide EPG now/next (operators)

Track C overlays **now/next** program titles on the fixed ZIP **27403** Guide lineup. It does **not** change Live routing, `RoutePlan`, Send, or encoder logic.

Canonical builder: `scripts/avaccess/build_guide_epg.py`. Config: `config/guide_epg.yaml`. Output served as `/local/avaccess/guide_epg.json`.

Compose already mounts `../config` → `/config/avaccess/config` and `../scripts/avaccess` → `/config/avaccess/scripts`. The HA package `packages/avaccess_guide.yaml` exposes:

- `shell_command.avaccess_refresh_guide_epg` → `avaccess/run_build_guide_epg.py`

#### 1. Guide EPG config

The guide list is the DirecTV Greensboro lineup on TV Passport (`scripts/avaccess/directv_lineup.py` → `guide_channels.json`). It keeps every channel in that lineup except music audio, pay-per-view, promo barkers, and channels that are not in the package (on-demand storefronts and duplicate 9xxx grids). Sports pages do not use this file. `config/guide_epg.yaml` then grabs now/next from TV Passport (the `tvpassport.com` site in [iptv-org/epg](https://github.com/iptv-org/epg)) for the main locals and sports channels. The grabber is Python (`scripts/avaccess/tvpassport.py`) because the HA image does not ship Node. Guide search waits briefly before filtering so typing does not steal the cursor. **Now** lists every TV and the program on it.

`config/guide_epg.example.yaml` is the offline fixture (no `grabber` key). Use it when you want to build from your own XMLTV file or URL instead of TV Passport. When refreshing via the HA `shell_command` without the grabber, use an **absolute** `source.file` path or a `url` — the process cwd is the HA config directory, not the repo root.

#### 2. Build / refresh `guide_epg.json`

CLI (from repo root). This hits TV Passport, then writes now/next:

```bash
python3 scripts/avaccess/build_guide_epg.py \
  --config config/guide_epg.yaml \
  --out homeassistant/config/www/avaccess/guide_epg.json
```

From Home Assistant (Developer Tools → Actions, or automation):

```yaml
action: shell_command.avaccess_refresh_guide_epg
```

Optional hourly refresh (example — add to `automations.yaml` or a package if desired):

```yaml
# automation:
#   - id: avaccess_refresh_guide_epg_hourly
#     alias: AVAccess refresh Guide EPG
#     trigger:
#       - platform: time_pattern
#         hours: "/1"
#     action:
#       - service: shell_command.avaccess_refresh_guide_epg
```

#### 3. Stale feed and banner

The panel fetches `/local/avaccess/guide_epg.json` on connect and about every **15 minutes**. If the feed is missing, unreadable, or `generatedAt` is older than **6 hours**, Guide still lists channels (numbers + names) and shows a muted banner: **Guide listings unavailable — channel list only**. Fresh feeds show **Now** / **Next** titles; search matches number, name, and those titles. Sport chips are unchanged.

The checked-in `guide_epg.json` is a snapshot from the last grab. If `generatedAt` is older than **6 hours**, Guide falls back to the channel list and the banner. Refresh with the builder above (or the HA shell command) to fill now/next again. Choosing a Guide channel and pressing Take plans a DirecTV tune to that major; the dry-run summary shows `Tune` plus the channel number. Games do not tune.

## Operator guide — Sports Routing panel

Staff handouts, with screenshots of the landscape iPad: **[docs/STAFF_QUICK_START.pdf](docs/STAFF_QUICK_START.pdf)** and **[docs/STAFF_FULL_GUIDE.pdf](docs/STAFF_FULL_GUIDE.pdf)** _(PDFs pending rebuild; use [docs/STAFF_TRAINING.md](docs/STAFF_TRAINING.md) for the current UI.)_ Source text: **[docs/STAFF_TRAINING.md](docs/STAFF_TRAINING.md)**.

On a landscape iPad (wider than 900px) the panel is three columns: a left rail (**Guide**, **Now**, and **Sets** pinned at the top, then DirecTV sports in their own scrolling list), **Sources** in the middle, and **Displays** on the right, with **Take** along the bottom. The rail and the lists scroll by dragging. iPad Safari and the Home Assistant Companion use overlay scrollbars that fade, so the panel does not hide them. A desktop browser still draws a permanent bar; that is Chrome, not the iPad.

- **Sports rail** — DirecTV’s own categories (Football, Basketball, Soccer, and the rest of the sports page). A category with more than one league gets chips in the Sources column (NFL, NCAA Football, NBA, NCAA Basketball (M), and so on). Each list is filled from `/local/avaccess/sports_schedule.json` for ZIP **27403**, and that file has to come from DirecTV sports-info (`source: directv-sports-info`). TV Passport is not a sports source. The panel reloads that file on connect and about every **15 minutes**. A game with no satellite major stays on the list and does not tune.
- **Guide** — the TV Passport DirecTV lineup for ZIP **27403**, opened from the top of the left rail. Music audio, pay-per-view, barkers, and channels that are not in the package are left out. **Now/next** shows when `guide_epg.json` is fresh. Search matches channel number, name, and now/next titles. If EPG is missing or older than **6 hours**, channels still list with a muted “Guide listings unavailable” banner.
- **Now** — this iPad's assignment list for TVs 1–35, also at the top of the left rail. TVs with no plan here read **Unassigned** (still showing the last box), not Off. PRACTICE and LIVE keep separate occupancy, so Now shows the list for the current mode. **Clear room state** (next to Live commit) wipes both of this iPad's occupancy stores.
- **Displays** — **All 35 TVs** (Preset 1), **4 Programs**, **9 Programs**, **Pick TVs**, or a named TV set (the adhoc path below). The on-screen button is **Take**. Under the **PRACTICE** banner it is a dry run. **Sets**, at the top of the left rail, saves those names (Patio, Bar) on the iPad and, when Home Assistant is connected, through `shell_command.avaccess_save_tv_sets` into `custom_tv_sets.json`.
- **No free box** — a named set or Pick TVs prefers a free DirecTV box (ENC-01–ENC-10). Only when none are free: if every selected TV is already on one box, Take reuses it after **Confirm**. If not, the middle column lists the programs already on; choose one and Take becomes **Replace** (then **Confirm** if there are leftover TVs). That box changes channel. TVs that were on it and are not in the set keep showing the retuned program until reassigned; nothing turns them off. All 35, 4 Programs, and 9 Programs do not use this path.

### Sports schedule refresh

DirecTV returns **one calendar day** per request (`days=YYYY-MM-DD`). A full slate is those days merged on game id. The sports page customer type for this account is **Bars and Restaurants** (`bundles=20`). The response still includes residential and private-office packages. A channel is used only when one of its packages is marked for public viewing (`commercial_public`). Private-office packs such as Sports Choice are not tune targets. Greensboro locals **2, 8, 12, and 45** stay, because the commercial headend carries them even when DirecTV tags them with the residential MySports package. Out-of-market **NBA** games are the exception: they show up when the page is on the residential customer type with the **NBA League Pass** add-on, and those feeds are kept even though DirecTV marks the Premium numbers off-satellite. Residential-only tiers (Choice, Ultimate, Sports Pack, Peacock, ESPN Unlimited) are not tune targets. A Python download of DirecTV from the Home Assistant container is refused. Do not paste Cookie or XSRF values into a script.

On Home Assistant OS, install and start the [Selenium Standalone add-on](https://github.com/davida72/selenium-homeassistant) so port **4444** is up. Each morning at 06:00 (Home Assistant local time) `shell_command.avaccess_refresh_sports` asks that browser for the next 8 days and writes `www/avaccess/sports_schedule.json`. The package is `packages/avaccess_sports.yaml`.

A PC that can already open the sports page can pull the same file:

```bash
pip install playwright
python3 scripts/avaccess/directv_sports.py --pull --ahead 8 \
  --out homeassistant/config/www/avaccess/sports_schedule.json
```

`--ahead 8` is today through the next week in Eastern time (the Monday-night game can fall on the following UTC date). If a hidden window is refused, add `--headed`. A saved games response still works with `--file games-2026-10-25.json` (repeat `--file` for each day).

Group presets and the adhoc TV grid are exclusive modes: bartenders plan either a group (Preset 1/2/3) or an adhoc TV set, not both at once.

### PRACTICE vs LIVE Take (Track B hybrid)

Every **Take** builds a `RoutePlan` and shows the summary (program → encoder → TV list). The header banner says which kind of Take it is.

- **PRACTICE – TVs will not change** (default) — **PRACTICE summary**; updates local occupancy for training; no SHEF or UDP.
- **LIVE – TVs WILL change** — turn **Live commit: ON** (button enabled only when `/local/avaccess/inventory.json` has all ENC/RX hostnames + network fields); Take then calls HA `script.avaccess_live_execute` (with `returnResponse`) for live SHEF tune + UDP reconnect. **Live summary** shows per-slot `ok` / `error`; occupancy is saved only for `ok` slots. Keep `input_boolean.avaccess_live_commit` off unless you intend live routing. Run Live only from HA OS or a host-network container ([docs/HA_LIVE.md](docs/HA_LIVE.md) section 0).

### Preset 1 — ALL (one program → all TVs)

1. Pick one game or guide channel (content-first), **or** start from TVs / Preset 1 and then choose content.
2. Confirm destination as **Preset 1**.
3. Tap **Take**.
4. Plan: one slot — `ENC-01` → TVs `1`–`35`.

### Preset 2 / Preset 3 — striped multi-program groups

These are **Groups / Programs** flows, not “paint one program onto all 35 TVs” or contiguous encoder-block shortcuts.

1. Choose **Preset 2** (up to 4 programs) or **Preset 3** (up to 9 programs) **first**.
2. Multi-select programs from Sports and/or Guide. Selection order is slot order: 1st → `ENC-01`, 2nd → `ENC-02`, and so on.
3. Tap **Take** when at least one program is selected (extra taps past capacity are ignored).
4. TVs are assigned **striped** by encoder ordinal `k` (1-based):  
   `tvs = [t for t in 1..35 if (t - 1) % N == (k - 1)]` with `N=4` (Preset 2) or `N=9` (Preset 3).
5. Unused program slots are **omitted** from the plan; those encoders stay unchanged.
6. The summary lists each chosen program → encoder → striped TV list (for example, Preset 2 with two games shows `ENC-01` / `ENC-02` only).

### Pick TVs — adhoc free encoder

1. Select any non-empty set of TVs 1–35 (content-first destination **Pick TVs**, or TV-first path).
2. Pick **one** program (game or guide channel).
3. Planner claims the **lowest-index free** encoder among `ENC-01`…`ENC-10` (`ENC-10` is eligible as spare).
4. If every encoder is busy, the panel shows **All DirecTV boxes are in use**: it reuses a box the selected TVs already share (after **Confirm**), or asks staff to choose a program to replace.
5. Tap **Take**. Under PRACTICE this applies the plan locally (occupancy only — no live network).

### Path A — Content-first (Preset 1 and adhoc)

Use when the bartender knows **what** to show first:

1. Tap a **sport chip** or **Guide**.
2. Tap a **game card** or **guide channel row**.
3. On the destination screen, choose **Presets** or **Pick TVs** (exclusive modes):
   - **Presets** — Preset 1 for all-TV one-program; Preset 2/3 enter the multi-program group picker (add more programs as needed).
   - **Pick TVs** — multi-select TVs 1–35 on the grid (adhoc free-encoder path).
4. Tap **Take**.
5. Return to the prior browse list with updated badges / occupancy from the plan.

### Path B — TV-first (adhoc)

Use when the bartender knows **which TVs** need content first:

1. Tap the **TVs** chip.
2. Multi-select grid 1–35 (**Pick TVs**).
3. Tap **Next: Choose content** (requires at least one TV selected).
4. On the content picker, choose **Sports** or **Guide** (exclusive modes):
   - **Sports** — sport chips + game list.
   - **Guide** — ZIP 27403 DirecTV list + search.
5. Tap a game or channel.
6. Tap **Take** (claims a free encoder for the selected TVs).
7. Return to TVs browse with updated occupancy.

### Assignments / occupancy

Each TV shows one route at a time. PRACTICE plans, and the `ok` slots of a Live plan, update **slot-aware** occupancy (which encoder is busy, with what label/channel, covering which TVs). Overlapping TVs move to the new plan’s encoder; previous encoders drop those TVs from their local set. State persists in browser `localStorage` on the iPad, per iPad only; there is no server ledger. Practice and Live occupancy are separate stores: PRACTICE Takes read and write `avaccess-bartender-panel-practice-v1`, and Live Takes (Live commit on and inventory ready) read and write `avaccess-bartender-panel-v2`. Switching modes reloads the target store (no merge), so practice routes are never treated as busy boxes in Live and a practice Take never changes Live occupancy. The planner’s busy encoders and the Now screen use the store for the current mode. **Clear room state** wipes both stores.

### Cache refresh after UI updates

The panel is loaded via `module_url` in `homeassistant/config/configuration.yaml`. After a UI deploy, bump the query string (currently `?v=35`) and restart Home Assistant if needed. On the iPad, force-quit Companion or clear its cache so it does not serve a stale `panel-health.js`. Copy `www/panels/`. Do not recopy `inventory.json` or `custom_tv_sets.json` over the live files. The site steps are [docs/HA_LIVE.md](docs/HA_LIVE.md).

## Panel validation workflows

### Static panel validation

```bash
.venv/bin/python scripts/validate_panels.py --config-dir homeassistant/config
```

### End-to-end validation (static + Home Assistant config check)

```bash
bash scripts/run_ha_panel_validation.sh
```

Notes:
- If Docker is available, the script validates inside a Home Assistant container.
- If Docker is not available, it falls back to local `homeassistant --script check_config`.
- The script auto-prefers `.venv/bin/python` when present.

### Run automated tests

```bash
python3 -m unittest discover -s tests -p 'test_*.py' -q
node --test tests/js/*.test.js
```

Every Python test is a `unittest.TestCase`, so pytest is optional (`.venv/bin/python -m pytest tests -q` runs the same tests). The JS tests run on Node 22; `tests/js/panel-harness.js` stubs the DOM so `panel-send.test.js` and `panel-render.test.js` can drive the real panel.
