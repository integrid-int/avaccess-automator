#!/usr/bin/env python3
"""Sync weekly NFL channel slots from XMLTV into channels.yaml.

This script updates these keys in channels config:
  - nfl_afternoon_game_1..4
  - nfl_sunday_game_1..9

Blackout-aware behavior:
- When the same game appears on both Sunday Ticket and a local affiliate,
  the selector can prefer local channels first (useful for ZIP 27403 and
  other markets with blackout rules).
"""

from __future__ import annotations

import argparse
import datetime as dt
import gzip
import io
import re
import urllib.request
import xml.etree.ElementTree as et
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import yaml


@dataclass
class Program:
    channel_id: str
    start: dt.datetime
    stop: dt.datetime | None
    title: str
    subtitle: str
    desc: str
    categories: list[str]


@dataclass
class Candidate:
    game_id: str
    start: dt.datetime
    channel_number: str
    channel_class: str
    channel_id: str
    channel_names: list[str]
    title: str
    subtitle: str


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def save_yaml(path: Path, data: dict[str, Any]) -> None:
    text = yaml.safe_dump(data, sort_keys=False, width=120, allow_unicode=False)
    path.write_text(text)


def fetch_xmltv_bytes(source_cfg: dict[str, Any]) -> bytes:
    if "file" in source_cfg:
        raw = Path(source_cfg["file"]).read_bytes()
    elif "url" in source_cfg:
        with urllib.request.urlopen(source_cfg["url"], timeout=30) as resp:
            raw = resp.read()
    else:
        raise SystemExit("sync config source must include 'file' or 'url'")

    compression = str(source_cfg.get("compression", "auto")).lower()
    if compression == "none":
        return raw
    if compression == "gzip":
        return gzip.decompress(raw)
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    return raw


def parse_xmltv_time(raw: str, default_tz: ZoneInfo) -> dt.datetime:
    # XMLTV commonly uses: YYYYmmddHHMMSS +/-ZZZZ
    raw = raw.strip()
    m = re.match(r"^(\d{14})(?:\s+([+-]\d{4}))?$", raw)
    if not m:
        raise ValueError(f"Unsupported XMLTV datetime: {raw}")
    base = m.group(1)
    offset = m.group(2)
    if offset:
        return dt.datetime.strptime(f"{base} {offset}", "%Y%m%d%H%M%S %z")
    naive = dt.datetime.strptime(base, "%Y%m%d%H%M%S")
    return naive.replace(tzinfo=default_tz)


def parse_xmltv(xml_bytes: bytes, tz: ZoneInfo) -> tuple[dict[str, list[str]], list[Program]]:
    root = et.parse(io.BytesIO(xml_bytes)).getroot()
    channels: dict[str, list[str]] = {}
    for ch in root.findall("channel"):
        ch_id = ch.attrib.get("id", "").strip()
        if not ch_id:
            continue
        names = [n.text.strip() for n in ch.findall("display-name") if n.text and n.text.strip()]
        channels[ch_id] = names

    progs: list[Program] = []
    for p in root.findall("programme"):
        ch_id = p.attrib.get("channel", "").strip()
        start_raw = p.attrib.get("start", "").strip()
        stop_raw = p.attrib.get("stop", "").strip()
        if not ch_id or not start_raw:
            continue
        try:
            start = parse_xmltv_time(start_raw, tz)
            stop = parse_xmltv_time(stop_raw, tz) if stop_raw else None
        except ValueError:
            continue
        title = (p.findtext("title") or "").strip()
        subtitle = (p.findtext("sub-title") or "").strip()
        desc = (p.findtext("desc") or "").strip()
        categories = [c.text.strip() for c in p.findall("category") if c.text and c.text.strip()]
        progs.append(
            Program(
                channel_id=ch_id,
                start=start,
                stop=stop,
                title=title,
                subtitle=subtitle,
                desc=desc,
                categories=categories,
            )
        )
    return channels, progs


def next_sunday_date(now_local: dt.datetime, week_offset: int, include_today_if_sunday: bool) -> dt.date:
    # Monday=0, Sunday=6
    days = (6 - now_local.weekday()) % 7
    if days == 0 and not include_today_if_sunday:
        days = 7
    days += max(0, week_offset) * 7
    return (now_local + dt.timedelta(days=days)).date()


