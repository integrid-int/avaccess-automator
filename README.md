# avaccess-automator

Home Assistant test environment for validating the **iPad bartender Sports Routing** panel.

## Goals (aligned with AVAccess plan)

This panel is designed for Home Assistant Companion on iPad and implements **Track A** (striped group/program `RoutePlan` planner), **Track B** (hybrid dry-run / live IR+UDP execute when inventory validates), and **Track C** Guide now/next EPG overlay from XMLTV.

- Sports chips filter **EPG-derived** Now/Upcoming programmes on Spectrum sports channels (All / NFL / CFB / NBA / NHL / Other)
- **Spectrum Gold (TV Platinum) channel guide** for ZIP **27403** — full dial, music excluded — with optional **now/next** titles from `guide_epg.json`
- **Groups / Programs** (not whole-TV-set shortcuts for Preset 2/3):
  - **Preset 1 — ALL** — one program → `ENC-01` → all 35 TVs
  - **Preset 2 — 4 Programs** — pick up to 4 programs; striped across `ENC-01`…`ENC-04`; unused encoder slots omitted / left unchanged
  - **Preset 3 — 9 Programs** — pick up to 9 programs; striped across `ENC-01`…`ENC-09`; unused encoder slots omitted / left unchanged
- **Pick TVs (adhoc)** — multi-select TVs 1–35; planner claims the lowest-index free encoder (`ENC-01`…`ENC-10`); errors with **No free encoders** if none are free
- **Hybrid Send (Track B)** — default **Dry-run Send** builds a `RoutePlan`, shows the summary, and updates local occupancy; optional **Live Send** runs iTach IR tune then UDP reconnect when inventory is live-ready
- Dual entry paths remain for Preset 1 and adhoc; Preset 2/3 are **group-first → multi-program picker → Send**
- Clean, large-target UI for bartender speed

**Still out of scope:** telnet free-encoder discovery and zone mapping profiles.

## What this repository provides

- Runnable Home Assistant test environment: `homeassistant/docker-compose.yml`
- Custom panel registered in `homeassistant/config/configuration.yaml`
- Bartender panel module: `homeassistant/config/www/panels/panel-health.js`
- Panel validator: `scripts/validate_panels.py`
- Automated tests: `tests/test_validate_panels.py`

## Python setup for local validation

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements-dev.txt homeassistant
```

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
- `../config` → `/config/avaccess/config` (ro)

For local Core (no Docker), the same paths are available via checked-in symlinks under `homeassistant/config/avaccess/`. The HA package `packages/avaccess_routing.yaml` exposes:

- `input_boolean.avaccess_live_commit` (default **off**)
- `shell_command.avaccess_execute_route_plan` → `avaccess/run_execute_route_plan.py`

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

#### 2. iTach IR codes

Same symlink pattern — remove the link first (or `cp --remove-destination`) so the example is not clobbered:

```bash
rm config/itach.yaml
cp config/itach.example.yaml config/itach.yaml
# edit config/itach.yaml — iTach host, encoder→output map, digit / OK IR codes
```

#### 3. Export inventory JSON (panel Live gate)

After editing inventory YAML, refresh the browser-readable gate file:

```bash
.venv/bin/python scripts/avaccess/export_inventory_json.py \
  --input config/inventory.yaml
```

Output: `homeassistant/config/www/avaccess/inventory.json` (served as `/local/avaccess/inventory.json`). The panel Live gate requires **all** `ENC-01`…`ENC-10` and `RX-01`…`RX-35` hostnames filled (no `REPLACE_ME`) plus non-empty `network.broadcast` and `network.udp_switch_port`. CLI `--live` is narrower: it validates only devices referenced by the plan (and the same network fields).

#### 4. Dry-run vs Live toggle

| Mode | How | Behavior |
|------|-----|----------|
| **Dry-run** (default) | Panel **Live commit** off; HA `input_boolean.avaccess_live_commit` off | Builds/summarizes `RoutePlan`, updates local occupancy only — no IR/UDP |
| **Live** | Panel **Live commit** on **and** inventory JSON live-ready | After local apply, posts plan to `shell_command.avaccess_execute_route_plan` (`plan_b64` + `live: true`) for IR tune → UDP reconnect per slot |

The panel toggle syncs once from `input_boolean.avaccess_live_commit` when `hass` is available. If Live is requested but inventory is not ready, Send still applies locally and records a warning: `Live blocked: inventory not ready`.

Home Assistant `shell_command` often does **not** return script stdout to `hass.callService`. The panel best-effort parses stdout when present and merges per-slot statuses into the Live summary; otherwise check the CLI JSON report or Home Assistant logs for detailed per-slot live results.

#### 5. CLI execute (offline / ops)

```bash
# Dry-run (prints IR/UDP payloads; no network) — default hybrid posture
.venv/bin/python scripts/avaccess/execute_route_plan.py \
  --inventory config/inventory.yaml \
  --itach-config config/itach.yaml \
  --plan-file /tmp/plan.json \
  --dry-run

