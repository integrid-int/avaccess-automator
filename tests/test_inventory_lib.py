from pathlib import Path

from scripts.avaccess.inventory_lib import (
    striped_rx_ids,
    tv_to_rx_id,
    validate_inventory_for_plan,
    load_inventory,
)

ROOT = Path(__file__).resolve().parents[1]


def test_striped_rx_ids_match_track_a_formula():
    assert striped_rx_ids(4, 1) == [
        "RX-01", "RX-05", "RX-09", "RX-13", "RX-17", "RX-21", "RX-25", "RX-29", "RX-33"
    ]
    assert striped_rx_ids(4, 4)[-1] == "RX-32"


def test_tv_to_rx_id_zero_pads():
    assert tv_to_rx_id(1) == "RX-01"
    assert tv_to_rx_id(35) == "RX-35"


def test_example_inventory_not_live_ready():
    inv = load_inventory(ROOT / "config" / "inventory.example.yaml")
    plan = {
        "mode": "preset_2",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "label": "A @ B", "channel": "FOX", "channelNumber": "206"},
                "tvs": [1, 5, 9],
            }
        ],
        "warnings": [],
    }
    ok, errors = validate_inventory_for_plan(inv, plan)
    assert ok is False
    assert any("REPLACE_ME" in e or "hostname" in e.lower() for e in errors)
