import base64
import json
from pathlib import Path

from scripts.avaccess.save_tv_sets import normalize


def test_normalize_keeps_named_sets_and_drops_junk(tmp_path: Path):
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
