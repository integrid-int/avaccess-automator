# avaccess-automator

Home Assistant test environment for validating the **iPad bartender Sports Routing** panel.

## Goals (aligned with AVAccess plan)

This panel is designed for Home Assistant Companion on iPad and implements **Track A** of the AVAccess route planner: group/program planning with a dry-run `RoutePlan` (no live UDP/IR).

- Games listed under **sport chips** (NFL, CFB, NBA, NHL, MLB, WNBA)
- Each game shows **team logos + team names**
- **Spectrum channel guide** for ZIP **27403** (Spectrum / Xumo tune numbers and labels)
- **Groups / Programs** (not whole-TV-set shortcuts for Preset 2/3):
  - **Preset 1 — ALL** — one program → `ENC-01` → all 35 TVs
  - **Preset 2 — 4 Programs** — pick up to 4 programs; striped across `ENC-01`…`ENC-04`; unused encoder slots omitted / left unchanged
  - **Preset 3 — 9 Programs** — pick up to 9 programs; striped across `ENC-01`…`ENC-09`; unused encoder slots omitted / left unchanged
- **Pick TVs (adhoc)** — multi-select TVs 1–35; planner claims the lowest-index free encoder (`ENC-01`…`ENC-10`); errors with **No free encoders** if none are free
- **Send is dry-run only (Track A)** — builds a `RoutePlan`, shows the summary, and updates local occupancy; **no live UDP or IR**
- Dual entry paths remain for Preset 1 and adhoc; Preset 2/3 are **group-first → multi-program picker → Dry-run Send**
- Clean, large-target UI for bartender speed

Track B (live UDP/IR) and Track C (EPG now/next) are out of scope for this panel revision.

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

- **Sport chips** — tap NFL, CFB, NBA, NHL, MLB, or WNBA to browse that sport’s game list.
- **Guide** — opens the Spectrum / Xumo channel lineup for ZIP **27403**. Use the search field to filter by channel number or name. (Static lineup only — **no EPG now/next** in Track A.)
- **TVs** — starts the **TV-first / adhoc** path (see below).

Group presets and the adhoc TV grid are exclusive modes: bartenders plan either a group (Preset 1/2/3) or an adhoc TV set, not both at once.

### Dry-run Send (Track A)

Every **Dry-run Send** builds a `RoutePlan`, shows the dry-run summary (program → encoder → TV list), and updates local slot/TV occupancy in the browser. It does **not** emit live UDP reconnects or IR tunes. Live commit is Track B.

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

The panel is loaded via `module_url` in `homeassistant/config/configuration.yaml`. After a UI deploy, bump the query string (currently `?v=9`) and restart Home Assistant if needed. On the iPad, hard-refresh the panel or clear the Companion app cache so the browser does not serve a stale `panel-health.js`.

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
