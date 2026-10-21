#!/usr/bin/env python3
"""See if DirecTV's public sports pages name a channel for each game.

This machine is blocked from directv.com. Run it on a PC that can open the site:

  python3 scripts/avaccess/probe_directv_sports.py --zip 27403

Paste the printed report. Raw pages are saved under ./directv-sports-probe/ and
are not part of the app. No login, and it does not tune a receiver.
"""

from __future__ import annotations

import argparse
import json
import re
import ssl
import sys
import urllib.error
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlparse

USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
)
PAGES = (
    "https://www.directv.com/sports-info/football/all",
    "https://www.directv.com/sports-info/leagues/nfl/schedule",
    "https://www.directv.com/sports-info/baseball/all",
    "https://www.directv.com/sports-info/leagues/mlb/schedule",
)
# Paths named in https://www.directv.com/robots.txt. They are public URLs.
SEED_APIS = (
    "https://www.directv.com/sports-info/season?league_text_id=nfl",
    "https://www.directv.com/sports-info/season?league_text_id=mlb",
    "https://www.directv.com/sports-info/embed/api/",
)
MAX_SCRIPTS = 6
MAX_APIS = 8
MAX_BYTES = 1_500_000

_SCRIPT_SRC = re.compile(r"""<script[^>]+src=["']([^"']+)["']""", re.I)
_URL = re.compile(r"""https?://[^"'\\\s<>]+|/sports-info/[A-Za-z0-9_./?=&%-]+""")
_CHANNEL_KEYS = {
    "channel",
    "channelnumber",
    "channelnum",
    "channelno",
    "major",
    "station",
}
_TITLE_KEYS = {"title", "eventtitle", "name", "programtitle", "episodetitle"}
_TEAM_KEYS = {"hometeam", "awayteam", "home", "away", "visitor", "opponent"}


class _ScriptSrcParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.srcs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "script":
            return
        for key, value in attrs:
            if key.lower() == "src" and value:
                self.srcs.append(value)


def extract_script_srcs(html: str) -> list[str]:
    parser = _ScriptSrcParser()
    parser.feed(html)
    found = list(parser.srcs)
    found.extend(_SCRIPT_SRC.findall(html))
    out: list[str] = []
    for src in found:
        if src not in out:
            out.append(src)
    return out


def extract_urls(text: str) -> list[str]:
    out: list[str] = []
    for match in _URL.findall(text):
        cleaned = match.rstrip(").,;]")
        if cleaned not in out:
            out.append(cleaned)
    return out


def _norm_key(key: str) -> str:
    return re.sub(r"[^a-z0-9]", "", key.lower())


def _channel_value(value: Any) -> str | None:
    if isinstance(value, bool) or value is None:
        return None
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        text = value.strip()
        if re.fullmatch(r"\d{2,4}(?:\.\d+)?", text):
            return text.split(".", 1)[0]
    return None


def _label(value: Any) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, dict):
        for key in ("name", "shortName", "displayName", "title", "abbreviation"):
            inner = value.get(key)
            if isinstance(inner, str) and inner.strip():
                return inner.strip()
    return ""


def walk_events(node: Any, found: list[dict[str, str]] | None = None) -> list[dict[str, str]]:
    """Pull objects that look like a game plus a channel number."""
    if found is None:
        found = []
    if isinstance(node, dict):
        flat = {_norm_key(str(key)): value for key, value in node.items()}
        channel = ""
        for key, value in flat.items():
            if key in _CHANNEL_KEYS:
                channel = _channel_value(value) or channel
        title = ""
        for key, value in flat.items():
            if key in _TITLE_KEYS and isinstance(value, str):
                title = value.strip()
                break
        away = ""
        home = ""
        for key, value in flat.items():
            if key in {"awayteam", "away", "visitor"}:
                away = away or _label(value)
            elif key in {"hometeam", "home"}:
                home = home or _label(value)
        teams = f"{away} at {home}" if away and home else ""
        if channel and (title or teams):
            row = {"channel": channel, "title": title or teams}
            if teams and teams != title:
                row["teams"] = teams
            if row not in found:
                found.append(row)
        for value in node.values():
            walk_events(value, found)
    elif isinstance(node, list):
        for value in node:
            walk_events(value, found)
    return found


def embedded_json(html: str) -> list[Any]:
    blobs: list[Any] = []
    pattern = re.compile(
        r'<script[^>]*type=["\']application/(?:json|ld\+json)["\'][^>]*>(.*?)</script>',
        re.I | re.S,
    )
    for match in pattern.finditer(html):
        try:
            blobs.append(json.loads(match.group(1)))
        except json.JSONDecodeError:
            continue
    return blobs


def text_hits(text: str) -> dict[str, Any]:
    lowered = text.lower()
    slots = sorted(set(re.findall(r"\b955[0-9]\b|\b956[0-7]\b", text)))
    return {
        "sundayTicket": lowered.count("sunday ticket"),
        "extraInnings": lowered.count("extra innings"),
        "localProgramming": lowered.count("local programming"),
        "nflFootball": lowered.count("nfl football"),
        "slots9550": slots,
    }


def same_site(url: str) -> bool:
    host = urlparse(url).hostname or ""
    return host == "directv.com" or host.endswith(".directv.com")


def interesting(url: str) -> bool:
    lowered = url.lower()
    if any(token in lowered for token in ("googletagmanager", "facebook", "doubleclick", "demdex")):
        return False
    return any(
        token in lowered
        for token in ("sports-info", "schedule", "season", "embed/api", "lineup", "channel")
    )