# Live (validates plan-referenced ENC/RX + network; exit 2 on preflight fail)
.venv/bin/python scripts/avaccess/execute_route_plan.py \
  --inventory config/inventory.yaml \
  --itach-config config/itach.yaml \
  --plan-b64 '<base64-RoutePlan-json>' \
  --live
```

Per slot: IR digits then UDP `msg_b_reconnect`; failures set slot `status` / `error` and execution continues; final JSON report on stdout (`ok` / per-slot status / `errors`). Exit `0` all ok, `1` slot errors, `2` preflight.

#### 6. Still out of scope after Track B

Telnet truth for free-encoder discovery and zone mapping profiles are **not** part of Track B (or Track C Guide EPG).

### Spectrum Gold lineup + Track C Guide/Sports EPG (operators)

The Guide uses the **full Spectrum Gold** dial for ZIP **27403** (mapped from the public tvchannelsguide **TV Platinum** column; music channels excluded). Sports lists come from the same `guide_epg.json` feed (no league APIs, no demo seed games).

This does **not** change Live routing, `RoutePlan`, Send, or encoder logic.

| Artifact | Path |
|----------|------|
| Lineup snapshot | `config/spectrum_lineup_27403.json` (+ `/local/avaccess/spectrum_lineup_27403.json`) |
| Panel channel module | `homeassistant/config/www/panels/spectrum-lineup-data.js` |
| EPG builder | `scripts/avaccess/build_guide_epg.py` |
| EPG config | `config/guide_epg.yaml` |
| Served EPG | `/local/avaccess/guide_epg.json` |

Compose already mounts `../config` → `/config/avaccess/config` and `../scripts/avaccess` → `/config/avaccess/scripts`. The HA package `packages/avaccess_guide.yaml` exposes:

- `shell_command.avaccess_refresh_guide_epg` → `avaccess/run_build_guide_epg.py`

#### 1. Refresh Spectrum lineup (infrequent)

Live HTML pulls may be Cloudflare-blocked; use a saved markdown dump of the Greensboro page (or the committed fixture):

```bash
.venv/bin/python scripts/avaccess/pull_spectrum_lineup.py \
  --from-markdown tests/fixtures/spectrum_greensboro_tvchannelsguide.md
```

This rewrites the JSON snapshot and regenerates `spectrum-lineup-data.js`. Validate with `--check`.

#### 2. Guide EPG config

The repo ships `config/guide_epg.yaml` as a **symlink** to `guide_epg.example.yaml`. Remove it (or use `--remove-destination`) before copying so `cp` does not follow the symlink and overwrite the example:

```bash
rm config/guide_epg.yaml
cp config/guide_epg.example.yaml config/guide_epg.yaml
# edit config/guide_epg.yaml — XMLTV source + channel_number_map
#
# equivalent: cp --remove-destination config/guide_epg.example.yaml config/guide_epg.yaml
```

Point `source` at your XMLTV feed (`file` or `url` + `compression`). Fill `channel_number_map` so Spectrum numbers (from the lineup snapshot — e.g. ESPN **17**, ESPN2 **16**) map to XMLTV channel id(s). Empty lists mean that channel stays in the Guide with blank now/next. `lineup_file` + `sports_window_hours` drive the Sports Now/Upcoming block. When refreshing via the HA `shell_command`, use an **absolute** `source.file` path or a `url` — the process cwd is the HA config directory, not the repo root.

#### 2. Pull league schedules (scraper) then build `guide_epg.json`

```bash
# Live ESPN scoreboards → config/sports_schedule.json
.venv/bin/python scripts/avaccess/pull_sports_schedule.py

# XMLTV now/next for the full lineup (auto name-match) + schedule↔EPG match
.venv/bin/python scripts/avaccess/build_guide_epg.py \
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

The panel fetches `/local/avaccess/guide_epg.json` on connect and about every **15 minutes**. If the feed is missing, unreadable, or `generatedAt` is older than **6 hours**, Guide still lists channels (numbers + names) and shows a muted banner: **Guide listings unavailable — channel list only**. Fresh feeds show **Now** / **Next** titles; search matches number, name, and those titles. Sports chips read the same feed’s `sports` block (schedule + Now/Upcoming).

Sparse now/next usually means the XMLTV feed only covers some networks, or names did not uniquely auto-match — point `source` at a full Greensboro XMLTV and rebuild. The checked-in default may be a demo/fixture build.

## Operator guide — Sports Routing panel

The bartender panel uses a **top chip row** to switch browse modes:

`All · NFL · CFB · NBA · NHL · MLB · WNBA · Other · Guide · TVs`

