from pathlib import Path
from scripts.avaccess.build_guide_epg import build_guide_epg, classify_sport_key
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]


def test_classify_sport_key():
    assert classify_sport_key("NFL Live") == "nfl"
    assert classify_sport_key("College Football: Georgia vs Alabama") == "cfb"
    assert classify_sport_key("NBA: Lakers at Celtics") == "nba"
    assert classify_sport_key("NHL: Bruins at Maple Leafs") == "nhl"
    assert classify_sport_key("SportsCenter") == "other"


def test_build_guide_epg_now_next_for_mapped_channels():
    cfg = {
        "timezone": "UTC",
        "zip_code": "27403",
        "source": {"file": str(ROOT / "tests/fixtures/guide_sample.xmltv"), "compression": "none"},
        "channel_number_map": {"17": ["espn.example"], "7": ["fox.example"]},
        "sports_channel_numbers": ["17"],
        "sports_window_hours": 12,
    }
    now = dt.datetime(2026, 8, 10, 18, 30, tzinfo=dt.timezone.utc)
    out = build_guide_epg(cfg, now=now)
    assert out["zip"] == "27403"
    assert out["channels"]["17"]["now"]["title"] == "SportsCenter"
    assert out["channels"]["17"]["next"]["title"] == "College Football: Georgia vs Alabama"
    assert out["channels"]["7"]["now"]["title"] == "Local News"


def test_build_guide_epg_sports_now_and_upcoming():
    cfg = {
        "timezone": "UTC",
        "zip_code": "27403",
        "source": {"file": str(ROOT / "tests/fixtures/guide_sample.xmltv"), "compression": "none"},
        "channel_number_map": {
            "17": ["espn.example"],
            "16": ["espn2.example"],
        },
        "sports_channel_numbers": ["16", "17"],
        "sports_window_hours": 12,
        "lineup_file": str(ROOT / "config/spectrum_lineup_27403.json"),
    }
    now = dt.datetime(2026, 8, 10, 18, 30, tzinfo=dt.timezone.utc)
    out = build_guide_epg(cfg, now=now)
    sports = out["sports"]
    assert sports["windowHours"] == 12
    now_titles = {i["title"] for i in sports["now"]}
    upcoming_titles = {i["title"] for i in sports["upcoming"]}
    assert "SportsCenter" in now_titles
    assert "NBA: Lakers at Celtics" in now_titles
    assert "College Football: Georgia vs Alabama" in upcoming_titles
    assert "NFL Live" in upcoming_titles
    assert "NHL: Bruins at Maple Leafs" in upcoming_titles
    # Currently airing items must not also appear in upcoming.
    assert now_titles.isdisjoint(upcoming_titles)
    cfb = next(i for i in sports["upcoming"] if "College Football" in i["title"])
    assert cfb["sportKey"] == "cfb"
    assert cfb["channelNumber"] == "17"
    assert cfb["channelName"] == "ESPN"
