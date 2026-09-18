# Home Assistant staging — A2 UI checklist

Walked: 2026-09-18 against live `http://127.0.0.1:8123` (HA **2026.9.3**, container `avaccess-ha-staging`).

Plan: `docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md` section A2.

**Overall: PASS** (cloud Chrome desktop + 768×1024 viewport). Real iPad Safari / HA Companion was not on this VM; remaining device caveats are below.

## Onboarding

| Item | Value |
|------|--------|
| Method | Home Assistant REST API (not the HTML wizard) |
| User created | `POST /api/onboarding/users` → `{client_id:"http://127.0.0.1:8123/", name:"Operator", username:"operator", password:"avaccess-staging", language:"en"}` → `auth_code` |
| Token exchange | `POST /auth/token` `grant_type=authorization_code` `client_id=http://127.0.0.1:8123/` |
| Core config | `POST /api/onboarding/core_config` with Bearer: `location_name=AVAccess Staging`, `language=en`, `country=US`, `timezone=America/New_York`, `unit_system=us_customary`, `currency=USD` → 200 |
| Analytics | `POST /api/onboarding/analytics` `{}` (skip/disable) → 200 |
| Integration | `POST /api/onboarding/integration` `{"client_id":"http://127.0.0.1:8123/","redirect_uri":"http://127.0.0.1:8123/?auth_callback=1"}` → 200 + `auth_code`. Empty body failed (`client_id` required); missing `redirect_uri` also 400. |
| After | `GET /` **200** (no longer 302 `/onboarding.html`). `GET /api/onboarding` is **404** once complete. |
| Owner | **username `operator` / password `avaccess-staging`** |
| Long-lived token | Created via websocket `auth/long_lived_access_token` client_name `avaccess-a2-checklist`, lifespan 365 days. Stored only in gitignored `homeassistant/staging/config/.a2_auth.json` (not committed). |

`GET /api/config`: `location_name=AVAccess Staging`, `currency=USD`, US customary units, `version=2026.9.3`, `state=RUNNING`. `time_zone` still reported **UTC** after the core_config POST on this boot (staging YAML now sets `time_zone: America/New_York` for the next prepare/restart).

## A2 UI bug checklist

| Check | Result | Notes |
|-------|--------|-------|
| Control tab loads without red "entity not found" for program/channel/target helpers | **Pass** | Chrome 1280×800 and 768×1024. Helpers show `program_a` / `espn` / `RX-01,RX-02`. Websocket `lovelace/config` `url_path=avaccess-matrix` matches YAML. No red missing-entity cards. |
| Favorites row: FOX / NFL Afternoon / All Sunday are large enough to tap on iPad | **Pass** | Buttons **FOX Local**, **NFL Afternoon Games**, **All NFL Sunday Games** (3-column grid). On 768×1024 the longer names wrap 2–3 lines but remain large tappable HA button cards. Not verified on physical iPad Safari. |
| Preset 1/2/3 buttons visible without horizontal scroll | **Pass** | **Preset 1 ALL**, **Preset 2 4 Programs**, **Preset 3 9 Programs** all visible in one row at desktop and 768×1024. No horizontal scroll in screenshots. |
| Program A–I grid fits portrait iPad | **Pass** | 3×3 grid of Program A–I fully visible in 768×1024 Control screenshot. |
| Channel buttons wrap; NFL S1–S9 readable | **Pass** | S1–S8 labeled `NFL S1`…`NFL S8` on this walk. Slot 9 was **`S9 NFL Slot`** in the example YAML; renamed to **`NFL S9`** after the walk so the grid is consistent. |
| **NFL / College Football / Basketball** tabs switch and keep destination card | **Pass** | Views `nfl` / `cfb` / `hoops`. Each keeps Selection helpers, Destination card, and **Route Program -> TVs**. Header tab icons switch (football / helmet / basketball). |
| Now Playing card: unavailable entities are acceptable in staging; must not break the view | **Pass** | `sensor.directv_h25_01`–`_09`, state `STAGING - DirecTV not connected`. No `media_player.*` entities. Card does not break the view. |
| Tap Favorite FOX → script runs (log shows STAGING echo, no traceback) | **Pass** | `POST /api/services/script/avaccess_favorite_fox` 200; `last_triggered=2026-09-18T16:54:20Z`. Logs: `STAGING avaccess_preset_1_all` then `STAGING avaccess_directv_tune`. No traceback. |
| Tap Route Program → TVs with `RX-01,RX-02` → script runs | **Pass** | Set `input_text.avaccess_target_rxs` to `RX-01,RX-02`, then `script.avaccess_route_selected_program_to_tvs` and `script.avaccess_route_program_to_tvs` with `{program:program_a, targets:RX-01,RX-02}`. Both 200. Logs: `STAGING avaccess_route_targets` twice. UI button calls `script.avaccess_route_selected_program_to_tvs`. |
| Settings/Guide views on pretty dashboard (if used) do not 404 | **N/A / Pass** | Pretty dashboard is **not** loaded. Staging Lovelace YAML is only `dashboards/avaccess_matrix.yaml` (`avaccess-matrix`). Default `/lovelace` returns 200. No Settings/Guide paths in this dashboard. |
| Browser console / HA logs: no YAML parse errors after restart | **Pass** | Current boot (`Home Assistant initialized in 1.51s`, 2026.9.3): no YAML parse / Invalid config / traceback from AVAccess package. Lovelace YAML dashboard rendered. Browser console was not captured (headless CDP); UI loaded without HA error cards. |

