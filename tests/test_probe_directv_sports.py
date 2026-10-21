import unittest

from scripts.avaccess.probe_directv_sports import (
    embedded_json,
    extract_script_srcs,
    text_hits,
    walk_events,
)


class ProbeDirectvSportsTests(unittest.TestCase):
    def test_extract_script_srcs_keeps_page_scripts(self):
        html = '<html><script src="/sports-info/app.js"></script><script src="/other.js"></script>'
        assert extract_script_srcs(html) == ["/sports-info/app.js", "/other.js"]

    def test_text_hits_notice_sunday_ticket_slots(self):
        hits = text_hits("NFL Sunday Ticket ch 9554 and 9555. Local Programming.")
        assert hits["sundayTicket"] == 1
        assert hits["localProgramming"] == 1
        assert hits["slots9550"] == ["9554", "9555"]

    def test_embedded_json_reads_a_schedule_blob(self):
        html = '<script type="application/json">{"events":[{"title":"NFL Football","channel":"206"}]}</script>'
        rows = []
        for blob in embedded_json(html):
            rows.extend(walk_events(blob))
        assert rows == [{"channel": "206", "title": "NFL Football"}]

    def test_walk_events_reads_a_game_and_its_channel(self):
        payload = {
            "events": [
                {
                    "awayTeam": {"name": "49ers"},
                    "homeTeam": {"name": "Falcons"},
                    "channelNumber": "9554",
                    "title": "NFL Football",
                },
                {"title": "First Take"},
            ]
        }
        rows = walk_events(payload)
        assert rows == [
            {
                "channel": "9554",
                "title": "NFL Football",
                "teams": "49ers at Falcons",
            }
        ]
