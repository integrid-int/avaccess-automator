#!/usr/bin/env python3
"""Pull Schedules Direct JSON → XMLTV for ZIP 27403 Spectrum/Charter."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import re
import sys
import xml.etree.ElementTree as et
from pathlib import Path
from typing import Any
from xml.dom import minidom

import requests
import yaml

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

SD_BASE = "https://json.schedulesdirect.org/20141201"
DEFAULT_CONFIG = ROOT / "config" / "schedules_direct.yaml"
DEFAULT_UA = "avaccess-automator/1.0 (github.com/integrid-int/avaccess-automator)"
SPECTRUM_NAME_RE = re.compile(r"spectrum|charter", re.I)


class SchedulesDirectError(RuntimeError):
    pass


def password_sha1(password: str | None, password_sha1_env: str | None) -> str:
    if password_sha1_env and re.fullmatch(r"[0-9a-fA-F]{40}", password_sha1_env):
        return password_sha1_env.lower()
    if not password:
        raise SchedulesDirectError(
            "Set SD_PASSWORD or SD_PASSWORD_SHA1 in the environment"
        )
    return hashlib.sha1(password.encode("utf-8")).hexdigest()


def load_config(path: Path) -> dict[str, Any]:
    if not path.is_file():
        raise SchedulesDirectError(f"Missing config: {path}")
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise SchedulesDirectError(f"Expected YAML mapping in {path}")
    return data


def sd_session(username: str, sha1: str) -> requests.Session:
    session = requests.Session()
    session.headers.update(
        {
            "User-Agent": DEFAULT_UA,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }
    )
    resp = session.post(
        f"{SD_BASE}/token",
        json={"username": username, "password": sha1},
        timeout=60,
    )
    try:
        payload = resp.json()
    except ValueError as exc:
        raise SchedulesDirectError(f"Token response not JSON: {resp.text[:200]}") from exc
    if resp.status_code >= 400 or not payload.get("token"):
        raise SchedulesDirectError(
            f"Token failed: {payload.get('message') or resp.text[:200]}"
        )
    session.headers["token"] = payload["token"]
    return session


def list_headend_lineups(
    session: requests.Session, *, country: str, postalcode: str
) -> list[dict[str, Any]]:
    resp = session.get(
        f"{SD_BASE}/headends",
        params={"country": country, "postalcode": postalcode},
        timeout=60,
    )
    data = resp.json()
    if resp.status_code >= 400 or not isinstance(data, list):
        raise SchedulesDirectError(
            f"headends failed: {data if isinstance(data, dict) else resp.text[:200]}"
        )
    out: list[dict[str, Any]] = []
    for head in data:
        if not isinstance(head, dict):
            continue
        for lineup in head.get("lineups") or []:
            out.append(
                {
                    "lineup": lineup.get("lineup"),
                    "name": lineup.get("name"),
                    "uri": lineup.get("uri"),
                    "transport": head.get("transport"),
                    "location": head.get("location"),
                    "headend": head.get("headend"),
                }
            )
    return out


def prefer_spectrum_lineup(candidates: list[dict[str, Any]]) -> dict[str, Any]:
    cable = [
        c
        for c in candidates
        if SPECTRUM_NAME_RE.search(str(c.get("name") or ""))
        and str(c.get("transport") or "").lower() == "cable"
    ]
    if not cable:
        raise SchedulesDirectError(
            "No Spectrum/Charter cable lineup found for this postal code"
        )
    # Prefer -X (expanded digital) over -L when both exist.
    cable.sort(key=lambda c: (0 if str(c.get("lineup") or "").endswith("-X") else 1))
    return cable[0]


def ensure_lineup(session: requests.Session, lineup_id: str) -> None:
    resp = session.put(f"{SD_BASE}/lineups/{lineup_id}", timeout=60)
    data = resp.json() if resp.content else {}
    # Already present is fine; SD may return OK or an error we can ignore if GET works.
    if resp.status_code < 400:
        return
    message = str(data.get("message") or data.get("response") or resp.text)
    if "already" in message.lower() or data.get("response") in {"OK", "DUPLICATE_LINEUP"}:
        return
    # Confirm via GET
    check = session.get(f"{SD_BASE}/lineups/{lineup_id}", timeout=60)
    if check.status_code < 400:
        return
    raise SchedulesDirectError(f"Could not add lineup {lineup_id}: {message}")


def fetch_lineup(session: requests.Session, lineup_id: str) -> dict[str, Any]:
    resp = session.get(f"{SD_BASE}/lineups/{lineup_id}", timeout=120)
    data = resp.json()
    if resp.status_code >= 400:
        raise SchedulesDirectError(
            f"lineup fetch failed: {data.get('message') or resp.text[:200]}"
        )
    return data


def fetch_schedules(
    session: requests.Session,
    station_ids: list[str],
    *,
    days: int,
    batch_size: int = 5000,
) -> list[dict[str, Any]]:
    dates = [
        (dt.date.today() + dt.timedelta(days=offset)).isoformat()
        for offset in range(max(1, days))
    ]
    payload = [{"stationID": sid, "date": dates} for sid in station_ids]
    out: list[dict[str, Any]] = []
    for start in range(0, len(payload), batch_size):
        chunk = payload[start : start + batch_size]
        resp = session.post(f"{SD_BASE}/schedules", json=chunk, timeout=180)
        data = resp.json()
        if resp.status_code >= 400:
            raise SchedulesDirectError(
                f"schedules failed: {data if isinstance(data, dict) else resp.text[:200]}"
            )
        if not isinstance(data, list):
            raise SchedulesDirectError("schedules response was not a list")
        out.extend(data)
    return out


def fetch_programs(
    session: requests.Session, program_ids: list[str], *, batch_size: int = 500
) -> dict[str, dict[str, Any]]:
    unique = sorted(set(program_ids))
    by_id: dict[str, dict[str, Any]] = {}
    for start in range(0, len(unique), batch_size):
        chunk = unique[start : start + batch_size]
        resp = session.post(f"{SD_BASE}/programs", json=chunk, timeout=180)
        data = resp.json()
        if resp.status_code >= 400:
            raise SchedulesDirectError(
                f"programs failed: {data if isinstance(data, dict) else resp.text[:200]}"
            )
        if not isinstance(data, list):
            raise SchedulesDirectError("programs response was not a list")
        for prog in data:
            pid = str(prog.get("programID") or "")
            if pid:
                by_id[pid] = prog
    return by_id


def _xmltv_time(air_date_time: str) -> str:
    """Convert SD airDateTime (ISO) to XMLTV YYYYmmddHHMMSS +0000."""
    moment = dt.datetime.fromisoformat(str(air_date_time).replace("Z", "+00:00"))
    moment = moment.astimezone(dt.timezone.utc)
    return moment.strftime("%Y%m%d%H%M%S +0000")


def _channel_number(raw: Any) -> str:
    text = str(raw or "").strip()
    if re.fullmatch(r"\d+", text):
        return str(int(text))  # strip leading zeros: 016 -> 16
    return text


def build_xmltv(
    lineup: dict[str, Any],
    schedules: list[dict[str, Any]],
    programs: dict[str, dict[str, Any]],
) -> bytes:
    root = et.Element(
        "tv",
        {
            "source-info-name": "Schedules Direct",
            "generator-info-name": "avaccess-automator/pull_schedules_direct.py",
        },
    )
    station_by_id = {
        str(st.get("stationID")): st for st in (lineup.get("stations") or [])
    }
    xml_id_by_station: dict[str, str] = {}
    for mapping in lineup.get("map") or []:
        sid = str(mapping.get("stationID") or "")
        if not sid or sid not in station_by_id:
            continue
        number = _channel_number(mapping.get("channel"))
        xml_id = f"I{sid}.schedulesdirect.org"
        xml_id_by_station[sid] = xml_id
        st = station_by_id[sid]
        ch = et.SubElement(root, "channel", {"id": xml_id})
        name = str(st.get("name") or st.get("callsign") or sid)
        callsign = str(st.get("callsign") or name)
        et.SubElement(ch, "display-name").text = f"{number} {name}"
        et.SubElement(ch, "display-name").text = callsign
        et.SubElement(ch, "display-name").text = number
        et.SubElement(ch, "display-name").text = name

    for sched in schedules:
        sid = str(sched.get("stationID") or "")
        xml_id = xml_id_by_station.get(sid)
        if not xml_id:
            continue
        for prog in sched.get("programs") or []:
            pid = str(prog.get("programID") or "")
            air = prog.get("airDateTime")
            dur = prog.get("duration")
            if not air or dur is None:
                continue
            try:
                start = _xmltv_time(str(air))
                start_dt = dt.datetime.fromisoformat(str(air).replace("Z", "+00:00"))
                stop_dt = start_dt + dt.timedelta(seconds=int(dur))
                stop = stop_dt.astimezone(dt.timezone.utc).strftime("%Y%m%d%H%M%S +0000")
            except (TypeError, ValueError):
                continue
            meta = programs.get(pid) or {}
            titles = meta.get("titles") or []
            title = ""
            if titles and isinstance(titles[0], dict):
                title = str(titles[0].get("title120") or "")
            if not title:
                title = pid
            node = et.SubElement(
                root,
                "programme",
                {"start": start, "stop": stop, "channel": xml_id},
            )
            et.SubElement(node, "title", {"lang": "en"}).text = title
            for cat in meta.get("genres") or []:
                et.SubElement(node, "category", {"lang": "en"}).text = str(cat)

    rough = et.tostring(root, encoding="utf-8")
    pretty = minidom.parseString(rough).toprettyxml(indent="  ", encoding="utf-8")
    return pretty


def write_lineup_id(config_path: Path, lineup_id: str) -> None:
    data = load_config(config_path)
    data["lineup_id"] = lineup_id
    config_path.write_text(
        yaml.safe_dump(data, sort_keys=False, allow_unicode=False),
        encoding="utf-8",
    )


MUSIC_NAME_RE = re.compile(
    r"music\s*choice|sonic\s*tap|stingray\s*music|\bmc\b",
    re.I,
)
SPORTS_NAME_RE = re.compile(
    r"\bespn|\bfs1\b|\bfs2\b|fox sports|nfl|nba|nhl|mlb|golf|tennis|"
    r"fanduel|acc network|sec network|big ten|btn|olympic|"
    r"cbs sports|nbc sports|be[ií]n|sportsnet|stadium|"
    r"willow|tvg|outdoor channel|maav|fight",
    re.I,
)
NEWS_NAME_RE = re.compile(
    r"news|cnn|msnbc|cnbc|fox news|weather|bloomberg|c-span|newsnation",
    re.I,
)
KIDS_NAME_RE = re.compile(
    r"disney|nickelodeon|nick\b|cartoon|universal kids|baby|pbs kids|boomerang",
    re.I,
)
PREMIUM_NAME_RE = re.compile(
    r"\bhbo\b|cinemax|showtime|\bsho\b|starz|movieplex|indieplex|retroplex|the movie channel|\btmc\b",
    re.I,
)


def classify_category(name: str, callsign: str = "") -> str:
    text = f"{name} {callsign}"
    if MUSIC_NAME_RE.search(text):
        return "Music"
    if PREMIUM_NAME_RE.search(text):
        return "Premium"
    if SPORTS_NAME_RE.search(text):
        return "Sports"
    if NEWS_NAME_RE.search(text):
        return "News"
    if KIDS_NAME_RE.search(text):
        return "Kids"
    return "Cable"


def lineup_channels_from_sd(
    lineup: dict[str, Any],
    *,
    lineup_id: str,
    exclude_music: bool = True,
) -> list[dict[str, Any]]:
    """Build panel GUIDE channels from Schedules Direct map (source of truth)."""
    stations = {
        str(st.get("stationID")): st for st in (lineup.get("stations") or [])
    }
    channels: list[dict[str, Any]] = []
    seen: set[str] = set()
    for mapping in lineup.get("map") or []:
        sid = str(mapping.get("stationID") or "")
        st = stations.get(sid)
        if not st:
            continue
        number = _channel_number(mapping.get("channel"))
        if not number or number in seen:
            continue
        name = str(st.get("name") or st.get("callsign") or sid).strip()
        callsign = str(st.get("callsign") or "").strip()
        category = classify_category(name, callsign)
        music = category == "Music" or bool(MUSIC_NAME_RE.search(name))
        if exclude_music and music:
            continue
        seen.add(number)
        channels.append(
            {
                "id": f"ch-{number}",
                "number": number,
                "name": name,
                "callsign": callsign,
                "category": category,
                "music": False,
                "stationId": sid,
            }
        )

    def sort_key(ch: dict[str, Any]) -> tuple[int, str]:
        n = ch["number"]
        return (int(n), n) if n.isdigit() else (10**9, n)

    channels.sort(key=sort_key)
    return channels


def lineup_channels_from_xmltv(
    xmltv_path: Path,
    *,
    exclude_music: bool = True,
) -> list[dict[str, Any]]:
    """Rebuild panel lineup from a Schedules Direct XMLTV cache (offline SoT)."""
    import xml.etree.ElementTree as etree

    root = etree.parse(xmltv_path).getroot()
    channels: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ch in root.findall("channel"):
        names = [
            (n.text or "").strip()
            for n in ch.findall("display-name")
            if n.text and n.text.strip()
        ]
        number = ""
        for name in names:
            if re.fullmatch(r"\d+", name):
                number = str(int(name))
                break
        if not number or number in seen:
            continue
        # Prefer bare network name (last display-name from our writer).
        name = names[-1] if names else number
        callsign = names[1] if len(names) > 1 else name
        category = classify_category(name, callsign)
        music = category == "Music" or bool(MUSIC_NAME_RE.search(name))
        if exclude_music and music:
            continue
        seen.add(number)
        sid = str(ch.attrib.get("id") or "")
        m = re.search(r"I(\d+)\.schedulesdirect\.org", sid)
        channels.append(
            {
                "id": f"ch-{number}",
                "number": number,
                "name": name,
                "callsign": callsign,
                "category": category,
                "music": False,
                "stationId": m.group(1) if m else "",
            }
        )

    def sort_key(item: dict[str, Any]) -> tuple[int, str]:
        n = item["number"]
        return (int(n), n) if n.isdigit() else (10**9, n)

    channels.sort(key=sort_key)
    return channels


def write_lineup_artifacts(
    channels: list[dict[str, Any]],
    *,
    lineup_id: str,
    postalcode: str,
) -> list[Path]:
    """Write SD lineup JSON + panel JS module (Schedules Direct is SoT)."""
    payload = {
        "zip": postalcode,
        "package": "spectrum-cable",
        "packageColumn": "Schedules Direct",
        "source": f"schedulesdirect:{lineup_id}",
        "lineupId": lineup_id,
        "generatedAt": dt.datetime.now(tz=dt.timezone.utc).isoformat(),
        "channels": channels,
    }
    paths = [
        ROOT / "config" / "spectrum_lineup_27403.json",
        ROOT
        / "homeassistant"
        / "config"
        / "www"
        / "avaccess"
        / "spectrum_lineup_27403.json",
    ]
    js_path = (
        ROOT
        / "homeassistant"
        / "config"
        / "www"
        / "panels"
        / "spectrum-lineup-data.js"
    )
    written: list[Path] = []
    for path in paths:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
        written.append(path)
        print(path)
    js_path.parent.mkdir(parents=True, exist_ok=True)
    # Strip internal-only fields from the browser module.
    browser_channels = [
        {
            "id": c["id"],
            "number": c["number"],
            "name": c["name"],
            "category": c["category"],
        }
        for c in channels
    ]
    js_path.write_text(
        "// Generated from Schedules Direct — do not edit by hand.\n"
        f"export const GUIDE_CHANNELS = {json.dumps(browser_channels, indent=2)};\n",
        encoding="utf-8",
    )
    written.append(js_path)
    print(js_path)
    print(f"{len(channels)} channels (Schedules Direct SoT, music excluded)")
    return written


def pull(
    cfg: dict[str, Any],
    *,
    config_path: Path | None = None,
    write_lineup_id: bool = False,
) -> Path:
    username = os.environ.get("SD_USERNAME") or cfg.get("username")
    if not username:
        raise SchedulesDirectError("Set SD_USERNAME")
    sha = password_sha1(
        os.environ.get("SD_PASSWORD"),
        os.environ.get("SD_PASSWORD_SHA1"),
    )
    country = str(cfg.get("country") or "USA")
    postalcode = str(cfg.get("postalcode") or "27403")
    days = int(cfg.get("days") or 2)
    lineup_id = str(cfg.get("lineup_id") or "").strip()
    out = Path(str(cfg.get("xmltv_out") or "config/cache/schedules_direct.xmltv"))
    if not out.is_absolute():
        out = ROOT / out

    session = sd_session(str(username), sha)
    if not lineup_id:
        candidates = list_headend_lineups(
            session, country=country, postalcode=postalcode
        )
        chosen = prefer_spectrum_lineup(candidates)
        lineup_id = str(chosen["lineup"])
        print(f"Selected lineup {lineup_id} ({chosen.get('name')} / {chosen.get('transport')})")
        if write_lineup_id and config_path is not None:
            write_lineup_id(config_path, lineup_id)

    ensure_lineup(session, lineup_id)
    lineup = fetch_lineup(session, lineup_id)
    # Schedules Direct map is the channel-number / name authority for the panel.
    channels = lineup_channels_from_sd(
        lineup,
        lineup_id=lineup_id,
        exclude_music=bool(cfg.get("exclude_music", True)),
    )
    write_lineup_artifacts(channels, lineup_id=lineup_id, postalcode=postalcode)

    station_ids = [
        str(m.get("stationID"))
        for m in (lineup.get("map") or [])
        if m.get("stationID")
    ]
    print(f"Stations: {len(station_ids)}; days={days}")
    schedules = fetch_schedules(session, station_ids, days=days)
    program_ids = [
        str(p.get("programID"))
        for sched in schedules
        for p in (sched.get("programs") or [])
        if p.get("programID")
    ]
    print(f"Schedule rows: {len(schedules)}; program ids: {len(set(program_ids))}")
    programs = fetch_programs(session, program_ids)
    xml_bytes = build_xmltv(lineup, schedules, programs)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(xml_bytes)
    print(out)
    return out


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument(
        "--write-lineup-id",
        action="store_true",
        help="Persist discovered lineup_id into the config YAML",
    )
    parser.add_argument(
        "--list-lineups",
        action="store_true",
        help="List headend lineups for postalcode and exit",
    )
    parser.add_argument(
        "--lineup-from-xmltv",
        type=Path,
        help="Rebuild panel lineup JSON/JS from an existing SD XMLTV cache (no API)",
    )
    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.config)
        if args.lineup_from_xmltv:
            xmltv_path = args.lineup_from_xmltv
            if not xmltv_path.is_absolute():
                xmltv_path = ROOT / xmltv_path
            channels = lineup_channels_from_xmltv(
                xmltv_path,
                exclude_music=bool(cfg.get("exclude_music", True)),
            )
            write_lineup_artifacts(
                channels,
                lineup_id=str(cfg.get("lineup_id") or "from-xmltv"),
                postalcode=str(cfg.get("postalcode") or "27403"),
            )
            return 0
        if args.list_lineups:
            username = os.environ.get("SD_USERNAME") or cfg.get("username")
            sha = password_sha1(
                os.environ.get("SD_PASSWORD"),
                os.environ.get("SD_PASSWORD_SHA1"),
            )
            session = sd_session(str(username), sha)
            rows = list_headend_lineups(
                session,
                country=str(cfg.get("country") or "USA"),
                postalcode=str(cfg.get("postalcode") or "27403"),
            )
            for row in rows:
                print(
                    f"{row.get('lineup')}\t{row.get('transport')}\t"
                    f"{row.get('location')}\t{row.get('name')}"
                )
            return 0
        pull(cfg, config_path=args.config, write_lineup_id=args.write_lineup_id)
    except (OSError, SchedulesDirectError, requests.RequestException, yaml.YAMLError) as exc:
        print(f"pull_schedules_direct failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
