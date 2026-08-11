# Schedules Direct Guide Pull Design

**Status:** Approved / implemented  
**Date:** 2026-08-11  
**Extends:** `2026-08-10-spectrum-lineup-sports-epg-design.md`

## Goal

Pull live Greensboro Spectrum listings from a Schedules Direct account into XMLTV, then reuse the existing `build_guide_epg.py` path for Guide now/next + Sports matching.

## Decisions

| Topic | Choice |
|-------|--------|
| Approach | Native SD JSON API → XMLTV in-repo (Approach A) |
| Credentials | `SD_USERNAME` + `SD_PASSWORD` (or `SD_PASSWORD_SHA1`) via env |
| Config | `config/schedules_direct.yaml` (gitignored); example committed |
| Lineup | Auto-discover Charter Spectrum Cable for ZIP 27403; prefer `USA-NC32529-X` |
| Add lineup | `PUT /lineups/{id}` if not on account |
| Channel SoT | SD lineup map → `spectrum_lineup_27403.json` + panel JS (not tvchannelsguide) |
| EPG attach | Dial **number** from XMLTV display-name (name match only as fallback) |
| Downstream | `build_guide_epg.py` consumes SD XMLTV + SD lineup |

## Operator flow

```bash
export SD_USERNAME=...
export SD_PASSWORD=...
cp config/schedules_direct.example.yaml config/schedules_direct.yaml
python3 scripts/avaccess/pull_schedules_direct.py --config config/schedules_direct.yaml --write-lineup-id
python3 scripts/avaccess/build_guide_epg.py --config config/guide_epg.yaml \
  --out homeassistant/config/www/avaccess/guide_epg.json
```

## Non-goals

- Committing SD credentials or raw XMLTV cache
- Replacing ESPN sports schedule scrape (still optional overlay)
