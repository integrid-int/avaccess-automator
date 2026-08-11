from scripts.avaccess.pull_schedules_direct import (
    _channel_number,
    classify_category,
    lineup_channels_from_sd,
    prefer_spectrum_lineup,
    password_sha1,
)
import hashlib
import pytest


def test_password_sha1_hashes_plaintext():
    assert password_sha1("secret", None) == hashlib.sha1(b"secret").hexdigest()


def test_password_sha1_prefers_env_hash():
    digest = "a" * 40
    assert password_sha1("ignored", digest) == digest


def test_channel_number_strips_leading_zeros():
    assert _channel_number("016") == "16"
    assert _channel_number("17") == "17"


def test_prefer_spectrum_lineup_picks_x():
    chosen = prefer_spectrum_lineup(
        [
            {
                "lineup": "USA-NC32529-L",
                "name": "Charter Spectrum",
                "transport": "Cable",
            },
            {
                "lineup": "USA-NC32529-X",
                "name": "Charter Spectrum",
                "transport": "Cable",
            },
            {
                "lineup": "USA-NC-ANT",
                "name": "Local Antenna",
                "transport": "Antenna",
            },
        ]
    )
    assert chosen["lineup"] == "USA-NC32529-X"


def test_prefer_spectrum_lineup_errors_when_missing():
    with pytest.raises(Exception, match="No Spectrum"):
        prefer_spectrum_lineup(
            [{"lineup": "X", "name": "DirecTV", "transport": "Satellite"}]
        )


def test_lineup_channels_from_sd_is_number_authority_and_drops_music():
    lineup = {
        "stations": [
            {"stationID": "1", "name": "ESPN", "callsign": "ESPN"},
            {"stationID": "2", "name": "Music Choice Hit List", "callsign": "MC"},
            {"stationID": "3", "name": "WFMY", "callsign": "WFMY"},
        ],
        "map": [
            {"stationID": "1", "channel": "017"},
            {"stationID": "2", "channel": "1901"},
            {"stationID": "3", "channel": "009"},
        ],
    }
    channels = lineup_channels_from_sd(lineup, lineup_id="USA-NC32529-X")
    nums = [c["number"] for c in channels]
    assert nums == ["9", "17"]
    assert channels[1]["name"] == "ESPN"
    assert channels[1]["category"] == "Sports"
    assert classify_category("Fox News") == "News"
