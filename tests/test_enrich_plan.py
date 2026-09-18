import copy

import pytest

from scripts.avaccess.enrich_plan import enrich_route_plan

MINI_INV = {
    "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
    "encoders": [
        {"id": "ENC-01", "hostname": "IPE935-AAA", "mac": "AAA"},
        {"id": "ENC-02", "hostname": "IPE935-BBB", "mac": "BBB"},
    ],
    "receivers": [
        {"id": "RX-01", "hostname": "IPD935-001", "mac": "001"},
        {"id": "RX-05", "hostname": "IPD935-005", "mac": "005"},
        {"id": "RX-02", "hostname": "IPD935-002", "mac": "002"},
    ],
}


def _sample_plan():
    return {
        "mode": "adhoc",
        "commit": "dry_run",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-02",
                "program": {
                    "kind": "channel",
                    "id": "ch-espn",
                    "label": "ESPN",
                    "channel": "ESPN",
                    "channelNumber": "206",
                },
                "tvs": [1, 5],
                "tune": None,
                "udp": None,
                "status": "planned",
            }
        ],
        "warnings": [],
    }


def test_enrich_fills_udp_hostnames():
    plan = _sample_plan()
    out = enrich_route_plan(plan, MINI_INV)
    slot = out["slots"][0]
    assert slot["udp"]["txHostname"] == "IPE935-BBB"
    assert slot["udp"]["rxHostnames"] == ["IPD935-001", "IPD935-005"]
    assert slot["tune"]["channelNumber"] == "206"
    # Original plan must not be mutated
    assert plan["slots"][0]["udp"] is None
    assert plan["slots"][0]["tune"] is None


def test_enrich_raises_on_invalid_inventory():
    bad_inv = copy.deepcopy(MINI_INV)
    bad_inv["encoders"][1]["hostname"] = "IPE935-REPLACE_ME"
    with pytest.raises(ValueError, match="REPLACE_ME"):
        enrich_route_plan(_sample_plan(), bad_inv)
