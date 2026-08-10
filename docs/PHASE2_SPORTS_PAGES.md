# Phase 2: Sports Pages + Daily Updates + Targeted TV Routing

This phase extends the control surface from one generic page into sport-specific pages that update
frequently and can route content to:

1. Preset groups (existing favorites/presets), or  
2. One or many specific TVs (ad-hoc routing).

## Delivered foundations

- Sport pages are generated from `channels.yaml -> sports_pages`
- Dashboard includes per-sport views (NFL, College Football, Basketball examples)
- Added helper: `input_text.avaccess_target_rxs`
- Added scripts:
  - `script.avaccess_route_selected_program_to_tvs`
  - `script.avaccess_route_program_to_tvs`
- Added command backend:
  - `scripts/route_targets.py` (encoder -> specific RX list)

## Daily update strategy

### A) Channel labels/content
- Keep daily/weekly schedule sync running (XMLTV)
- Let sync update NFL slot labels (matchups)
- Regenerate HA bundle after sync

### B) Sport tabs
- Update channel memberships in `sports_pages` as needed
- Regenerate HA bundle to refresh tab contents

## Operator workflow

### Preset path
1. Tap Favorite/Preset (e.g., NFL Afternoon Games)
2. System routes screens + tunes assigned programs

### Ad-hoc TV path
1. Pick sport page and tune/select program  
2. Enter TVs in `input_text.avaccess_target_rxs` (e.g., `RX-01,RX-04,RX-18`)  
3. Tap **Route Program -> TVs**

## Suggested automations

1. **Daily 6:00 AM** — regenerate bundle (sports tabs stay fresh)  
2. **Tuesday 6:00 AM** — weekly NFL schedule sync + bundle regenerate  
3. **Manual override button** — rerun refresh before events
