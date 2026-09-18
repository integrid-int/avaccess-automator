# Home Assistant staging boot status

Checked: 2026-09-18 (cloud agent VM).

## Result

**Boot success.** Home Assistant 2026.9.3 is running and serving the UI.

URL (on this VM): http://127.0.0.1:8123  
Onboarding: http://127.0.0.1:8123/onboarding.html

## Docker available

**Yes** (installed during this check).

| Item | Value |
|------|--------|
| Docker CLI / daemon | 29.1.3 (`docker.io` + `docker-compose-v2` via apt) |
| Compose | 2.40.3 (`docker compose`) |
| Notes | Daemon was not present at start. Nested overlayfs cannot use the default overlay storage driver (`overlay: filesystem ... not supported as upperdir`). Dockerd was started with `storage-driver: vfs`. |

## Container status

**Up** — `avaccess-ha-staging` (`ghcr.io/home-assistant/home-assistant:stable`).

- Port bind: `0.0.0.0:8123->8123/tcp`
- After config fixes, logs show: `Home Assistant initialized in 1.51s` / `Starting Home Assistant 2026.9.3`
- Lovelace, scripts, `input_select`, `shell_command`, and dummy `sensor.directv_h25_0{1-9}` entities registered

## HTTP status

| Request | Response |
|---------|----------|
| `HEAD http://127.0.0.1:8123` | **405 Method Not Allowed** (HA HTTP allows GET, not HEAD; server is up) |
| `GET http://127.0.0.1:8123/` | **302** → `/onboarding.html` |
| `GET http://127.0.0.1:8123/onboarding.html` | **200 OK** (`text/html`) |

Onboarding is not finished (expected for a fresh staging instance).

## Log errors

**Current boot: none.** After the staging config fixes below, `docker logs --since` for the latest start had no `ERROR` / `Invalid config` / recovery-mode lines.

Fixed during this stand-up (earlier boots):

1. `unit_system: us` rejected (`expected 'metric' or 'us_customary' or 'imperial'`). HA entered recovery mode. Staging template now uses `unit_system: us_customary`.
2. Dummy Now Playing entities used legacy `sensor: / platform: template`, which HA 2026.9 rejects (`must be configured under its own template key`). `prepare_ha_staging.py` now rewrites those to modern `template:` sensors so `sensor.directv_h25_*` still load.

Unrelated noise on an earlier boot (not present after restart): `Timeout fetching homeassistant_alerts data` (outbound alerts, not config). `HEAD` 405 is protocol, not a crash.

## Next manual iPad steps

1. Open **http://\<reachable-host\>:8123** in Safari (or HA Companion). On this VM that is `http://127.0.0.1:8123`; publish/port-forward 8123 if the iPad is not on the same host.
2. Complete first-run onboarding (create the owner account). YAML dashboards are already enabled.
3. Open the sidebar dashboard **AVAccess Matrix**.
4. Walk the UI checklist in `docs/DIRECTV_H25_PATCH_AND_TEST_PLAN.md` section A2 (desktop **and** iPad): Control tab helpers, favorite/preset tap targets, sports tabs, Now Playing dummy sensors (`STAGING - DirecTV not connected`), no red missing-entity cards.
5. Tap presets / favorites / route buttons. Shell commands are `echo STAGING ...` stubs; taps should not fail for missing hardware.
6. Do not point this instance at live AVAccess or H25 boxes until that checklist passes.

## Files changed for boot

- `scripts/prepare_ha_staging.py` — `unit_system: us_customary`; post-process generated package template sensors.
- `docs/HA_STAGING_STATUS.md` — this report.

Generated runtime config under `homeassistant/staging/config/` is gitignored and was not committed.