def parse_hhmm(value: str) -> dt.time:
    return dt.datetime.strptime(value, "%H:%M").time()


def in_window(moment: dt.datetime, day: dt.date, start_t: dt.time, end_t: dt.time, tz: ZoneInfo) -> bool:
    start_dt = dt.datetime.combine(day, start_t, tz)
    end_dt = dt.datetime.combine(day, end_t, tz)
    return start_dt <= moment.astimezone(tz) <= end_dt


def norm_text(value: str) -> str:
    return re.sub(r"\s+", " ", value.strip().lower())


def looks_like_nfl(program: Program, keywords: list[str]) -> bool:
    blob = " ".join(
        [
            program.title,
            program.subtitle,
            program.desc,
            " ".join(program.categories),
        ]
    ).lower()
    return any(k.lower() in blob for k in keywords)


def map_channel_number(channel_id: str, channel_names: list[str], map_cfg: dict[str, Any]) -> str | None:
    by_id = map_cfg.get("by_channel_id", {})
    if channel_id in by_id:
        return str(by_id[channel_id])

    by_name = map_cfg.get("by_display_name", {})
    for name in channel_names:
        if name in by_name:
            return str(by_name[name])
        n = norm_text(name)
        for key, val in by_name.items():
            if norm_text(key) == n:
                return str(val)
    return None


def _to_norm_set(values: list[str]) -> set[str]:
    return {norm_text(v) for v in values if str(v).strip()}


def _to_str_set(values: list[Any]) -> set[str]:
    return {str(v).strip() for v in values if str(v).strip()}


def build_channel_classification(sync_cfg: dict[str, Any]) -> dict[str, dict[str, set[str]]]:
    raw = sync_cfg.get("channel_classification", {})
    if not isinstance(raw, dict):
        return {}

    out: dict[str, dict[str, set[str]]] = {}
    for class_name, rules in raw.items():
        if not isinstance(rules, dict):
            continue
        out[class_name] = {
            "by_channel_id": _to_str_set(rules.get("by_channel_id", [])),
            "by_display_name": _to_norm_set(rules.get("by_display_name", [])),
            "by_display_name_contains": _to_norm_set(rules.get("by_display_name_contains", [])),
            "by_numbers": _to_str_set(rules.get("by_numbers", [])),
        }

    zip_code = str(sync_cfg.get("zip_code", "")).strip()
    market_profiles = sync_cfg.get("market_profiles", {})
    if zip_code and isinstance(market_profiles, dict):
        market = market_profiles.get(zip_code)
        if isinstance(market, dict):
            local = out.setdefault(
                "local",
                {
                    "by_channel_id": set(),
                    "by_display_name": set(),
                    "by_display_name_contains": set(),
                    "by_numbers": set(),
                },
            )
            local["by_display_name_contains"].update(
                _to_norm_set(market.get("local_display_name_contains", []))
            )
            local["by_display_name"].update(_to_norm_set(market.get("local_display_name", [])))
            local["by_channel_id"].update(_to_str_set(market.get("local_channel_ids", [])))
            local["by_numbers"].update(_to_str_set(market.get("local_channel_numbers", [])))
    return out


def _matches_channel_rule(
    channel_id: str, channel_names: list[str], channel_number: str, rule: dict[str, set[str]]
) -> bool:
    if channel_id in rule["by_channel_id"]:
        return True
    if channel_number in rule["by_numbers"]:
        return True

    names_norm = [norm_text(n) for n in channel_names]
    for n in names_norm:
        if n in rule["by_display_name"]:
            return True
        for frag in rule["by_display_name_contains"]:
            if frag and frag in n:
                return True
    return False


def classify_channel(
    channel_id: str,
    channel_names: list[str],
    channel_number: str,
    class_rules: dict[str, dict[str, set[str]]],
) -> str:
    for class_name, rule in class_rules.items():
        if _matches_channel_rule(channel_id, channel_names, channel_number, rule):
            return class_name
    return "other"


