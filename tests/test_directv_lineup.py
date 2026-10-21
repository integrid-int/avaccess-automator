import unittest
from pathlib import Path

from scripts.avaccess.directv_lineup import (
    exclude_reason,
    guide_channels_from_rows,
    parse_lineup_html,
)

FIXTURE = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "directv_lineup_sample.html"


class DirectvLineupTests(unittest.TestCase):
    def test_exclude_reason_drops_music_ppv_barkers_and_keeps_the_package(self):
        assert exclude_reason("Music Choice Pop") == "music"
        assert exclude_reason("Hot Choice PPV") == "ppv"
        assert exclude_reason("DirecTV Sports 121") == "ppv"
        assert exclude_reason("Audience Network") == "barker"
        assert exclude_reason("ESPN On Demand") == "not-in-package"
        assert exclude_reason("HBO - Eastern Feed") is None
        assert exclude_reason("QVC") is None
        assert exclude_reason("Playboy HD") is None
        assert exclude_reason("MTV USA - Eastern Feed") is None
        assert exclude_reason("Adult Swim East") is None
        assert exclude_reason("ESPN") is None
        assert exclude_reason("AMC") is None

    def test_parse_lineup_keeps_locals_sports_and_sunday_ticket(self):
        rows = parse_lineup_html(FIXTURE.read_text(encoding="utf-8"))
        channels, excluded = guide_channels_from_rows(rows)
        by_number = {channel["number"]: channel for channel in channels}
        assert set(by_number) == {"2", "70", "206", "331", "501", "576", "700", "9554"}
        assert by_number["206"]["name"] == "ESPN"
        assert by_number["206"]["category"] == "Sports"
        assert by_number["2"]["category"] == "Local"
        assert by_number["501"]["name"].startswith("HBO")
        assert by_number["9554"]["name"] == "NFL Sunday Ticket 705"
        assert "9547" not in by_number
        assert "801" not in by_number
        assert excluded["music"] == 1
        assert excluded["ppv"] == 2
        assert excluded["not-in-package"] == 2