def fetch(url: str, timeout: float = 30) -> dict[str, Any]:
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept": "text/html,application/json;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout, context=ssl.create_default_context()) as response:
            raw = response.read(MAX_BYTES + 1)
            truncated = len(raw) > MAX_BYTES
            body = raw[:MAX_BYTES].decode("utf-8", "replace")
            return {
                "url": url,
                "status": response.status,
                "contentType": response.headers.get("content-type", ""),
                "body": body,
                "truncated": truncated,
                "error": "",
            }
    except urllib.error.HTTPError as exc:
        body = exc.read(8000).decode("utf-8", "replace")
        return {
            "url": url,
            "status": exc.code,
            "contentType": exc.headers.get("content-type", "") if exc.headers else "",
            "body": body,
            "truncated": False,
            "error": f"HTTP {exc.code}",
        }
    except Exception as exc:  # noqa: BLE001 — report the network failure to the operator
        return {
            "url": url,
            "status": 0,
            "contentType": "",
            "body": "",
            "truncated": False,
            "error": f"{type(exc).__name__}: {exc}",
        }


def _safe_name(url: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", urlparse(url).path.strip("/")) or "index"
    query = urlparse(url).query
    if query:
        cleaned += "_" + re.sub(r"[^A-Za-z0-9._-]+", "_", query)[:40]
    return cleaned[:80]


def _print_result(result: dict[str, Any], events: list[dict[str, str]]) -> None:
    hits = text_hits(result["body"])
    print(f"\nURL {result['url']}")
    status = result["status"] or result["error"]
    print(f"  status {status}  bytes {len(result['body'])}  {result['contentType']}")
    if result["error"] and result["status"] == 0:
        print(f"  error {result['error']}")
    print(
        "  mentions "
        f"Sunday Ticket={hits['sundayTicket']} "
        f"Extra Innings={hits['extraInnings']} "
        f"Local Programming={hits['localProgramming']} "
        f"NFL Football={hits['nflFootball']}"
    )
    if hits["slots9550"]:
        print(f"  Sunday Ticket majors in the page: {', '.join(hits['slots9550'])}")
    else:
        print("  no 9552–9567 channel numbers in this response")
    if events:
        print(f"  games with a channel ({min(len(events), 12)} of {len(events)}):")
        for row in events[:12]:
            teams = f" | {row['teams']}" if row.get("teams") else ""
            print(f"    ch {row['channel']}: {row['title']}{teams}")
    elif result["status"] == 200 and "loading" in result["body"].lower() and not events:
        print("  page shell only (it says Loading). Schedule is in a later request.")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--zip", default="27403", help="Market ZIP to note in the report")
    parser.add_argument(
        "--out",
        type=Path,
        default=Path("directv-sports-probe"),
        help="Folder for the raw responses",
    )
    args = parser.parse_args(argv)
    args.out.mkdir(parents=True, exist_ok=True)

    print(f"DirecTV sports probe for ZIP {args.zip}")
    print("Looking for a channel number on each game, especially 9552–9567.")
    pages = [fetch(url) for url in PAGES]
    discovered: list[str] = []
    for page in pages:
        if page["status"] != 200:
            continue
        path = args.out / f"{_safe_name(page['url'])}.html"
        path.write_text(page["body"], encoding="utf-8")
        for src in extract_script_srcs(page["body"]):
            absolute = urljoin(page["url"], src)
            if same_site(absolute) and absolute not in discovered:
                discovered.append(absolute)
        for found in extract_urls(page["body"]):
            absolute = urljoin(page["url"], found)
            if same_site(absolute) and interesting(absolute) and absolute not in discovered:
                discovered.append(absolute)

    scripts = []
    for url in discovered[:MAX_SCRIPTS]:
        if not url.endswith(".js") and "/static/" not in url and "/_next/" not in url:
            continue
        result = fetch(url)
        scripts.append(result)
        if result["status"] == 200:
            for found in extract_urls(result["body"]):
                absolute = urljoin(url, found)
                if same_site(absolute) and interesting(absolute) and absolute not in discovered:
                    discovered.append(absolute)

    apis = [fetch(url) for url in SEED_APIS]
    extra = [
        url
        for url in discovered
        if interesting(url) and not url.endswith(".js") and url not in PAGES and url not in SEED_APIS
    ]
    apis.extend(fetch(url) for url in extra[:MAX_APIS])

    blocked = all(item["status"] in {0, 403, 500} for item in pages)
    for item in pages + apis:
        events: list[dict[str, str]] = []
        body = item["body"].strip()
        if body[:1] in "[{":
            try:
                events = walk_events(json.loads(body))
            except json.JSONDecodeError:
                events = []
        else:
            for blob in embedded_json(item["body"]):
                events.extend(walk_events(blob))
        _print_result(item, events)
        if item["status"] == 200 and item not in pages:
            suffix = ".json" if body[:1] in "[{" else ".txt"
            (args.out / f"{_safe_name(item['url'])}{suffix}").write_text(body, encoding="utf-8")

    print("\n---")
    if blocked:
        print("This PC was blocked too (403 or connection error). The report above is the result.")
        return 1
    slot_events = []
    for item in pages + apis:
        body = item["body"].strip()
        if body[:1] not in "[{":
            continue
        try:
            payload = json.loads(body)
        except json.JSONDecodeError:
            continue
        for row in walk_events(payload):
            if row["channel"].startswith("95"):
                slot_events.append(row)
    if slot_events:
        print(f"Found {len(slot_events)} games tied to a 95xx channel. Paste this report back.")
    else:
        print(
            "No game was tied to a 9552–9567 Sunday Ticket channel. "
            "If the lines above only show FOX, CBS, ESPN, or NBC, this page does not map the slot. "
            "Paste this report back."
        )
    print(f"Saved responses in {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
