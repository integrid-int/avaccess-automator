"""TV Passport grabber: parse station HTML and map it onto DirecTV majors."""

from __future__ import annotations

import datetime as dt
import re
import tempfile
import unittest
from pathlib import Path

import yaml

from scripts.avaccess.build_guide_epg import build_guide_epg
from scripts.avaccess.tvpassport import (
    LINEUP,
    GuideChannel,
    grab_xmltv,
    materialize_listings,
    parse_station_html,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests" / "fixtures" / "tvpassport_station.html"


class TvpassportTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def test_parse_station_html_uses_page_timezone_and_movie_title(self):
        timezone_name, rows = parse_station_html(FIXTURE.read_text(encoding="utf-8"))
        assert timezone_name == "America/Los_Angeles"
        assert [row["title"] for row in rows] == ["SportsCenter", "NFL Live", "Hoosiers"]
        listings = materialize_listings(rows, timezone_name)
        assert listings[0].start.tzinfo is not None
        assert listings[0].start.utcoffset() == dt.timedelta(hours=-7)
        assert listings[0].desc == "Highlights & scores."
        assert listings[1].subtitle == "Week 6"

    def test_grab_xmltv_builds_now_next_for_a_guide_channel(self):
        html = FIXTURE.read_text(encoding="utf-8")
        seen: list[str] = []

        def fetch(url: str) -> str:
            seen.append(url)
            return html

        lineup = (GuideChannel("206", "ESPN", "espn-hd/3036", "ESPN.us@HD"),)
        xml = grab_xmltv(days=1, lineup=lineup, fetch=fetch, today=dt.date(2026, 10, 20))
        assert seen == ["https://www.tvpassport.com/tv-listings/stations/espn-hd/3036/2026-10-20"]
        xml_path = self.tmp_path / "guide.xmltv"
        xml_path.write_bytes(xml)
        now = dt.datetime(2026, 10, 20, 10, 30, tzinfo=dt.timezone(dt.timedelta(hours=-7)))
        out = build_guide_epg(
            {
                "timezone": "America/Los_Angeles",
                "zip_code": "27403",
                "source": {"file": str(xml_path), "compression": "none"},
                "channel_number_map": {"206": ["ESPN.us@HD"]},
            },
            now=now,
        )
        assert out["channels"]["206"]["now"]["title"] == "SportsCenter"
        assert out["channels"]["206"]["next"]["title"] == "NFL Live"

    def test_lineup_matches_guide_config_and_panel_channels(self):
        cfg = yaml.safe_load((ROOT / "config" / "guide_epg.yaml").read_text(encoding="utf-8"))
        assert cfg["grabber"]["kind"] == "tvpassport"
        mapping = {str(number): ids for number, ids in cfg["channel_number_map"].items()}
        assert [channel.number for channel in LINEUP] == list(mapping)
        for channel in LINEUP:
            assert mapping[channel.number] == [channel.xmltv_id]
        js = (ROOT / "homeassistant" / "config" / "www" / "panels" / "panel-data.js").read_text(
            encoding="utf-8"
        )
        numbers = re.findall(r'number: "(\d+)"', js)
        assert numbers == [channel.number for channel in LINEUP]
