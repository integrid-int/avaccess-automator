import base64
import json
import tempfile
import unittest
from pathlib import Path

from scripts.avaccess.save_tv_sets import normalize


class SaveTvSetsTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def test_normalize_keeps_named_sets_and_drops_junk(self):
        document = normalize(
            {
                "source": "tv-sets",
                "sets": [
                    {"id": "set-patio", "name": "Patio", "tvs": [10, 8, 8, 9, 40]},
                    {"id": "set-bad", "name": "  ", "tvs": [1]},
                    {"id": "set-dup", "name": "patio", "tvs": [1]},
                    {"id": "set-bar", "name": "Bar", "tvs": ["1", "2"]},
                ],
            }
        )
        assert document["source"] == "tv-sets"
        assert document["sets"] == [
            {"id": "set-patio", "name": "Patio", "tvs": [8, 9, 10]},
            {"id": "set-bar", "name": "Bar", "tvs": [1, 2]},
        ]
        raw = base64.b64encode(json.dumps(document).encode()).decode()
        assert raw