## Entity list summary (`GET /api/states`)

Helpers (all present):

- `input_select.avaccess_program` = `program_a`
- `input_select.avaccess_channel` = `espn`
- `input_text.avaccess_target_rxs` = `RX-01,RX-02`

Scripts required by A2 (all present, plus `script.avaccess_route_selected_program_to_tvs`):

| Entity | Friendly name |
|--------|----------------|
| `script.avaccess_favorite_fox` | AVAccess Favorite FOX Local |
| `script.avaccess_favorite_nfl_afternoon_games` | AVAccess Favorite NFL Afternoon Games |
| `script.avaccess_favorite_all_nfl_sunday_games` | AVAccess Favorite All NFL Sunday Games |
| `script.avaccess_preset_1_all` | AVAccess Preset 1_all |
| `script.avaccess_preset_2_four_programs` | AVAccess Preset 2_four_programs |
| `script.avaccess_preset_3_nine_programs` | AVAccess Preset 3_nine_programs |
| `script.avaccess_tune_channel` | AVAccess tune channel on source |
| `script.avaccess_route_program_to_tvs` | AVAccess route program to TVs |
| `script.avaccess_route_selected_program_to_tvs` | AVAccess route selected program to TVs |

32 `script.avaccess_*` entities total (tune shortcuts for ESPN/ESPN2/FS1/TNT/locals/NFL A1–A4/S1–S9 included).

Dummy Now Playing sensors (9/9):

| Entity | State |
|--------|--------|
| `sensor.directv_h25_01` … `sensor.directv_h25_09` | `STAGING - DirecTV not connected` |

No `media_player.directv_*`. Dashboard Now Playing cards reference `sensor.directv_h25_*` only.

Lovelace: websocket `lovelace/config` with `url_path=avaccess-matrix` succeeded. REST `/api/lovelace/avaccess-matrix` is 404 (YAML dashboards are not that REST path). File: `homeassistant/staging/config/dashboards/avaccess_matrix.yaml`.

## Script call results

| Call | HTTP | last_triggered | Log evidence |
|------|------|----------------|--------------|
| `POST /api/services/script/avaccess_favorite_fox` `{}` | 200 | 2026-09-18T16:54:20.652Z | `echo "STAGING avaccess_preset_1_all"` rc=0; delay 2s; `echo "STAGING avaccess_directv_tune"` rc=0 |
| `POST /api/services/input_text/set_value` `{entity_id:input_text.avaccess_target_rxs, value:RX-01,RX-02}` | 200 | — | helper already `RX-01,RX-02` |
| `POST /api/services/script/avaccess_route_selected_program_to_tvs` `{}` | 200 | 2026-09-18T16:54:23.675Z | nested `avaccess_route_program_to_tvs`; `echo "STAGING avaccess_route_targets"` rc=0 |
| `POST /api/services/script/avaccess_route_program_to_tvs` `{program:program_a, targets:RX-01,RX-02}` | 200 | 2026-09-18T16:54:24.686Z | `echo "STAGING avaccess_route_targets"` rc=0 |

No script traceback. Staging echo is expected (`--ui-staging` stubs).

## Log errors

Sources: `sudo docker logs avaccess-ha-staging --since 10m` and `homeassistant/staging/config/home-assistant.log`.

**Current HA process** (initialized 12:50:11 local / 16:50 UTC): no Invalid config, no recovery mode, no AVAccess traceback.

