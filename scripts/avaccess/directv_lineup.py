"""DirecTV Greensboro guide lineup from TV Passport.

TV Passport lineup 5960D is "DirecTV - Greensboro - Winston-Salem, NC".
Channel numbers in that grid are the majors the guide tunes. Sports pages
do not use this file.
"""

from __future__ import annotations

import datetime as dt
import http.cookiejar
import json
import re
import sys
import urllib.request
from html.parser import HTMLParser
from pathlib import Path
from typing import Any

ZIP_CODE = "27403"
LINEUP_ID = "5960D"
LINEUP_SET_URL = (
    "https://www.tvpassport.com/lineups/set/5960D"
    "?lineupname=DirecTV+-+Greensboro+-+Winston-Salem%2C+NC+"
    "&tz=America/New_York"
)
USER_AGENT = "Mozilla/5.0 (compatible; avaccess-guide/1.0)"

# Audio services, not music-video networks (MTV, CMT, VH1 stay).
_MUSIC_AUDIO = (
    "music choice",
    "sirius",
    "siriusxm",
    "sonic tap",
    "dmx",
)
_PPV = ("ppv", "pay-per-view", "pay per view", "hot choice")

_TRAILING_NUMBER = re.compile(r"\s*\([^)]*\)\s*$")
_SPORTS_SLOT = re.compile(r"^DirecTV Sports (\d+)$", re.IGNORECASE)
_NFLST = re.compile(r"^NFLST\d+$", re.IGNORECASE)


class _LineupParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.rows: list[dict[str, str]] = []
        self._cur: dict[str, str] | None = None
        self._capture: str | None = None

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {key: value or "" for key, value in attrs}
        classes = ad.get("class", "").split()
        if tag == "div" and "channel_cell" in classes:
            self._cur = {
                "station": ad.get("data-station", "").strip(),
                "title": ad.get("title", "").strip(),
                "href": "",
                "callsign": "",
                "number": "",
            }
            self.rows.append(self._cur)
            return
        if self._cur is None:
            return
        if tag == "a" and "/stations/" in ad.get("href", ""):
            self._cur["href"] = ad["href"]
        if tag == "span" and ad.get("class") == "channel-callsign":
            self._capture = "callsign"
        elif tag == "span" and ad.get("class") == "channel-number":
            self._capture = "number"

    def handle_endtag(self, tag: str) -> None:
        if tag == "span":
            self._capture = None

    def handle_data(self, data: str) -> None:
        if self._cur is not None and self._capture:
            self._cur[self._capture] += data.strip()


def parse_lineup_html(html: str) -> list[dict[str, str]]:
    parser = _LineupParser()
    parser.feed(html)
    return [row for row in parser.rows if row.get("number")]


def exclude_reason(name: str, callsign: str = "") -> str | None:
    """Why a channel stays out of the guide, or None to keep it.

    Dropped: music audio, pay-per-view, promo barkers, and channels that are
    not in the package (on-demand storefronts). Music-video networks
    (MTV, CMT, VH1), premiums, shopping, and news stay.
    """
    blob = f"{name} {callsign}".lower()
    plain = _TRAILING_NUMBER.sub("", name).strip().lower()
    if "audience network" in blob or re.search(r"\bbarker\b", blob):
        return "barker"
    if any(token in blob for token in _MUSIC_AUDIO):
        return "music"
    if any(token in blob for token in _PPV):
        return "ppv"
    # 100s "DirecTV Sports 121" slots are event / PPV, not a network.
    if re.fullmatch(r"directv sports 1\d\d", plain):
        return "ppv"
    if "on demand" in blob or "ondemand" in blob or "on dmenad" in blob:
        return "not-in-package"
    return None


def _display_name(title: str, callsign: str) -> str:
    plain = _TRAILING_NUMBER.sub("", title).strip() or title.strip()
    sports = _SPORTS_SLOT.match(plain)
    if sports and _NFLST.match(callsign.strip()):
        return f"NFL Sunday Ticket {sports.group(1)}"
    return plain


