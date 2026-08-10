from pathlib import Path
from scripts.avaccess.build_guide_epg import build_guide_epg
import datetime as dt

ROOT = Path(__file__).resolve().parents[1]


def test_build_guide_epg_now_next_for_mapped_channels():
    cfg = {
        "timezone": "UTC",
        "zip_code": "27403",
        "source": {"file": str(ROOT / "tests/fixtures/guide_sample.xmltv"), "compression": "none"},
        "channel_number_map": {"206": ["espn.example"], "4": ["fox.example"]},
    }
    now = dt.datetime(2026, 8, 10, 18, 30, tzinfo=dt.timezone.utc)
    out = build_guide_epg(cfg, now=now)
    assert out["zip"] == "27403"
    assert out["channels"]["206"]["now"]["title"] == "SportsCenter"
    assert out["channels"]["206"]["next"]["title"] == "NFL Live"
    assert out["channels"]["4"]["now"]["title"] == "Local News"
