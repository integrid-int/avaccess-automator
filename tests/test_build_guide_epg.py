from pathlib import Path
from scripts.avaccess.build_guide_epg import (
    auto_map_xmltv_ids,
    build_guide_epg,
    classify_sport_key,
    map_xmltv_ids_by_number,
    match_broadcast_to_channel,
    match_schedule_to_epg,
    normalize_channel_name,
)
import datetime as dt
import json
import shutil

ROOT = Path(__file__).resolve().parents[1]


def test_classify_sport_key():
    assert classify_sport_key("NFL Live") == "nfl"
    assert classify_sport_key("College Football: Georgia vs Alabama") == "cfb"
    assert classify_sport_key("NBA: Lakers at Celtics") == "nba"
    assert classify_sport_key("NHL: Bruins at Maple Leafs") == "nhl"
    assert classify_sport_key("MLB: Yankees at Red Sox") == "mlb"
    assert classify_sport_key("WNBA: Aces at Liberty") == "wnba"
    assert classify_sport_key("SportsCenter") == "other"


def test_auto_map_prefers_channel_number_from_xmltv():
    lineup = [
        {"number": "17", "name": "ESPN Wrong Label"},
        {"number": "33", "name": "CNN"},
        {"number": "999", "name": "Unknown Net"},
    ]
    xmltv = {
        "espn.example": ["17 ESPN", "ESPN", "17"],
        "cnn.example": ["CNN", "33"],
        "other.example": ["Something Else"],
    }
    resolved = auto_map_xmltv_ids(lineup, xmltv, {})
    assert resolved["17"] == ["espn.example"]
    assert resolved["33"] == ["cnn.example"]
    assert resolved["999"] == []
    assert map_xmltv_ids_by_number(xmltv)["17"] == ["espn.example"]


def test_normalize_channel_name_strips_hd_suffix():
    assert normalize_channel_name("ESPN HD") == normalize_channel_name("ESPN")


def test_build_guide_epg_now_next_and_auto_map_lineup():
    # Ensure schedule fixture exists for config symlink consumers.
    sched = ROOT / "config/sports_schedule.json"
    if not sched.exists():
        shutil.copy(ROOT / "tests/fixtures/sports_schedule_sample.json", sched)

    cfg = {
        "timezone": "UTC",
        "zip_code": "27403",
        "source": {"file": str(ROOT / "tests/fixtures/guide_sample.xmltv"), "compression": "none"},
        "channel_number_map": {"17": ["espn.example"]},
        "lineup_file": str(ROOT / "config/spectrum_lineup_27403.json"),
        "sports_schedule_file": str(ROOT / "tests/fixtures/sports_schedule_sample.json"),
        "sports_window_hours": 12,
    }
    now = dt.datetime(2026, 8, 10, 18, 30, tzinfo=dt.timezone.utc)
    out = build_guide_epg(cfg, now=now)
    assert out["zip"] == "27403"
    assert out["channels"]["17"]["now"]["title"] == "SportsCenter"
    # Auto-mapped from lineup name "CNN" / "wfmy" etc.
    assert out["channels"]["9"]["now"]["title"] == "WFMY Local News"
    assert out["mappedChannelCount"] >= 8
    sports = out["sports"]
    assert any("Lakers" in i["title"] for i in sports["now"])
    assert "schedule" in sports
    mlb = next(i for i in sports["schedule"] if i["id"] == "sched-mlb-1")
    assert mlb["matched"] is True
    assert mlb["channelNumber"] == "306"
    assert mlb["matchVia"] == "broadcast"
    wnba = next(i for i in sports["schedule"] if i["sportKey"] == "wnba")
    assert wnba["matched"] is True
    assert wnba["channelNumber"] == "300"  # prefer HD ESPN dial


def test_match_broadcast_to_channel_prefers_sports_hd():
    lineup = [
        {"number": "17", "name": "ESPN", "category": "Sports"},
        {"number": "300", "name": "ESPN", "category": "Sports"},
        {"number": "40", "name": "Fox News Channel", "category": "News"},
        {"number": "400", "name": "FS1", "category": "Sports"},
    ]
    hit = match_broadcast_to_channel(["ESPN"], lineup)
    assert hit["channelNumber"] == "300"
    fs1 = match_broadcast_to_channel(["FS1"], lineup)
    assert fs1["channelNumber"] == "400"
    # Do not map bare FOX onto Fox News.
    assert match_broadcast_to_channel(["FOX"], lineup) is None


def test_match_schedule_to_epg_team_names():
    sports = {
        "now": [],
        "upcoming": [
            {
                "channelNumber": "306",
                "channelName": "MLB Network",
                "title": "MLB: New York Yankees at Boston Red Sox",
                "start": "2026-08-10T22:00:00+00:00",
                "end": "2026-08-11T01:00:00+00:00",
            }
        ],
    }
    games = [
        {
            "id": "sched-mlb-1",
            "sportKey": "mlb",
            "away": "New York Yankees",
            "home": "Boston Red Sox",
            "title": "Yankees at Red Sox",
            "start": "2026-08-10T23:05:00+00:00",
        }
    ]
    matched = match_schedule_to_epg(games, sports)
    assert matched[0]["matched"] is True
    assert matched[0]["channelNumber"] == "306"
