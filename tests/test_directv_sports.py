"""DirecTV sports-info games JSON -> sports rail with satellite majors."""

from scripts.avaccess.directv_sports import (
    games_url,
    is_tunable_showing,
    merge_payloads,
    parse_schedule,
    tunable_showings,
)


def _channel(major, **extra):
    channel = {
        "number_major": major,
        "number_display": str(major),
        "callsign_display": extra.pop("callsign", "NET"),
        "title_display": extra.pop("title", "Net"),
        "title_pgws": extra.pop("title_pgws", "Net HD"),
        "is_sat": True,
        "nondtv": 0,
        "residential_only": False,
        "commercial_only": False,
        "ppv": False,
    }
    channel.update(extra)
    return channel


def _showing(channel, **extra):
    showing = {"is_sat": True, "channel": channel}
    showing.update(extra)
    return showing


def _game(gid, league, away, home, showings, starts="2026-10-27T00:15:00.000000Z"):
    return {
        "id": gid,
        "starts_at": starts,
        "league": {"text_id": league},
        "away_team": {"name": away, "display_name_short": away, "text_id_short": away[:3].upper()},
        "home_team": {"name": home, "display_name_short": home, "text_id_short": home[:3].upper()},
        "showings": showings,
        "betting_odds": {"should": "not copy"},
    }


def test_games_url_matches_the_sports_page_request():
    assert games_url("27403", "2026-10-25") == (
        "https://www.directv.com/sports-info/games?zip=27403&days=2026-10-25"
    )


def test_cowboys_at_eagles_prefers_local_abc_and_drops_placeholders():
    game = _game(
        1214029,
        "NFL",
        "Cowboys",
        "Eagles",
        [
            _showing(_channel(206, callsign="ESPN", title="ESPN")),
            _showing(_channel(30000, callsign="ABC", title="ABC", number_display="ABC")),
            _showing(_channel(45, callsign="WXLV", title="ABC TELEVISION S(WXLV)")),
            _showing(_channel(212, callsign="NFL", title="NFL Network")),
            _showing(
                _channel(
                    9,
                    callsign="WSOC",
                    title_pgws="Greensboro WSOC 9 ABC (Virtual)",
                )
            ),
            _showing(
                _channel(
                    11,
                    callsign="WTVD",
                    title_display="Greensboro, NC WTVD ABC (Virt)",
                    title_pgws="none",
                )
            ),
            _showing(_channel(209, callsign="ESPN2", title="ESPN2")),
        ],
    )
    showings = tunable_showings(game)
    assert [item["channelNumber"] for item in showings] == ["45", "206", "209", "212"]
    schedule = parse_schedule({"games": [game]}, generated_at=_stamp())
    rail = schedule["sports"][0]["games"][0]
    assert rail["id"] == "nfl-1214029"
    assert rail["away"] == "Cowboys"
    assert rail["home"] == "Eagles"
    assert rail["channel"] == "45 WXLV"
    assert rail["channelNumber"] == "45"
    assert rail["tipoff"] == "Mon 8:15 PM"
    assert "betting_odds" not in rail
    assert [item["channelNumber"] for item in rail["alternates"]] == ["206", "209", "212"]
    assert rail["alternates"][-1]["channel"] == "212 NFL Network"


def test_national_net_beats_center_ice_and_empty_showings_stay_untunable():
    kings = _game(
        1225395,
        "NHL",
        "Kings",
        "Rangers",
        [
            _showing(_channel(215, callsign="NHLN")),
            _showing(_channel(771, callsign="NHL CENTER ICE")),
            _showing(_channel(770, callsign="NHL CENTER ICE")),
        ],
        starts="2026-10-28T00:00:00Z",
    )
    pending = _game(1229478, "MLB", "Brewers", "Rays", [], starts="2026-10-27T00:00:00Z")
    schedule = parse_schedule({"games": [kings, pending]}, generated_at=_stamp())
    by_id = {sport["id"]: sport for sport in schedule["sports"]}
    nhl = by_id["nhl"]["games"][0]
    assert nhl["channelNumber"] == "215"
    assert [item["channelNumber"] for item in nhl["alternates"]] == ["770", "771"]
    mlb = by_id["mlb"]["games"][0]
    assert mlb["channelNumber"] is None
    assert mlb["channel"] == "No channel"


def test_apps_streaming_and_other_leagues_are_not_tune_targets():
    peacock = _showing(
        _channel(40005, callsign="PEAC", number_display="PEAC", residential_only=True),
        is_sat=False,
    )
    unlimited = _showing(
        _channel(40015, callsign="ESPN Unltd", number_display="ESPN Unltd", residential_only=True, is_sat=False),
        is_sat=False,
    )
    us_open_stream = _showing(_channel(903, callsign="USO", is_sat=False))
    usa = _showing(_channel(242, callsign="USA"))
    assert is_tunable_showing(peacock) is False
    assert is_tunable_showing(unlimited) is False
    assert is_tunable_showing(us_open_stream) is False
    assert is_tunable_showing(usa) is True
    golf = _game(1, "ProGolf", "TBD", "TBD", [usa])
    wnba = _game(2, "WNBA", "Aces", "Liberty", [peacock, usa], starts="2026-10-26T23:00:00Z")
    schedule = parse_schedule({"games": [golf, wnba]}, generated_at=_stamp())
    assert [sport["id"] for sport in schedule["sports"]] == ["wnba"]
    assert schedule["sports"][0]["games"][0]["channelNumber"] == "242"


def test_merge_payloads_keeps_the_copy_with_showings():
    thin = _game(5, "NBA", "Mavericks", "Heat", [])
    full = _game(5, "NBA", "Mavericks", "Heat", [_showing(_channel(216, callsign="NBA"))])
    merged = merge_payloads([{"games": [thin]}, {"games": [full]}])
    assert len(merged["games"]) == 1
    assert tunable_showings(merged["games"][0])[0]["channelNumber"] == "216"


def _stamp():
    import datetime as dt

    return dt.datetime(2026, 10, 20, 19, 55, tzinfo=dt.timezone.utc)
