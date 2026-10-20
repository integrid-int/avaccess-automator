"""DirecTV sports-info games JSON -> sports rail with satellite majors."""

import json

import pytest

from scripts.avaccess.directv_sports import (
    DirectvSportsError,
    browser_channel_order,
    fetch_window_via_selenium,
    games_url,
    is_tunable_showing,
    main,
    merge_payloads,
    parse_schedule,
    payloads_from_page_results,
    tunable_showings,
    window_days,
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


_SPORT = {
    "NFL": ("football", "Football", "🏈", 1),
    "NBA": ("basketball", "Basketball", "🏀", 2),
    "MLB": ("baseball", "Baseball", "⚾", 3),
    "NHL": ("hockey", "Hockey", "🏒", 4),
    "WNBA": ("basketball", "Basketball", "🏀", 2),
    "ProGolf": ("golf", "Golf", "⛳", 9),
    "EPL": ("soccer", "Soccer", "⚽", 5),
}


def _game(gid, league, away, home, showings, starts="2026-10-27T00:15:00.000000Z"):
    sport_id, sport_title, emoji, rank = _SPORT.get(league, (league.lower(), league, "", 50))
    return {
        "id": gid,
        "starts_at": starts,
        "sport": {"text_id": sport_id, "title": sport_title, "emoji": emoji, "rank": rank, "show": True},
        "league": {"text_id": league, "title": league, "title_short": league, "rank": 1, "show": True},
        "away_team": {"name": away, "display_name_short": away, "text_id_short": away[:3].upper()},
        "home_team": {"name": home, "display_name_short": home, "text_id_short": home[:3].upper()},
        "showings": showings,
        "betting_odds": {"should": "not copy"},
    }


def test_games_url_matches_the_sports_page_request():
    assert games_url("27403", "2026-10-25") == (
        "https://www.directv.com/sports-info/games?zip=27403&days=2026-10-25&bundles=20"
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
    nhl = by_id["hockey"]["games"][0]
    assert nhl["channelNumber"] == "215"
    assert [item["channelNumber"] for item in nhl["alternates"]] == ["770", "771"]
    mlb = by_id["baseball"]["games"][0]
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
    golf["description"] = "PGA: Butterfield Bermuda Championship, Final Round"
    wnba = _game(2, "WNBA", "Aces", "Liberty", [peacock, usa], starts="2026-10-26T23:00:00Z")
    hidden = _game(3, "NFL", "Hidden", "Hidden", [usa])
    hidden["league"]["show"] = False
    schedule = parse_schedule({"games": [golf, wnba, hidden]}, generated_at=_stamp())
    by_id = {sport["id"]: sport for sport in schedule["sports"]}
    assert [sport["id"] for sport in schedule["sports"]] == ["basketball", "golf"]
    assert by_id["basketball"]["games"][0]["channelNumber"] == "242"
    assert by_id["basketball"]["leagues"][0]["id"] == "wnba"
    assert by_id["golf"]["games"][0]["away"].startswith("PGA:")
    assert by_id["golf"]["games"][0]["home"] == ""


def test_window_days_is_the_eastern_calendar():
    import datetime as dt

    assert window_days(3, today=dt.date(2026, 10, 25)) == [
        "2026-10-25",
        "2026-10-26",
        "2026-10-27",
    ]


def test_page_results_keep_each_day_and_reject_a_refusal():
    body = json.dumps({"games": [_game(1214005, "NFL", "49ers", "Falcons", [])]})
    payloads = payloads_from_page_results(
        [{"day": "2026-10-25", "status": 200, "body": body}]
    )
    assert payloads[0]["games"][0]["id"] == 1214005
    with pytest.raises(DirectvSportsError, match="refused"):
        payloads_from_page_results(
            [{"day": "2026-10-25", "status": 403, "body": "Access Denied"}]
        )


def test_espn_logo_aliases_and_pulled_days():
    game = _game(1214005, "NFL", "49ers", "Falcons", [])
    game["away_team"]["text_id_short"] = "SFO"
    game["home_team"]["text_id_short"] = "ATL"
    schedule = parse_schedule(
        {"games": [game]},
        generated_at=_stamp(),
        days=["2026-10-25", "2026-10-26"],
    )
    rail = schedule["sports"][0]["games"][0]
    assert rail["awayLogo"].endswith("/nfl/500/sf.png")
    assert rail["homeLogo"].endswith("/nfl/500/atl.png")
    assert schedule["days"] == ["2026-10-25", "2026-10-26"]
    assert browser_channel_order("msedge") == ["msedge"]


def test_pull_writes_the_window_and_a_refusal_keeps_the_old_file(tmp_path, monkeypatch):
    out = tmp_path / "sports_schedule.json"
    out.write_text("{}\n", encoding="utf-8")

    def refused(*_args, **_kwargs):
        raise DirectvSportsError("DirecTV refused the browser pull")

    monkeypatch.setattr("scripts.avaccess.directv_sports.fetch_window_in_browser", refused)
    assert main(["--pull", "--ahead", "2", "--out", str(out)]) == 1
    assert out.read_text(encoding="utf-8") == "{}\n"

    def fetched(_zip, days, **_kwargs):
        assert days == ["2026-10-26"]
        return [{"games": [_game(9, "NBA", "Mavericks", "Heat", [_showing(_channel(216, callsign="NBA"))])]}]

    monkeypatch.setattr("scripts.avaccess.directv_sports.fetch_window_in_browser", fetched)
    assert main(["--pull", "--days", "2026-10-26", "--out", str(out)]) == 0
    written = json.loads(out.read_text(encoding="utf-8"))
    assert written["days"] == ["2026-10-26"]
    assert written["sports"][0]["games"][0]["channelNumber"] == "216"


def test_college_basketball_sits_under_basketball_with_the_nba():
    college = _game(1228045, "NCAAB", "Tennessee", "Duke", [_showing(_channel(612, callsign="ACCN"))])
    college["sport"] = {"text_id": "basketball", "title": "Basketball", "emoji": "🏀", "rank": 2, "show": True}
    college["league"]["title"] = "College Basketball (M)"
    college["league"]["title_short"] = "NCAA Basketball (M)"
    college["league"]["rank"] = 6
    nba = _game(9, "NBA", "Mavericks", "Heat", [_showing(_channel(216, callsign="NBA"))])
    schedule = parse_schedule({"games": [college, nba]}, generated_at=_stamp())
    basketball = schedule["sports"][0]
    assert basketball["id"] == "basketball"
    assert [league["id"] for league in basketball["leagues"]] == ["nba", "ncaab"]
    assert basketball["leagues"][1]["chipTitle"] == "NCAA Basketball (M)"
    by_league = {game["leagueId"]: game for game in basketball["games"]}
    assert by_league["ncaab"]["channelNumber"] == "612"
    assert by_league["nba"]["channelNumber"] == "216"


def test_college_football_sits_under_football_with_the_nfl():
    college = _game(1228556, "NCAAF", "Pittsburgh", "Miami", [_showing(_channel(206, callsign="ESPN"))])
    college["sport"] = {"text_id": "football", "title": "Football", "emoji": "🏈", "rank": 1, "show": True}
    college["league"]["title"] = "College Football"
    college["league"]["title_short"] = "NCAA Football"
    college["league"]["rank"] = 6
    nfl = _game(1214005, "NFL", "49ers", "Falcons", [_showing(_channel(9558, callsign="NFL"))])
    schedule = parse_schedule({"games": [college, nfl]}, generated_at=_stamp())
    football = schedule["sports"][0]
    assert football["id"] == "football"
    assert [league["id"] for league in football["leagues"]] == ["nfl", "ncaaf"]
    assert football["leagues"][1]["chipTitle"] == "NCAA Football"
    by_league = {game["leagueId"]: game for game in football["games"]}
    assert by_league["ncaaf"]["channelNumber"] == "206"
    assert by_league["nfl"]["channelNumber"] == "9558"


def test_commercial_plan_drops_residential_packages_and_keeps_locals():
    sunday = _showing(
        _channel(
            9558,
            callsign="NFL",
            commercial_only=True,
            packages=[
                {
                    "title": "NFL SUNDAY TICKET",
                    "commercial": True,
                    "commercial_public": True,
                    "residential": False,
                }
            ],
        )
    )
    local = _showing(
        _channel(
            8,
            callsign="WGHP",
            packages=[
                {
                    "title": "MySports",
                    "commercial": False,
                    "commercial_public": False,
                    "residential": True,
                }
            ],
        )
    )
    sports_pack = _showing(
        _channel(
            464,
            callsign="TUDN",
            packages=[
                {
                    "title": "SPORTS PACK",
                    "commercial": False,
                    "commercial_public": False,
                    "residential": True,
                }
            ],
        )
    )
    business = _showing(
        _channel(
            242,
            callsign="USA",
            packages=[
                {"title": "ULTIMATE", "commercial": False, "commercial_public": False, "residential": True},
                {
                    "title": "COMMERCIAL CHOICE",
                    "commercial": True,
                    "commercial_public": True,
                    "residential": False,
                },
            ],
        )
    )
    private_office = _showing(
        _channel(
            218,
            callsign="GOLF",
            packages=[
                {
                    "title": "SPORTS CHOICE",
                    "commercial": True,
                    "commercial_public": False,
                    "commercial_private": True,
                }
            ],
        )
    )
    assert is_tunable_showing(sunday) is True
    assert is_tunable_showing(local) is True
    assert is_tunable_showing(sports_pack) is False
    assert is_tunable_showing(business) is True
    assert is_tunable_showing(private_office) is False
    game = _game(1, "NFL", "49ers", "Falcons", [sports_pack, private_office, sunday])
    showings = tunable_showings(game)
    assert [item["channelNumber"] for item in showings] == ["9558"]
    assert "packages" not in showings[0]


def test_selenium_pull_uses_the_addon_browser_without_cookies():
    from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
    import threading

    seen = []

    class Handler(BaseHTTPRequestHandler):
        def _read(self):
            length = int(self.headers.get("Content-Length") or 0)
            raw = self.rfile.read(length) if length else b""
            body = json.loads(raw.decode() or "{}") if raw else None
            seen.append((self.command, self.path, self.headers.get("Cookie"), body))
            return body

        def _send(self, payload, status=200):
            data = json.dumps(payload).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_POST(self):
            body = self._read()
            if self.path == "/session":
                self._send({"value": {"sessionId": "abc"}})
                return
            if self.path == "/session/abc/execute/async":
                self._send(
                    {
                        "value": [
                            {
                                "day": "2026-10-25",
                                "status": 200,
                                "body": json.dumps(
                                    {
                                        "games": [
                                            _game(
                                                1214005,
                                                "NFL",
                                                "49ers",
                                                "Falcons",
                                                [
                                                    _showing(
                                                        _channel(
                                                            9558,
                                                            callsign="NFL",
                                                            packages=[
                                                                {
                                                                    "title": "NFL SUNDAY TICKET",
                                                                    "commercial": True,
                                                                }
                                                            ],
                                                        )
                                                    )
                                                ],
                                            )
                                        ]
                                    }
                                ),
                            }
                        ]
                    }
                )
                return
            self._send({"value": None})

        def do_DELETE(self):
            seen.append((self.command, self.path, self.headers.get("Cookie"), None))
            self._send({"value": None})

        def log_message(self, *_args):
            return

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        payloads = fetch_window_via_selenium(
            f"http://127.0.0.1:{server.server_address[1]}",
            "27403",
            ["2026-10-25"],
            page_timeout_s=5,
            script_timeout_s=5,
        )
    finally:
        server.shutdown()
    assert payloads[0]["games"][0]["id"] == 1214005
    assert any(item[1] == "/session/abc/url" for item in seen)
    assert all(item[2] is None for item in seen)
    script = next(item[3]["script"] for item in seen if item[1].endswith("/execute/async"))
    assert "27403" not in script
    posted = next(item[3] for item in seen if item[1].endswith("/execute/async"))
    assert posted["args"] == [{"zip": "27403", "days": ["2026-10-25"], "bundles": 20}]
    assert "bundles=" in script
    assert not any("Cookie" in json.dumps(item[3]) for item in seen if item[3])


def test_merge_payloads_keeps_the_copy_with_showings():
    thin = _game(5, "NBA", "Mavericks", "Heat", [])
    full = _game(5, "NBA", "Mavericks", "Heat", [_showing(_channel(216, callsign="NBA"))])
    merged = merge_payloads([{"games": [thin]}, {"games": [full]}])
    assert len(merged["games"]) == 1
    assert tunable_showings(merged["games"][0])[0]["channelNumber"] == "216"


def _stamp():
    import datetime as dt

    return dt.datetime(2026, 10, 20, 19, 55, tzinfo=dt.timezone.utc)
