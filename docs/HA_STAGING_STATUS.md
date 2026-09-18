# Home Assistant staging boot status

Checked: 2026-09-18 (cloud agent VM).

## Result

**Onboarding complete. A2 checklist walked.** Home Assistant 2026.9.3 is running, serving the UI, and is past first-run onboarding.

URL (on this VM): http://127.0.0.1:8123  
Dashboard: http://127.0.0.1:8123/avaccess-matrix/av-control (sidebar **AVAccess Matrix**)

Owner account: **username `operator` / password `avaccess-staging`**.

A2 pass/fail table, script evidence, logs, and screenshots: [`docs/HA_STAGING_A2_CHECKLIST.md`](HA_STAGING_A2_CHECKLIST.md).

## Docker available

**Yes** (installed during the earlier boot check).

| Item | Value |
|------|--------|
| Docker CLI / daemon | 29.1.3 (`docker.io` + `docker-compose-v2` via apt) |
| Compose | 2.40.3 (`docker compose`) |
| Notes | Nested overlayfs cannot use overlay as upperdir. Dockerd uses `storage-driver: vfs`. `docker` CLI needs `sudo`. |

## Container status

**Up** — `avaccess-ha-staging` (`ghcr.io/home-assistant/home-assistant:stable`).

- Port bind: `0.0.0.0:8123->8123/tcp`
- Logs: `Home Assistant initialized in 1.51s` / `Starting Home Assistant 2026.9.3`
- Lovelace YAML dashboard `avaccess-matrix`, scripts, `input_select` / `input_text` helpers, `shell_command` stubs, dummy `sensor.directv_h25_01`–`_09` registered

## HTTP status

| Request | Response |
|---------|----------|
| `GET http://127.0.0.1:8123/` | **200 OK** (`text/html`) after onboarding |
| `GET http://127.0.0.1:8123/lovelace` | **200 OK** |
| `GET http://127.0.0.1:8123/avaccess-matrix/av-control` | **200** (UI) |
| `GET /api/onboarding` | **404** once onboarding finished (all steps were `done:true` immediately before that) |
| `HEAD /` | **405** (HA HTTP allows GET, not HEAD) |

Onboarding was completed via REST (not the HTML wizard): users → `/auth/token` → core_config → analytics → integration (`client_id` + `redirect_uri` required on HA 2026.9). Long-lived token stored in gitignored `homeassistant/staging/config/.a2_auth.json`.

`GET /api/config`: `location_name=AVAccess Staging`, US customary, `currency=USD`, `state=RUNNING`. `time_zone` still reports UTC.

## A2 (this pass)

**PASS** against live HA. Details in [`docs/HA_STAGING_A2_CHECKLIST.md`](HA_STAGING_A2_CHECKLIST.md).

- Helpers: `input_select.avaccess_program`, `input_select.avaccess_channel`, `input_text.avaccess_target_rxs`
- Scripts include favorites, presets 1–3, `script.avaccess_tune_channel`, `script.avaccess_route_program_to_tvs`, `script.avaccess_route_selected_program_to_tvs`
- Dummy sensors `sensor.directv_h25_01`–`_09` state `STAGING - DirecTV not connected` (no `media_player` Now Playing)
- Fired Favorite FOX and Route Program → TVs (`RX-01,RX-02`); logs show `STAGING avaccess_preset_1_all`, `STAGING avaccess_directv_tune`, `STAGING avaccess_route_targets`
- Chrome screenshots at 1280×800 and 768×1024 for Control / NFL / College Football / Basketball

Non-blocking notes: Sunday slot 9 was `S9 NFL Slot` on this walk; example YAML now labels it `NFL S9`. Physical iPad Safari was not used. Onboarding pulled in Radio Browser (toast overlay).

## Log errors

**Current boot (after onboarding): no Invalid config / recovery mode / AVAccess traceback.**

Still seen (not config):

- `Timeout fetching homeassistant_alerts data` (outbound alerts)
- `http.data_validator` missing `client_id` / `redirect_uri` during the first integration POST probes
- Radio Browser “not ready” / UI toast

Fixed during the earlier stand-up (previous boots):

1. `unit_system: us` rejected (`expected 'metric' or 'us_customary' or 'imperial'`). Staging template uses `unit_system: us_customary`.
2. Dummy Now Playing used legacy `sensor: / platform: template`; HA 2026.9 requires the `template:` key. `generate_ha_bundle.py --ui-staging` now emits modern `template:` sensors; `prepare_ha_staging.py` still rewrites leftover legacy blocks.

## Next steps

1. Port-forward **8123** if an iPad is not on this host. Open `http://<reachable-host>:8123`, sign in as `operator` / `avaccess-staging`, sidebar **AVAccess Matrix**.
2. Optional physical iPad Safari / HA Companion walk (safe-area, tap, Companion sidebar) — Chrome 768×1024 already passed the A2 layout checks.
3. Do not point this instance at live AVAccess or H25 boxes until that device pass (if required) is done. Shell commands remain `echo STAGING ...` stubs.

## Files

- `scripts/prepare_ha_staging.py` — `unit_system: us_customary`; post-process generated package template sensors (boot stand-up).
- `docs/HA_STAGING_STATUS.md` — this report.
- `docs/HA_STAGING_A2_CHECKLIST.md` — A2 pass/fail evidence.

Generated runtime config under `homeassistant/staging/config/` is gitignored and was not committed.