def _clean_team_fragment(text: str, from_left: bool) -> str:
    words = [w for w in re.split(r"\s+", norm_text(text)) if w]
    if from_left:
        words = words[-4:]
    else:
        words = words[:4]
    # Remove generic broadcast words that can bleed into title parsing.
    stop = {
        "nfl",
        "football",
        "sunday",
        "ticket",
        "game",
        "live",
        "sports",
        "network",
    }
    words = [w for w in words if w not in stop]
    return " ".join(words).strip()


def parse_teams(text: str) -> str | None:
    s = re.sub(r"[\(\)\[\],:;]", " ", text)
    s = re.sub(r"\s+", " ", s).strip()
    if not s:
        return None
    lower = s.lower()
    separators = [" at ", " vs. ", " vs ", " @ "]
    for sep in separators:
        idx = lower.find(sep)
        if idx < 0:
            continue
        left = _clean_team_fragment(s[:idx], from_left=True)
        right = _clean_team_fragment(s[idx + len(sep) :], from_left=False)
        if left and right:
            return f"{left}_vs_{right}"
    return None


def kickoff_bucket(moment: dt.datetime) -> str:
    minute = (moment.minute // 15) * 15
    bucket = moment.replace(minute=minute, second=0, microsecond=0)
    return bucket.strftime("%Y%m%d%H%M")


def derive_game_id(program: Program, start_local: dt.datetime) -> str:
    # Prefer subtitle first because many feeds keep matchup there cleanly.
    for source in (program.subtitle, program.title, program.desc, f"{program.title} {program.subtitle}"):
        teams = parse_teams(source)
        if teams:
            return f"{kickoff_bucket(start_local)}|{teams}"
    return f"{kickoff_bucket(start_local)}|{norm_text(program.title)}|{norm_text(program.subtitle)}"


def dedupe_keep_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        out.append(item)
    return out


def choose_best_candidate(
    candidates: list[Candidate],
    class_priority: dict[str, int],
    prefer_local_for_blackout: bool,
) -> Candidate:
    def key(c: Candidate) -> tuple[int, str]:
        base_priority = class_priority.get(c.channel_class, class_priority.get("other", 999))
        # Optional nudge: always push local above same-time alternates.
        if prefer_local_for_blackout and c.channel_class == "local":
            base_priority = min(base_priority, -1)
        return (base_priority, c.channel_number)

    return sorted(candidates, key=key)[0]


def pick_channels_for_window(
    channels_meta: dict[str, list[str]],
    programmes: list[Program],
    tz: ZoneInfo,
    sunday: dt.date,
    keywords: list[str],
    map_cfg: dict[str, Any],
    class_rules: dict[str, dict[str, set[str]]],
    class_priority: dict[str, int],
    window: tuple[dt.time, dt.time],
    prefer_local_for_blackout: bool,
) -> tuple[list[str], list[Candidate]]:
    candidates: list[Candidate] = []

    for prog in programmes:
        start_local = prog.start.astimezone(tz)
        if start_local.date() != sunday:
            continue
        if not looks_like_nfl(prog, keywords):
            continue
        if not in_window(start_local, sunday, window[0], window[1], tz):
            continue

        ch_names = channels_meta.get(prog.channel_id, [])
        ch_number = map_channel_number(prog.channel_id, ch_names, map_cfg)
        if not ch_number:
            continue
        ch_class = classify_channel(prog.channel_id, ch_names, ch_number, class_rules)
        game_id = derive_game_id(prog, start_local)
        candidates.append(
            Candidate(
                game_id=game_id,
                start=start_local,
                channel_number=ch_number,
                channel_class=ch_class,
                channel_id=prog.channel_id,
                channel_names=ch_names,
                title=prog.title,
                subtitle=prog.subtitle,
            )
        )

    grouped: dict[str, list[Candidate]] = {}
    for c in candidates:
        grouped.setdefault(c.game_id, []).append(c)

    selected: list[Candidate] = []
    for game_id in sorted(grouped.keys()):
        _ = game_id
        selected.append(
            choose_best_candidate(
                grouped[game_id],
                class_priority=class_priority,
                prefer_local_for_blackout=prefer_local_for_blackout,
            )
        )

    selected_sorted = sorted(
        selected,
        key=lambda c: (
            c.start,
            class_priority.get(c.channel_class, class_priority.get("other", 999)),
            c.channel_number,
        ),
    )
    numbers = dedupe_keep_order([c.channel_number for c in selected_sorted])
    return numbers, selected_sorted


def ensure_channel_entry(channels_cfg: dict[str, Any], key: str, default_label: str) -> dict[str, Any]:
    channels_map = channels_cfg.setdefault("channels", {})
    entry = channels_map.get(key)
    if not isinstance(entry, dict):
        entry = {"number": "", "label": default_label}
        channels_map[key] = entry
    entry.setdefault("label", default_label)
    entry.setdefault("number", "")
    return entry


def apply_slots(
    channels_cfg: dict[str, Any],
    prefix: str,
    count: int,
    picked_numbers: list[str],
    fallback_numbers: list[str],
    label_prefix: str,
    picked_labels: list[str] | None = None,
    fallback_labels: list[str] | None = None,
) -> list[tuple[str, str, str]]:
    changes: list[tuple[str, str, str]] = []
    values = picked_numbers + fallback_numbers
    values = values[:count]
    label_values = (picked_labels or []) + (fallback_labels or [])
    label_values = label_values[:count]
    while len(values) < count:
        values.append("")
    while len(label_values) < count:
        label_values.append("")
    for idx in range(1, count + 1):
        key = f"{prefix}_{idx}"
        entry = ensure_channel_entry(channels_cfg, key, f"{label_prefix} {idx}")
        old = str(entry.get("number", ""))
        new = str(values[idx - 1])
        entry["number"] = new
        new_label = str(label_values[idx - 1]).strip()
        if new_label:
            entry["label"] = new_label
        if old != new:
            changes.append((key, old, new))
    return changes


def _compact_matchup_text(title: str, subtitle: str) -> str:
    cand = subtitle.strip() or title.strip()
    if not cand:
        return "NFL Game"
    cand = re.sub(r"\s+", " ", cand)
    if len(cand) > 34:
        cand = cand[:31].rstrip() + "..."
    return cand


def candidate_label(candidate: Candidate, slot_prefix: str, slot_index: int) -> str:
    class_short = "LCL" if candidate.channel_class == "local" else "ST"
    game = _compact_matchup_text(candidate.title, candidate.subtitle)
    return f"{slot_prefix}{slot_index} {game} ({class_short} {candidate.channel_number})"


def build_class_priority(sync_cfg: dict[str, Any]) -> dict[str, int]:
    order = sync_cfg.get("channel_class_priority", ["local", "nfl_ticket", "other"])
    if not isinstance(order, list) or not order:
        order = ["local", "nfl_ticket", "other"]
    out: dict[str, int] = {}
    for idx, name in enumerate(order):
        out[str(name)] = idx
    if "other" not in out:
        out["other"] = len(out)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", type=Path, required=True)
    parser.add_argument("--sync-config", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    channels_cfg = load_yaml(args.channels)
    sync_cfg = load_yaml(args.sync_config)

    tz_name = sync_cfg.get("timezone", "America/New_York")
    tz = ZoneInfo(tz_name)
    week_offset = int(sync_cfg.get("target_week_offset", 0))
    include_today_if_sunday = bool(sync_cfg.get("include_today_if_sunday", False))
    now_local = dt.datetime.now(tz)
    sunday = next_sunday_date(now_local, week_offset, include_today_if_sunday)

    source_cfg = sync_cfg.get("source", {})
    if not isinstance(source_cfg, dict):
        raise SystemExit("sync config 'source' must be a mapping")
    xml_bytes = fetch_xmltv_bytes(source_cfg)
    channels_meta, programmes = parse_xmltv(xml_bytes, tz=tz)

    keywords = sync_cfg.get("nfl_keywords", ["nfl", "football"])
    if not isinstance(keywords, list) or not keywords:
        raise SystemExit("nfl_keywords must be a non-empty list")

    aw = sync_cfg.get("afternoon_window", {"start": "13:00", "end": "19:00"})
    sw = sync_cfg.get("sunday_window", {"start": "09:00", "end": "23:59"})
    afternoon_window = (parse_hhmm(aw["start"]), parse_hhmm(aw["end"]))
    sunday_window = (parse_hhmm(sw["start"]), parse_hhmm(sw["end"]))

    map_cfg = sync_cfg.get("channel_number_map", {})
    if not isinstance(map_cfg, dict):
        raise SystemExit("channel_number_map must be a mapping")

    class_rules = build_channel_classification(sync_cfg)
    class_priority = build_class_priority(sync_cfg)
    prefer_local_for_blackout = bool(sync_cfg.get("prefer_local_for_blackout", True))

    afternoon_numbers, afternoon_selected = pick_channels_for_window(
        channels_meta=channels_meta,
        programmes=programmes,
        tz=tz,
        sunday=sunday,
        keywords=keywords,
        map_cfg=map_cfg,
        class_rules=class_rules,
        class_priority=class_priority,
        window=afternoon_window,
        prefer_local_for_blackout=prefer_local_for_blackout,
    )
    sunday_numbers, sunday_selected = pick_channels_for_window(
        channels_meta=channels_meta,
        programmes=programmes,
        tz=tz,
        sunday=sunday,
        keywords=keywords,
        map_cfg=map_cfg,
        class_rules=class_rules,
        class_priority=class_priority,
        window=sunday_window,
        prefer_local_for_blackout=prefer_local_for_blackout,
    )

    fallback_afternoon = [str(v) for v in sync_cfg.get("fallback_afternoon_numbers", [])]
    fallback_sunday = [str(v) for v in sync_cfg.get("fallback_sunday_numbers", [])]
    fallback_afternoon_labels = [f"NFL A{i} (Fallback {n})" for i, n in enumerate(fallback_afternoon, 1)]
    fallback_sunday_labels = [f"NFL S{i} (Fallback {n})" for i, n in enumerate(fallback_sunday, 1)]
    afternoon_labels = [candidate_label(c, "A", i) for i, c in enumerate(afternoon_selected, 1)]
    sunday_labels = [candidate_label(c, "S", i) for i, c in enumerate(sunday_selected, 1)]

    changes: list[tuple[str, str, str]] = []
    changes.extend(
        apply_slots(
            channels_cfg=channels_cfg,
            prefix="nfl_afternoon_game",
            count=4,
            picked_numbers=afternoon_numbers,
            fallback_numbers=fallback_afternoon,
            label_prefix="NFL A",
            picked_labels=afternoon_labels,
            fallback_labels=fallback_afternoon_labels,
        )
    )
    changes.extend(
        apply_slots(
            channels_cfg=channels_cfg,
            prefix="nfl_sunday_game",
            count=9,
            picked_numbers=sunday_numbers,
            fallback_numbers=fallback_sunday,
            label_prefix="NFL S",
            picked_labels=sunday_labels,
            fallback_labels=fallback_sunday_labels,
        )
    )

    print(f"Target Sunday: {sunday.isoformat()} ({tz_name})")
    print(f"Found candidate afternoon channels: {afternoon_numbers}")
    print(f"Found candidate sunday channels: {sunday_numbers}")
    print("Selected afternoon games:")
    for c in afternoon_selected:
        print(
            f"  {c.start.strftime('%H:%M')} {c.channel_number} ({c.channel_class}) "
            f"{c.title} | {c.subtitle}"
        )
    print("Selected sunday games:")
    for c in sunday_selected:
        print(
            f"  {c.start.strftime('%H:%M')} {c.channel_number} ({c.channel_class}) "
            f"{c.title} | {c.subtitle}"
        )

    if changes:
        print("Changes:")
        for key, old, new in changes:
            print(f"  {key}: '{old}' -> '{new}'")
    else:
        print("No channel number changes.")

    if args.dry_run:
        print("Dry run: not writing channels file.")
        return
    save_yaml(args.channels, channels_cfg)
    print(f"Wrote {args.channels}")


if __name__ == "__main__":
    main()
