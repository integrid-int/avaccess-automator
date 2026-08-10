from pathlib import Path

import pytest

from scripts.avaccess.pull_spectrum_lineup import (
    build_lineup_payload,
    filter_lineup,
    parse_tvchannelsguide_markdown,
    validate_lineup,
)

ROOT = Path(__file__).resolve().parents[1]
FIXTURE = ROOT / "tests/fixtures/spectrum_greensboro_tvchannelsguide.md"


def test_parse_and_filter_platinum_drops_music():
    raw = parse_tvchannelsguide_markdown(FIXTURE.read_text(encoding="utf-8"))
    assert len(raw) == 368
    kept = filter_lineup(raw, exclude_music=True)
    assert len(kept) >= 100
    assert all(not c["music"] for c in kept)
    assert all(c["id"] == f"ch-{c['number']}" for c in kept)
    assert not any("music choice" in c["name"].lower() for c in kept)
    espn = next(c for c in kept if c["name"] == "ESPN")
    assert espn["number"] == "17"
    assert espn["category"] == "Sports"
    wfmy = next(c for c in kept if "wfmy" in c["name"].lower())
    assert wfmy["number"] == "9"


def test_validate_lineup_rejects_tiny():
    with pytest.raises(ValueError, match="too small"):
        validate_lineup([{"name": "ESPN", "number": "17", "category": "Sports", "id": "ch-17", "music": False}])


def test_build_payload_package_gold():
    raw = parse_tvchannelsguide_markdown(FIXTURE.read_text(encoding="utf-8"))
    kept = filter_lineup(raw)
    payload = build_lineup_payload(kept, source="fixture")
    assert payload["zip"] == "27403"
    assert payload["package"] == "gold"
    assert payload["packageColumn"] == "TV Platinum"
    assert len(payload["channels"]) == len(kept)
