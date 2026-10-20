"""Grab ZIP 27403 DirecTV favorites from TV Passport station pages.

TV Passport is the US listings source used by iptv-org/epg (`sites/tvpassport.com`).
The Home Assistant image has Python, not Node, so this fetches the same station
HTML the iptv-org grabber parses and writes XMLTV for `build_guide_epg.py`.
"""

from __future__ import annotations

import datetime as dt
import sys
import urllib.error
import urllib.request
import xml.etree.ElementTree as et
from dataclasses import dataclass
from html.parser import HTMLParser
from zoneinfo import ZoneInfo

BASE_URL = "https://www.tvpassport.com/tv-listings/stations"
MARKET_TZ = "America/New_York"
USER_AGENT = "Mozilla/5.0 (compatible; avaccess-guide/1.0)"


@dataclass(frozen=True)
class GuideChannel:
    number: str
    name: str
    site_id: str
    xmltv_id: str


@dataclass(frozen=True)
class Listing:
    start: dt.datetime
    stop: dt.datetime | None
    title: str
    subtitle: str = ""
    desc: str = ""


# DirecTV majors for ZIP 27403. site_id is the TV Passport station path.
# xmltv_id is what channel_number_map must list. HD pages when the site has them.
LINEUP: tuple[GuideChannel, ...] = (
    GuideChannel("4", "WGHP FOX", "fox-wghp-greensboro-nc-hd/4717", "WGHP81.us@HD"),
    GuideChannel("2", "WFMY CBS", "cbs-wfmy-greensboro-nc-hd/4718", "WFMYTV21.us@HD"),
    GuideChannel("12", "WXII NBC", "nbc-wxii-winstonsalem-nc-hd/4721", "WXIITV201.us@HD"),
    GuideChannel("45", "WXLV ABC", "abc-wxlv-winstonsalem-nc-hd/4719", "WXLVTV481.us@HD"),
    GuideChannel("206", "ESPN", "espn-hd/3036", "ESPN.us@HD"),
    GuideChannel("207", "ESPN2", "espn2-hd/3379", "ESPN2.us@HD"),
    GuideChannel("400", "FS1", "fox-sports-1/668", "FoxSports1.us"),
    GuideChannel("245", "TNT", "tnt-hd-east-feed/3037", "TNT.us@HD"),
    GuideChannel("705", "NFL Sunday Ticket 1", "nfl-sunday-ticket-1/2747", "NFLSundayTicket1.us@SD"),
)

_MOVIE_TITLES = {"movie", "cinéma", "cinema"}


