from pathlib import Path

from scripts.avaccess.inventory_lib import (
    is_inventory_live_ready,
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
    live_ok, live_errors = is_inventory_live_ready(inv)
    assert live_ok is False
    assert any("REPLACE_ME" in e or "hostname" in e.lower() for e in live_errors)


def test_validate_requires_network_broadcast_and_port():
    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "tvs": [1],
            }
        ],
        "warnings": [],
    }
    inv = {
        "network": {"broadcast": "", "udp_switch_port": ""},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-AAA"}],
        "receivers": [{"id": "RX-01", "hostname": "IPD935-001"}],
    }
    ok, errors = validate_inventory_for_plan(inv, plan)
    assert ok is False
    assert any("broadcast" in e for e in errors)
    assert any("udp_switch_port" in e for e in errors)


def test_is_inventory_live_ready_requires_network_fields():
    inv = load_inventory(ROOT / "config" / "inventory.example.yaml")
    # Force hostnames to look real so network is the only failure mode.
    for enc in inv["encoders"]:
        enc["hostname"] = f"IPE935-{enc['id']}"
    for rx in inv["receivers"]:
        rx["hostname"] = f"IPD935-{rx['id']}"
    inv["network"]["broadcast"] = "   "
    del inv["network"]["udp_switch_port"]
    ok, errors = is_inventory_live_ready(inv)
    assert ok is False
    assert any("broadcast" in e for e in errors)
    assert any("udp_switch_port" in e for e in errors)