| Event | Severity | Relevance |
|-------|----------|-----------|
| `STAGING avaccess_preset_1_all` / `STAGING avaccess_directv_tune` / `STAGING avaccess_route_targets` | DEBUG | **Expected** staging echo |
| `Timeout fetching homeassistant_alerts data` | ERROR | Unrelated outbound HA alerts |
| `http.data_validator` missing `client_id` / `redirect_uri` | ERROR | From first onboarding integration probes (then succeeded) |
| `Radio Browser` not ready / toast “Starting radio_browser…” | INFO/UI | Default onboarding integration; overlays dashboard until dismissed. Not AVAccess YAML. |
| Earlier container boots: `unit_system: us` Invalid config; legacy template sensor platform | ERROR | **Fixed before this boot** (see `docs/HA_STAGING_STATUS.md`). Still in `--since 10m` docker history. |

## Dashboard YAML inspection

File: `homeassistant/staging/config/dashboards/avaccess_matrix.yaml` (also live via websocket).

| Requirement | Present? |
|-------------|----------|
| 3 favorite buttons with large names | Yes: FOX Local, NFL Afternoon Games, All NFL Sunday Games |
| 3 preset buttons | Yes: Preset 1 ALL / Preset 2 4 Programs / Preset 3 9 Programs |
| Program A–I | Yes |
| NFL S1–S9 channel labels | S1–S8 = `NFL S1`…`S8`; S9 was `S9 NFL Slot` on this walk, now `NFL S9` in `channels.example.yaml` |
| Sports tabs | NFL (`nfl`), College Football (`cfb`), Basketball (`hoops`) plus Control (`av-control`) |
| Destination card | Yes on every view |
| Route Program -> TVs | Yes → `script.avaccess_route_selected_program_to_tvs` |
| Now Playing uses sensors not media_player | Yes: `sensor.directv_h25_01`–`_09` |

Live UI notes (documented, generators not changed):

1. **S9 label** on this walk was `S9 NFL Slot`; `config/channels.example.yaml` now uses `NFL S9`.
2. Control view is masonry: Destination + Route Actions sit below the fold; S9 wraps alone under the 4-column channel grid.
3. At 768×1024 Control, the right **Route Program -> TVs** button can sit against the viewport edge (still readable). NFL/CFB/Basketball views look cleaner.
4. Favorite names wrap on narrow width; still tappable in Chrome.

## Screenshots

Chrome headless (not iPad Safari), logged in as `operator` via injected `hassTokens`. Saved under `/tmp/ha-a2-screenshots/` and `/opt/cursor/artifacts/screenshots/`.

| Viewport | Tab | Files |
|----------|-----|--------|
| desktop 1280×800 | Control | `desktop-control-top.png`, `desktop-control-bottom.png` |
| desktop 1280×800 | NFL | `desktop-nfl-top.png`, `desktop-nfl-bottom.png` |
| desktop 1280×800 | College Football | `desktop-cfb-top.png`, `desktop-cfb-bottom.png` |
| desktop 1280×800 | Basketball | `desktop-hoops-top.png`, `desktop-hoops-bottom.png` |
| iPad portrait 768×1024 | Control | `ipad-portrait-control-top.png`, `ipad-portrait-control-bottom.png` |
| iPad portrait 768×1024 | NFL | `ipad-portrait-nfl-top.png`, `ipad-portrait-nfl-bottom.png` |
| iPad portrait 768×1024 | College Football | `ipad-portrait-cfb-top.png`, `ipad-portrait-cfb-bottom.png` |
| iPad portrait 768×1024 | Basketball | `ipad-portrait-hoops-top.png`, `ipad-portrait-hoops-bottom.png` |

Sidebar shows **AVAccess Matrix**. No red entity-not-found.

## Remaining iPad Safari caveats

- This pass used **Google Chrome** at 768×1024, not iPad Safari or HA Companion.
- Publish / **port-forward 8123** to a host the iPad can reach (`http://<reachable-host>:8123`). This VM bind is `0.0.0.0:8123`; login `operator` / `avaccess-staging`.
- Safari-only issues not checked: safe-area / notch, 100vh, hover vs tap, Companion app sidebar, cached Lovelace after YAML regen.
- Dismiss the Radio Browser “Starting radio_browser…” toast if it covers Route Actions.
- Do not point this instance at live H25 / AVAccess hardware until a physical iPad walk is done if that gate is still required.

## Verdict

A2 cloud UI staging **PASS** for REST + YAML + Chrome viewports. Scripts fire; STAGING echoes; helpers/sensors present; no missing-entity Lovelace cards. Follow-up on a real iPad after port-forwarding 8123.