def _category(name: str) -> str:
    blob = name.lower()
    if any(
        token in blob
        for token in (
            "espn",
            "nfl",
            "nba",
            "mlb",
            "nhl",
            "sports",
            "sec network",
            "acc network",
            "big ten",
            "fox sports",
            "fanduel",
            "redzone",
            "golf",
            "tennis",
        )
    ):
        return "Sports"
    if any(token in blob for token in ("news", "cnn", "msnbc", "weather", "cnbc")):
        return "News"
    if any(
        token in blob
        for token in ("greensboro", "winston-salem", "winston salem", "pbs nc", "unc-tv", "unctv")
    ):
        return "Local"
    return "TV"


def _number_value(number: str) -> float:
    major, _, minor = str(number).partition("-")
    try:
        base = int(major)
    except ValueError:
        return 1e12
    try:
        sub = int(minor) if minor else 0
    except ValueError:
        sub = 0
    return base + sub / 1000.0


def guide_channels_from_rows(rows: list[dict[str, str]]) -> tuple[list[dict[str, str]], dict[str, int]]:
    """Filter, dedupe, and shape rows for the Sports Routing guide."""
    excluded: dict[str, int] = {}
    kept: list[dict[str, str]] = []
    seen_numbers: set[str] = set()
    seen_stations: set[str] = set()
    ordered = sorted(rows, key=lambda row: _number_value(row.get("number", "")))
    for row in ordered:
        number = str(row.get("number", "")).strip()
        if not number or number in seen_numbers:
            continue
        title = row.get("title") or row.get("name") or ""
        callsign = row.get("callsign") or ""
        reason = exclude_reason(title, callsign)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + 1
            continue
        station = str(row.get("station") or "").strip()
        # 9xxx grids repeat a station that already has its package major (RedZone).
        try:
            major = int(number.split("-", 1)[0])
        except ValueError:
            major = 0
        if station and station in seen_stations and major >= 9000:
            excluded["not-in-package"] = excluded.get("not-in-package", 0) + 1
            continue
        name = _display_name(title, callsign)
        kept.append(
            {
                "id": f"dtv-{number}",
                "number": number,
                "name": name,
                "category": _category(name),
            }
        )
        seen_numbers.add(number)
        if station:
            seen_stations.add(station)
    return kept, excluded


def _opener() -> urllib.request.OpenerDirector:
    jar = http.cookiejar.CookieJar()
    return urllib.request.build_opener(urllib.request.HTTPCookieProcessor(jar))


def fetch_lineup_html(opener: urllib.request.OpenerDirector | None = None) -> str:
    """POST the ZIP, then open the DirecTV Greensboro lineup with that cookie."""
    client = opener or _opener()
    headers = {"User-Agent": USER_AGENT, "Accept": "text/html"}
    post = urllib.request.Request(
        "https://www.tvpassport.com/index.php/lineups",
        data=f"postalCode={ZIP_CODE}".encode(),
        headers={**headers, "Content-Type": "application/x-www-form-urlencoded"},
    )
    with client.open(post, timeout=30) as response:
        response.read()
    request = urllib.request.Request(LINEUP_SET_URL, headers=headers)
    with client.open(request, timeout=40) as response:
        return response.read().decode("utf-8", errors="replace")


def build_guide_channel_payload(html: str, now: dt.datetime | None = None) -> dict[str, Any]:
    moment = now or dt.datetime.now(dt.timezone.utc)
    channels, excluded = guide_channels_from_rows(parse_lineup_html(html))
    if not channels:
        raise ValueError("DirecTV lineup parse returned no channels")
    return {
        "zip": ZIP_CODE,
        "source": f"tvpassport:{LINEUP_ID}",
        "generatedAt": moment.astimezone(dt.timezone.utc).isoformat(),
        "excluded": excluded,
        "channels": channels,
    }


def main(argv: list[str] | None = None) -> int:
    import argparse

    root = Path(__file__).resolve().parents[2]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--out",
        type=Path,
        default=root / "homeassistant" / "config" / "www" / "avaccess" / "guide_channels.json",
    )
    args = parser.parse_args(argv)
    try:
        html = fetch_lineup_html()
        payload = build_guide_channel_payload(html)
    except (OSError, ValueError) as exc:
        print(f"directv_lineup failed: {exc}", file=sys.stderr)
        return 1
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(
        f"{args.out} channels={len(payload['channels'])} excluded={payload['excluded']}",
        file=sys.stderr,
    )
    print(args.out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
