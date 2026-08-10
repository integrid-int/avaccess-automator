# avaccess-automator

Home Assistant test environment for validating the **iPad bartender Sports Routing** panel.

## Goals (aligned with AVAccess plan)

This panel is designed for Home Assistant Companion on iPad and mirrors the Phase 2 sports-routing workflow:

- Games listed under **sport chips** (NFL, CFB, NBA, NHL, MLB, WNBA)
- Each game shows **team logos + team names**
- **Spectrum channel guide** for ZIP **27403** (Spectrum / Xumo tune numbers and labels)
- **Groups = project presets**:
  - Preset 1 — ALL (all 35 TVs)
  - Preset 2 — 4 Programs (encoder blocks)
  - Preset 3 — 9 Programs (encoder blocks)
- **Individuals = TVs 1–35**, with adhoc multi-select
- **Dual entry paths:** content-first (pick game/channel, then TVs) or TV-first (pick TVs, then content)
- Clean, large-target UI for bartender speed

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

## Operator guide — Sports Routing panel

The bartender panel uses a **top chip row** to switch browse modes:

`NFL · CFB · NBA · NHL · MLB · WNBA · Guide · TVs`

- **Sport chips** — tap NFL, CFB, NBA, NHL, MLB, or WNBA to browse that sport’s game list. Tap a game card to choose it.
- **Guide** — opens the Spectrum / Xumo channel lineup for ZIP **27403**. Use the search field to filter by channel number or name. Tap a row to choose a channel.
- **TVs** — starts the **TV-first** path (see below).

Presets (`1_all`, `2_four_programs`, `3_nine_programs`) and the TV grid (1–35) are **never shown together** on the same step. The UI uses exclusive mode switches so bartenders pick either presets or adhoc TVs, not both at once.

### Path A — Content-first (default)

Use when the bartender knows **what** to show first:

1. Tap a **sport chip** or **Guide**.
2. Tap a **game card** or **guide channel row**.
3. On the destination screen, choose **Presets** or **Pick TVs** (exclusive modes):
   - **Presets** — Preset 1 (all 35 TVs), Preset 2 (4 Programs), or Preset 3 (9 Programs).
   - **Pick TVs** — multi-select TVs 1–35 on the grid.
4. Tap **Send to TVs**.
5. Return to the prior browse list; assigned TVs show updated badges.

### Path B — TV-first

Use when the bartender knows **which TVs** need content first:

1. Tap the **TVs** chip.
2. On the TV browse screen, use the exclusive mode switch:
   - **Pick TVs** — multi-select grid 1–35.
   - **Presets** — Preset 1/2/3 as a quick fill for the TV selection.
3. Tap **Next: Choose content** (requires at least one TV selected).
4. On the content picker, choose **Sports** or **Guide** (exclusive modes — not both lists at once):
   - **Sports** — sport chips + game list.
   - **Guide** — ZIP 27403 Spectrum/Xumo list + search.
5. Tap a game or channel.
6. Tap **Send to N TVs** (TVs were already chosen; no second TV picker).
7. Return to TVs browse with updated occupancy.

### Assignments

Each TV can only show one route (game or guide channel). When you send a new assignment, overlapping TVs are removed from any previous route automatically. Assignments persist in browser `localStorage` on the iPad.

### Cache refresh after UI updates

The panel is loaded via `module_url` in `homeassistant/config/configuration.yaml`. After a UI deploy, bump the query string (currently `?v=6`) and restart Home Assistant if needed. On the iPad, hard-refresh the panel or clear the Companion app cache so the browser does not serve a stale `panel-health.js`.

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
