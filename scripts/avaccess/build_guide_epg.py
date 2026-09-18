#!/usr/bin/env python3
"""Build guide_epg.json (now/next) from XMLTV for the bartender Guide panel."""

from __future__ import annotations

import argparse
import datetime as dt
import json
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


def build_guide_epg(cfg: dict[str, Any], now: dt.datetime | None = None) -> dict[str, Any]:
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
    _channels, programs = parse_xmltv(xml_bytes, tz)

    by_channel: dict[str, list[Program]] = {}
    for prog in programs:
        by_channel.setdefault(prog.channel_id, []).append(prog)

    number_map = cfg.get("channel_number_map") or {}
    if not isinstance(number_map, dict):
        raise ValueError("config.channel_number_map must be a mapping")

    out_channels: dict[str, Any] = {}
    for number, xmltv_ids in number_map.items():
        number_s = str(number)
        if isinstance(xmltv_ids, str):
            ids = [xmltv_ids]
        elif isinstance(xmltv_ids, list):
            ids = [str(i) for i in xmltv_ids]
        else:
            raise ValueError(
                f"channel_number_map[{number_s!r}] must be a string or list of ids"
            )
        channel_programs: list[Program] = []
        for ch_id in ids:
            channel_programs.extend(by_channel.get(ch_id, []))
        current, upcoming = _select_now_next(channel_programs, now)
        out_channels[number_s] = {
            "number": number_s,
            "now": _program_payload(current),
            "next": _program_payload(upcoming),
        }

    return {
        "zip": str(cfg.get("zip_code", "")),
        "generatedAt": now.astimezone(dt.timezone.utc).isoformat(),
        "channels": out_channels,
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
        payload = build_guide_epg(cfg)
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