class _StationParser(HTMLParser):
    """Pull timezone + listing rows from a TV Passport station page."""

    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.timezone: str | None = None
        self._in_tz = False
        self.items: list[dict[str, str]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        ad = {key: value or "" for key, value in attrs}
        if tag == "select" and ad.get("id") == "timezone_selector":
            self._in_tz = True
            return
        if self._in_tz and tag == "option" and self.timezone is None and "selected" in ad:
            value = ad.get("value", "").strip()
            if value:
                self.timezone = value
            return
        classes = ad.get("class", "").split()
        if tag == "div" and "list-group-item" in classes:
            self._take_item(ad)

    def handle_endtag(self, tag: str) -> None:
        if tag == "select":
            self._in_tz = False

    def _take_item(self, ad: dict[str, str]) -> None:
        start_raw = ad.get("data-st", "").strip()
        title = ad.get("data-showname", "").strip()
        if not start_raw or not title:
            return
        subtitle = ad.get("data-episodetitle", "").strip()
        if title.casefold() in _MOVIE_TITLES and subtitle:
            title = subtitle
            subtitle = ""
        self.items.append(
            {
                "start": start_raw,
                "duration": ad.get("data-duration", "").strip(),
                "title": title,
                "subtitle": subtitle,
                "desc": ad.get("data-description", "").strip(),
            }
        )


def parse_station_html(html: str) -> tuple[str, list[dict[str, str]]]:
    """Return (timezone name, raw listing rows) from a station page."""
    parser = _StationParser()
    parser.feed(html)
    return parser.timezone or MARKET_TZ, parser.items


def _xmltv_stamp(moment: dt.datetime) -> str:
    return moment.strftime("%Y%m%d%H%M%S %z")


def materialize_listings(rows: list[dict[str, str]], timezone_name: str) -> list[Listing]:
    """Interpret `data-st` in the page timezone. Times are wall-clock on the page."""
    try:
        tz = ZoneInfo(timezone_name)
    except Exception:
        tz = ZoneInfo(MARKET_TZ)
    listings: list[Listing] = []
    for row in rows:
        try:
            start = dt.datetime.strptime(row["start"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=tz)
        except ValueError:
            continue
        stop: dt.datetime | None = None
        raw_duration = row.get("duration") or ""
        if raw_duration.isdigit():
            minutes = int(raw_duration)
            if minutes > 0:
                stop = start + dt.timedelta(minutes=minutes)
        listings.append(
            Listing(
                start=start,
                stop=stop,
                title=row.get("title") or "",
                subtitle=row.get("subtitle") or "",
                desc=row.get("desc") or "",
            )
        )
    listings.sort(key=lambda item: item.start)
    return listings


def listings_to_xmltv(channels: list[tuple[GuideChannel, list[Listing]]]) -> bytes:
    """Serialize channels and programmes as XMLTV bytes."""
    root = et.Element("tv")
    for channel, listings in channels:
        node = et.SubElement(root, "channel", {"id": channel.xmltv_id})
        name = et.SubElement(node, "display-name")
        name.text = channel.name
        seen: set[tuple[str, str]] = set()
        for item in listings:
            key = (item.start.isoformat(), item.title)
            if key in seen:
                continue
            seen.add(key)
            attrib = {
                "start": _xmltv_stamp(item.start),
                "channel": channel.xmltv_id,
            }
            if item.stop is not None:
                attrib["stop"] = _xmltv_stamp(item.stop)
            programme = et.SubElement(root, "programme", attrib)
            title = et.SubElement(programme, "title")
            title.text = item.title
            if item.subtitle:
                subtitle = et.SubElement(programme, "sub-title")
                subtitle.text = item.subtitle
            if item.desc:
                desc = et.SubElement(programme, "desc")
                desc.text = item.desc
    return et.tostring(root, encoding="utf-8", xml_declaration=True)


def _default_fetch(url: str) -> str:
    request = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT, "Accept": "text/html"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8", errors="replace")


def grab_xmltv(
    *,
    days: int = 2,
    lineup: tuple[GuideChannel, ...] = LINEUP,
    fetch=None,
    today: dt.date | None = None,
) -> bytes:
    """Download station pages and return XMLTV for the lineup.

    `fetch` is a test hook `(url) -> html`. `today` is the first listing date
    in America/New_York.
    """
    if days < 1:
        raise ValueError("days must be >= 1")
    getter = fetch or _default_fetch
    start_day = today or dt.datetime.now(ZoneInfo(MARKET_TZ)).date()
    dates = [start_day + dt.timedelta(days=offset) for offset in range(days)]
    grouped: dict[str, list[Listing]] = {channel.xmltv_id: [] for channel in lineup}
    warnings: list[str] = []
    for channel in lineup:
        for day in dates:
            url = f"{BASE_URL}/{channel.site_id}/{day.isoformat()}"
            try:
                html = getter(url)
            except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
                warnings.append(f"{channel.number} {channel.name} {day.isoformat()}: {exc}")
                continue
            timezone_name, rows = parse_station_html(html)
            grouped[channel.xmltv_id].extend(materialize_listings(rows, timezone_name))
        print(
            f"tvpassport {channel.number} {channel.name}: {len(grouped[channel.xmltv_id])} listings",
            file=sys.stderr,
        )
    channels = [(channel, grouped[channel.xmltv_id]) for channel in lineup]
    total = sum(len(items) for _, items in channels)
    if total == 0:
        detail = "; ".join(warnings) or "no programmes"
        raise ValueError(f"TV Passport grab returned no programmes ({detail})")
    if warnings:
        print("tvpassport warnings: " + "; ".join(warnings), file=sys.stderr)
    return listings_to_xmltv(channels)
