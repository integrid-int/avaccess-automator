from scripts.avaccess.pull_sports_schedule import parse_scoreboard


def test_parse_scoreboard_extracts_home_away_and_broadcasts():
    sample = {
        "events": [
            {
                "id": "1",
                "name": "Away at Home",
                "date": "2026-08-10T00:00:00Z",
                "competitions": [
                    {
                        "competitors": [
                            {"homeAway": "away", "team": {"displayName": "Away"}},
                            {"homeAway": "home", "team": {"displayName": "Home"}},
                        ],
                        "broadcasts": [{"names": ["ESPN", "ESPN2"]}],
                        "geoBroadcasts": [
                            {
                                "type": {"shortName": "TV"},
                                "media": {"shortName": "MLB Network"},
                            }
                        ],
                    }
                ],
                "status": {"type": {"name": "STATUS_SCHEDULED"}},
            }
        ]
    }
    games = parse_scoreboard(sample, "mlb")
    assert len(games) == 1
    assert games[0]["away"] == "Away"
    assert games[0]["home"] == "Home"
    assert games[0]["sportKey"] == "mlb"
    assert games[0]["broadcasts"] == ["ESPN", "ESPN2", "MLB Network"]
