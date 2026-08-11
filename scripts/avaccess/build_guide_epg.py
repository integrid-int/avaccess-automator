#!/usr/bin/env python3
"""Build guide_epg.json (now/next) from XMLTV for the bartender Guide panel."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.avaccess.xmltv_lib import Program, fetch_xmltv_bytes, parse_xmltv

DEFAULT_CONFIG = ROOT / "config" / "guide_epg.yaml"
DEFAULT_OUT = ROOT / "homeassistant" / "config" / "www" / "avaccess" / "guide_epg.json"

_NFL_RE = re.compile(
    r"\bnfl\b|sunday night football|monday night football|thursday night football",
    re.I,
)
_CFB_RE = re.compile(r"college football|\bncaa football\b", re.I)
_NBA_RE = re.compile(r"\bnba\b", re.I)
_NHL_RE = re.compile(r"\bnhl\b", re.I)
_MLB_RE = re.compile(r"\bmlb\b|major league baseball", re.I)
_WNBA_RE = re.compile(r"\bwnba\b", re.I)
_NON_ALNUM_RE = re.compile(r"[^a-z0-9]+")


def classify_sport_key(title: str) -> str:
    """Map an EPG/schedule title to a Sports tab key."""
    text = str(title or "")
    if _NFL_RE.search(text):
        return "nfl"
    if _CFB_RE.search(text):
        return "cfb"
    if _WNBA_RE.search(text):
        return "wnba"
    if _NBA_RE.search(text):
        return "nba"
    if _NHL_RE.search(text):
        return "nhl"
    if _MLB_RE.search(text):
        return "mlb"
    return "other"


def normalize_channel_name(name: str) -> str:
    """Normalize channel labels for XMLTV ↔ Spectrum matching."""
    text = str(name or "").lower().strip()
    text = text.replace("&", " and ")
    text = _NON_ALNUM_RE.sub("", text)
    for prefix in ("the", "hd", "uhd", "east", "west"):
        if text.startswith(prefix) and len(text) > len(prefix) + 2:
            # strip trailing east/west variants only when whole-token style
            pass
    for suffix in ("hd", "uhd", "dtv", "tv"):
        if text.endswith(suffix) and len(text) > len(suffix) + 2:
            text = text[: -len(suffix)]
    return text


def map_xmltv_ids_by_number(
    xmltv_channels: dict[str, list[str]],
) -> dict[str, list[str]]:
    """Map Spectrum dial number → XMLTV id(s) from digit-only display-names."""
    number_to_ids: dict[str, list[str]] = {}
    for xml_id, names in xmltv_channels.items():
        for name in names:
            text = str(name or "").strip()
            if not re.fullmatch(r"\d+", text):
                continue
            number_s = str(int(text))
            number_to_ids.setdefault(number_s, []).append(xml_id)
    resolved: dict[str, list[str]] = {}
    for number_s, ids in number_to_ids.items():
        unique = sorted(set(ids))
        if len(unique) == 1:
            resolved[number_s] = unique
    return resolved


def auto_map_xmltv_ids(
    lineup_channels: list[dict[str, Any]],
    xmltv_channels: dict[str, list[str]],
    explicit_map: dict[str, Any],
) -> dict[str, list[str]]:
    """Resolve lineup numbers → XMLTV ids.

    Priority when Schedules Direct is source of truth:
    1) explicit channel_number_map
    2) dial number on XMLTV display-name (SD SoT)
    3) unique normalized name match (legacy fallback)
    """
    name_to_ids: dict[str, list[str]] = {}
    for xml_id, names in xmltv_channels.items():
        for name in names:
            key = normalize_channel_name(name)
            if not key:
                continue
            name_to_ids.setdefault(key, []).append(xml_id)

    by_number = map_xmltv_ids_by_number(xmltv_channels)

    resolved: dict[str, list[str]] = {}
    for number, xmltv_ids in explicit_map.items():
        number_s = str(number)
        if isinstance(xmltv_ids, str):
            ids = [xmltv_ids] if xmltv_ids else []
        elif isinstance(xmltv_ids, list):
            ids = [str(i) for i in xmltv_ids if str(i).strip()]
        else:
            raise ValueError(
                f"channel_number_map[{number_s!r}] must be a string or list of ids"
            )
        if ids:
            resolved[number_s] = ids

    for ch in lineup_channels:
        number_s = str(ch.get("number", "")).strip()
        if not number_s or number_s in resolved:
            continue
        if number_s in by_number:
            resolved[number_s] = by_number[number_s]
            continue
        key = normalize_channel_name(str(ch.get("name") or ""))
        matches = name_to_ids.get(key) or []
        unique = sorted(set(matches))
        if len(unique) == 1:
            resolved[number_s] = unique
        else:
            resolved.setdefault(number_s, [])

    # If lineup is empty, still emit every numbered XMLTV channel.
    if not lineup_channels:
        for number_s, ids in by_number.items():
            resolved.setdefault(number_s, ids)
    return resolved


def _iso(moment: dt.datetime | None) -> str | None:
    if moment is None:
        return None
    return moment.isoformat()


def _program_payload(program: Program | None) -> dict[str, Any] | None:
    if program is None:
        return None
    return {
        "title": program.title,
        "start": _iso(program.start),
        "stop": _iso(program.stop),
    }


def _is_airing(program: Program, now: dt.datetime) -> bool:
    if program.start > now:
        return False
    if program.stop is None:
        return True
    return now < program.stop


def _select_now_next(
    programs: list[Program], now: dt.datetime
) -> tuple[Program | None, Program | None]:
    """Pick now/next for one channel at ``now``.

    now = programme where start <= now < stop (stop null → ongoing if start <= now)
    next = earliest programme with start >= now after current
           (if now occupies, first start >= now.stop or >= now)
    """
    ordered = sorted(programs, key=lambda p: p.start)
    current = next((p for p in ordered if _is_airing(p, now)), None)
    if current is not None and current.stop is not None:
        next_floor = current.stop
    else:
        next_floor = now
    upcoming = next((p for p in ordered if p.start >= next_floor and p is not current), None)
    # If stop is null and we treated current as ongoing, still allow a later start >= now
    if current is not None and current.stop is None and upcoming is None:
        upcoming = next((p for p in ordered if p.start >= now and p is not current), None)
    return current, upcoming


def _resolve_path(raw: str | Path, config_path: Path | None = None) -> Path:
    path = Path(str(raw))
    if path.is_absolute():
        return path
    candidates = [ROOT / path]
    if config_path is not None:
        candidates.insert(0, config_path.parent / path)
    return next((p for p in candidates if p.is_file()), candidates[0])


def _load_lineup_channels(
    cfg: dict[str, Any], config_path: Path | None = None
) -> list[dict[str, Any]]:
    lineup_path = cfg.get("lineup_file")
    if not lineup_path:
        return []
    path = _resolve_path(lineup_path, config_path)
    data = json.loads(path.read_text(encoding="utf-8"))
    return list(data.get("channels") or [])


def _load_lineup_sports(
    cfg: dict[str, Any], config_path: Path | None = None
) -> dict[str, str]:
    """Return channelNumber → name for sports-category lineup rows."""
    explicit = cfg.get("sports_channel_numbers")
    names: dict[str, str] = {}
    for ch in _load_lineup_channels(cfg, config_path=config_path):
        if str(ch.get("category", "")).lower() != "sports":
            continue
        number = str(ch.get("number", "")).strip()
        if not number:
            continue
        names[number] = str(ch.get("name") or number)
    if isinstance(explicit, list) and explicit:
        allowed = [str(n) for n in explicit]
        names = {n: names.get(n, n) for n in allowed}
    return names


def _load_sports_schedule(
    cfg: dict[str, Any], config_path: Path | None = None
) -> list[dict[str, Any]]:
    raw = cfg.get("sports_schedule_file")
    if not raw:
        return []
    path = _resolve_path(raw, config_path)
    if not path.is_file():
        return []
    data = json.loads(path.read_text(encoding="utf-8"))
    games = data.get("games") if isinstance(data, dict) else data
    return list(games or [])


def match_schedule_to_epg(
    schedule_games: list[dict[str, Any]],
    sports_block: dict[str, Any],
) -> list[dict[str, Any]]:
    """Attach EPG channel numbers to scraped games when titles overlap."""
    epg_items = list(sports_block.get("now") or []) + list(
        sports_block.get("upcoming") or []
    )
    matched: list[dict[str, Any]] = []
    for game in schedule_games:
        away = str(game.get("away") or "").strip()
        home = str(game.get("home") or "").strip()
        title = str(game.get("title") or f"{away} at {home}").strip()
        sport_key = str(game.get("sportKey") or classify_sport_key(title))
        hit = None
        for item in epg_items:
            epg_title = str(item.get("title") or "")
            epg_l = epg_title.lower()
            if away and home and away.lower() in epg_l and home.lower() in epg_l:
                hit = item
                break
            # Short team nickname tokens (last word) as fallback.
            away_tok = away.split()[-1].lower() if away else ""
            home_tok = home.split()[-1].lower() if home else ""
            if (
                away_tok
                and home_tok
                and len(away_tok) > 3
                and len(home_tok) > 3
                and away_tok in epg_l
                and home_tok in epg_l
            ):
                hit = item
                break
        row = {
            "id": str(game.get("id") or f"sched-{sport_key}-{away}-{home}"),
            "channelNumber": hit.get("channelNumber") if hit else None,
            "channelName": hit.get("channelName") if hit else None,
            "title": title,
            "away": away,
            "home": home,
            "start": game.get("start") or (hit.get("start") if hit else None),
            "end": game.get("end") or (hit.get("end") if hit else None),
            "sportKey": sport_key,
            "matched": bool(hit),
            "source": "schedule",
        }
        matched.append(row)
    return matched


def _sport_item(*, number: str, name: str, program: Program) -> dict[str, Any]:
    start_iso = _iso(program.start) or ""
    return {
        "id": f"sport-{number}-{start_iso}",
        "channelNumber": number,
        "channelName": name,
        "title": program.title,
        "start": _iso(program.start),
        "end": _iso(program.stop),
        "sportKey": classify_sport_key(program.title),
    }


def build_sports_block(
    *,
    channel_programs: dict[str, list[Program]],
    sports_names: dict[str, str],
    now: dt.datetime,
    window_hours: int,
) -> dict[str, Any]:
    """Build Now + Upcoming sports lists (no duplicates)."""
    window_end = now + dt.timedelta(hours=window_hours)
    now_items: list[dict[str, Any]] = []
    upcoming_items: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    def sort_key(number: str) -> tuple[int, str]:
        return (int(number), number) if number.isdigit() else (10**9, number)

    for number, name in sorted(sports_names.items(), key=lambda kv: sort_key(kv[0])):
        programs = sorted(channel_programs.get(number, []), key=lambda p: p.start)
        for program in programs:
            item = _sport_item(number=number, name=name, program=program)
            if item["id"] in seen_ids:
                continue
            if _is_airing(program, now):
                now_items.append(item)
                seen_ids.add(item["id"])
                continue
            if now < program.start <= window_end:
                upcoming_items.append(item)
                seen_ids.add(item["id"])

    now_items.sort(key=lambda i: i.get("start") or "")
    upcoming_items.sort(key=lambda i: i.get("start") or "")
    return {
        "windowHours": window_hours,
        "now": now_items,
        "upcoming": upcoming_items,
    }


def build_guide_epg(
    cfg: dict[str, Any],
    now: dt.datetime | None = None,
    *,
    config_path: Path | None = None,
) -> dict[str, Any]:
    """Build guide EPG JSON from config mapping Spectrum numbers → XMLTV ids."""
    tz_name = str(cfg.get("timezone") or "UTC")
    tz = ZoneInfo(tz_name)
    if now is None:
        now = dt.datetime.now(tz=dt.timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=tz)
    else:
        now = now.astimezone(dt.timezone.utc)

    source = cfg.get("source")
    if not isinstance(source, dict):
        raise ValueError("config.source must be a mapping with file or url")

    xml_bytes = fetch_xmltv_bytes(source)
    xmltv_channels, programs = parse_xmltv(xml_bytes, tz)

    by_channel: dict[str, list[Program]] = {}
    for prog in programs:
        by_channel.setdefault(prog.channel_id, []).append(prog)

    number_map = cfg.get("channel_number_map") or {}
    if not isinstance(number_map, dict):
        raise ValueError("config.channel_number_map must be a mapping")

    lineup_channels = _load_lineup_channels(cfg, config_path=config_path)
    resolved_map = auto_map_xmltv_ids(lineup_channels, xmltv_channels, number_map)
    # Keep explicit-only numbers even when lineup_file is absent.
    for number, xmltv_ids in number_map.items():
        number_s = str(number)
        if number_s not in resolved_map:
            if isinstance(xmltv_ids, str):
                resolved_map[number_s] = [xmltv_ids] if xmltv_ids else []
            elif isinstance(xmltv_ids, list):
                resolved_map[number_s] = [str(i) for i in xmltv_ids if str(i).strip()]

    # Ensure every lineup channel appears in the EPG payload (null now/next if unmapped).
    for ch in lineup_channels:
        number_s = str(ch.get("number", "")).strip()
        if number_s:
            resolved_map.setdefault(number_s, [])

    out_channels: dict[str, Any] = {}
    programs_by_number: dict[str, list[Program]] = {}
    for number_s, ids in resolved_map.items():
        channel_programs: list[Program] = []
        for ch_id in ids:
            channel_programs.extend(by_channel.get(ch_id, []))
        programs_by_number[number_s] = channel_programs
        current, upcoming = _select_now_next(channel_programs, now)
        out_channels[number_s] = {
            "number": number_s,
            "now": _program_payload(current),
            "next": _program_payload(upcoming),
        }

    sports_names = _load_lineup_sports(cfg, config_path=config_path)
    window_hours = int(cfg.get("sports_window_hours") or 12)
    sports = build_sports_block(
        channel_programs=programs_by_number,
        sports_names=sports_names,
        now=now,
        window_hours=window_hours,
    )
    schedule_games = _load_sports_schedule(cfg, config_path=config_path)
    if schedule_games:
        sports["schedule"] = match_schedule_to_epg(schedule_games, sports)

    return {
        "zip": str(cfg.get("zip_code", "")),
        "generatedAt": now.astimezone(dt.timezone.utc).isoformat(),
        "channels": out_channels,
        "sports": sports,
        "mappedChannelCount": sum(1 for ids in resolved_map.values() if ids),
    }


def load_config(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise ValueError(f"Expected YAML mapping in {path}")
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG,
        help="Guide EPG YAML config (default: config/guide_epg.yaml)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=DEFAULT_OUT,
        help="Output JSON path (default: homeassistant/config/www/avaccess/guide_epg.json)",
    )
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        payload = build_guide_epg(cfg, config_path=args.config.resolve())
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(
            json.dumps(payload, indent=2, sort_keys=False) + "\n",
            encoding="utf-8",
        )
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"build_guide_epg failed: {exc}", file=sys.stderr)
        return 1
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
