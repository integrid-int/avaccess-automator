"""Shared XMLTV fetch/parse helpers for AVAccess guide EPG."""

from __future__ import annotations

import datetime as dt
import gzip
import io
import re
import urllib.request
import xml.etree.ElementTree as et
import defusedxml.ElementTree as DefusedET
from dataclasses import dataclass
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo


@dataclass(frozen=True)
class Program:
    channel_id: str
    start: dt.datetime
    stop: dt.datetime | None
    title: str
    subtitle: str = ""
    desc: str = ""
    categories: tuple[str, ...] = ()


def fetch_xmltv_bytes(source_cfg: dict[str, Any]) -> bytes:
    """Load XMLTV bytes from a local file or URL, optionally gunzipping."""
    if "file" in source_cfg:
        raw = Path(source_cfg["file"]).read_bytes()
    elif "url" in source_cfg:
        with urllib.request.urlopen(source_cfg["url"], timeout=30) as resp:
            raw = resp.read()
    else:
        raise ValueError("source must include 'file' or 'url'")

    compression = str(source_cfg.get("compression", "auto")).lower()
    if compression == "none":
        return raw
    if compression == "gzip":
        return gzip.decompress(raw)
    if raw[:2] == b"\x1f\x8b":
        return gzip.decompress(raw)
    return raw


def parse_xmltv_time(raw: str, default_tz: ZoneInfo) -> dt.datetime:
    """Parse XMLTV datetime (YYYYmmddHHMMSS [+/-ZZZZ])."""
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


def parse_xmltv(
    xml_bytes: bytes, tz: ZoneInfo
) -> tuple[dict[str, list[str]], list[Program]]:
    """Parse channel display-names and programme list from XMLTV bytes."""
    root = DefusedET.parse(io.BytesIO(xml_bytes)).getroot()
    channels: dict[str, list[str]] = {}
    for ch in root.findall("channel"):
        ch_id = ch.attrib.get("id", "").strip()
        if not ch_id:
            continue
        names = [
            n.text.strip()
            for n in ch.findall("display-name")
            if n.text and n.text.strip()
        ]
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
        categories = tuple(
            c.text.strip()
            for c in p.findall("category")
            if c.text and c.text.strip()
        )
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