- **Sport chips** — scraped league schedules (ESPN scoreboards via `pull_sports_schedule.py`) plus EPG Now/Upcoming. Schedule games are tunable only when team names match an EPG sports title.
- **Guide** — full Spectrum Gold dial for ZIP **27403** (category chips + search). Now/next fills for channels whose XMLTV ids are mapped explicitly or auto-matched by display-name. If EPG is missing or older than **6 hours**, channels still list with a muted “Guide listings unavailable” banner.
- **TVs** — starts the **TV-first / adhoc** path (see below).

Group presets and the adhoc TV grid are exclusive modes: bartenders plan either a group (Preset 1/2/3) or an adhoc TV set, not both at once.

### Dry-run vs Live Send (Track B hybrid)

Every Send builds a `RoutePlan`, shows the summary (program → encoder → TV list), and updates local slot/TV occupancy in the browser.

- **Dry-run Send** (default) — occupancy only; no IR or UDP.
- **Live Send** — enable **Live commit** (gated on `/local/avaccess/inventory.json` with all ENC/RX hostnames + network fields); then Send calls HA `shell_command.avaccess_execute_route_plan` for live IR tune + UDP reconnect. Keep `input_boolean.avaccess_live_commit` off unless you intend live routing. When the UI cannot capture shell stdout, use the CLI JSON report or HA logs for per-slot live results.

### Preset 1 — ALL (one program → all TVs)

1. Pick one game or guide channel (content-first), **or** start from TVs / Preset 1 and then choose content.
2. Confirm destination as **Preset 1**.
3. Tap **Dry-run Send**.
4. Plan: one slot — `ENC-01` → TVs `1`–`35`.

### Preset 2 / Preset 3 — striped multi-program groups

These are **Groups / Programs** flows, not “paint one program onto all 35 TVs” or contiguous encoder-block shortcuts.

1. Choose **Preset 2** (up to 4 programs) or **Preset 3** (up to 9 programs) **first**.
2. Multi-select programs from Sports and/or Guide. Selection order is slot order: 1st → `ENC-01`, 2nd → `ENC-02`, and so on.
3. Tap **Dry-run Send** when at least one program is selected (extra taps past capacity are ignored).
4. TVs are assigned **striped** by encoder ordinal `k` (1-based):  
   `tvs = [t for t in 1..35 if (t - 1) % N == (k - 1)]` with `N=4` (Preset 2) or `N=9` (Preset 3).
5. Unused program slots are **omitted** from the plan; those encoders stay unchanged.
6. The dry-run summary lists each chosen program → encoder → striped TV list (for example, Preset 2 with two games shows `ENC-01` / `ENC-02` only).

### Pick TVs — adhoc free encoder

1. Select any non-empty set of TVs 1–35 (content-first destination **Pick TVs**, or TV-first path).
2. Pick **one** program (game or guide channel).
3. Planner claims the **lowest-index free** encoder among `ENC-01`…`ENC-10` (`ENC-10` is eligible as spare).
4. If every encoder is busy, Send is blocked and the panel shows **No free encoders**.
5. Tap **Dry-run Send** to apply the plan locally (occupancy only — no live network).

### Path A — Content-first (Preset 1 and adhoc)

Use when the bartender knows **what** to show first:

1. Tap a **sport chip** or **Guide**.
2. Tap a **game card** or **guide channel row**.
3. On the destination screen, choose **Presets** or **Pick TVs** (exclusive modes):
   - **Presets** — Preset 1 for all-TV one-program; Preset 2/3 enter the multi-program group picker (add more programs as needed).
   - **Pick TVs** — multi-select TVs 1–35 on the grid (adhoc free-encoder path).
4. Tap **Dry-run Send**.
5. Return to the prior browse list with updated badges / occupancy from the dry-run plan.

### Path B — TV-first (adhoc)

Use when the bartender knows **which TVs** need content first:

1. Tap the **TVs** chip.
2. Multi-select grid 1–35 (**Pick TVs**).
3. Tap **Next: Choose content** (requires at least one TV selected).
4. On the content picker, choose **Sports** or **Guide** (exclusive modes):
   - **Sports** — sport chips + game list.
   - **Guide** — ZIP 27403 Spectrum/Xumo list + search.
5. Tap a game or channel.
6. Tap **Dry-run Send** (claims a free encoder for the selected TVs).
7. Return to TVs browse with updated occupancy.

### Assignments / occupancy

Each TV shows one route at a time. Dry-run plans update **slot-aware** occupancy (which encoder is busy, with what label/channel, covering which TVs). Overlapping TVs move to the new plan’s encoder; previous encoders drop those TVs from their local set. State persists in browser `localStorage` on the iPad.

### Cache refresh after UI updates

The panel is loaded via `module_url` in `homeassistant/config/configuration.yaml`. After a UI deploy, bump the query string (currently `?v=13`) and restart Home Assistant if needed. On the iPad, hard-refresh the panel or clear the Companion app cache so the browser does not serve a stale `panel-health.js`.

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
.venv/bin/python -m pytest tests/test_validate_panels.py -q
```
