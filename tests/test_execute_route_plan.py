import base64
import json
from pathlib import Path

import pytest

from scripts.avaccess import execute_route_plan as erp

ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_sequences_ir_then_udp(monkeypatch):
    calls = []
    monkeypatch.setattr(
        erp,
        "send_ir_digits",
        lambda **kw: calls.append(("ir", kw["digits"], kw["encoder_id"])),
    )
    monkeypatch.setattr(
        erp,
        "send_udp_reconnect",
        lambda **kw: calls.append(
            ("udp", kw["tx_hostname"], tuple(kw["rx_hostnames"]))
        ),
    )

    plan = {
        "mode": "preset_2",
        "commit": "dry_run",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {
                    "id": "g1",
                    "label": "A",
                    "channel": "FOX",
                    "channelNumber": "206",
                },
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": {"txHostname": "IPE935-AAA", "rxHostnames": ["IPD935-001"]},
                "status": "planned",
            },
            {
                "index": 2,
                "encoderId": "ENC-02",
                "program": {
                    "id": "g2",
                    "label": "B",
                    "channel": "CBS",
                    "channelNumber": "2",
                },
                "tvs": [2],
                "tune": {"channelNumber": "2"},
                "udp": {"txHostname": "IPE935-BBB", "rxHostnames": ["IPD935-002"]},
                "status": "planned",
            },
        ],
        "warnings": [],
    }
    report = erp.execute_plan(
        plan,
        inventory={
            "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010}
        },
        itach={},
        live=False,
    )
    assert [c[0] for c in calls] == ["ir", "udp", "ir", "udp"]
    assert calls[0][1] == "206"
    assert report["slots"][0]["status"] == "ok"
    assert report["ok"] is True


def test_continues_after_slot_error(monkeypatch):
    def boom_ir(**kw):
        if kw["encoder_id"] == "ENC-01":
            raise RuntimeError("ir failed")
        return None

    monkeypatch.setattr(erp, "send_ir_digits", boom_ir)
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: None)

    plan = {
        "mode": "adhoc",
        "commit": "dry_run",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "channelNumber": "206"},
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": {"txHostname": "TX-A", "rxHostnames": ["RX-A"]},
                "status": "planned",
            },
            {
                "index": 2,
                "encoderId": "ENC-02",
                "program": {"id": "g2", "channelNumber": "2"},
                "tvs": [2],
                "tune": {"channelNumber": "2"},
                "udp": {"txHostname": "TX-B", "rxHostnames": ["RX-B"]},
                "status": "planned",
            },
        ],
        "warnings": [],
    }
    report = erp.execute_plan(
        plan,
        inventory={"network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010}},
        itach={},
        live=False,
    )
    assert report["ok"] is False
    assert report["slots"][0]["status"] == "error"
    assert report["slots"][0]["error"] == "ir failed"
    assert report["slots"][0]["message"] == "ir failed"
    assert report["slots"][1]["status"] == "ok"
    assert "error" not in report["slots"][1]
    assert any("ir failed" in e for e in report["errors"])


def test_live_preflight_fails_on_bad_inventory(monkeypatch):
    monkeypatch.setattr(erp, "send_ir_digits", lambda **kw: None)
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: None)

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "channelNumber": "206"},
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": None,
                "status": "planned",
            }
        ],
        "warnings": [],
    }
    inv = {
        "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-REPLACE_ME"}],
        "receivers": [{"id": "RX-01", "hostname": "IPD935-001"}],
    }
    with pytest.raises(erp.PreflightError):
        erp.execute_plan(plan, inventory=inv, itach={}, live=True)


def test_live_preflight_fails_on_missing_network(monkeypatch):
    monkeypatch.setattr(erp, "send_ir_digits", lambda **kw: None)
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: None)

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "channelNumber": "206"},
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": {"txHostname": "TX-A", "rxHostnames": ["RX-A"]},
                "status": "planned",
            }
        ],
        "warnings": [],
    }
    inv = {
        "network": {},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-AAA"}],
        "receivers": [{"id": "RX-01", "hostname": "IPD935-001"}],
    }
    with pytest.raises(erp.PreflightError) as excinfo:
        erp.execute_plan(plan, inventory=inv, itach={}, live=True)
    assert any("broadcast" in e for e in excinfo.value.errors)
    assert any("udp_switch_port" in e for e in excinfo.value.errors)


def test_cli_dry_run_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(erp, "send_ir_digits", lambda **kw: None)
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: None)

    plan = {
        "mode": "adhoc",
        "commit": "dry_run",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "channelNumber": "206"},
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": {"txHostname": "TX-A", "rxHostnames": ["RX-A"]},
                "status": "planned",
            }
        ],
        "warnings": [],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    inv_path = tmp_path / "inv.yaml"
    inv_path.write_text(
        "network:\n  broadcast: 255.255.255.255\n  udp_switch_port: 5010\n"
        "encoders: []\nreceivers: []\n",
        encoding="utf-8",
    )
    itach_path = tmp_path / "itach.yaml"
    itach_path.write_text("controllers: {}\nencoder_to_output: {}\ncodes: {}\n")

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--itach-config",
            str(itach_path),
            "--plan-file",
            str(plan_path),
            "--dry-run",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True


def test_cli_plan_b64_live_preflight_exit_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(erp, "send_ir_digits", lambda **kw: None)
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: None)

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": None,
                "status": "planned",
            }
        ],
        "warnings": [],
    }
    inv_path = tmp_path / "inv.yaml"
    inv_path.write_text(
        "network:\n  broadcast: 255.255.255.255\n  udp_switch_port: 5010\n"
        "encoders:\n  - {id: ENC-01, hostname: IPE935-REPLACE_ME}\n"
        "receivers:\n  - {id: RX-01, hostname: IPD935-001}\n",
        encoding="utf-8",
    )
    itach_path = tmp_path / "itach.yaml"
    itach_path.write_text("controllers: {}\nencoder_to_output: {}\ncodes: {}\n")
    b64 = base64.b64encode(json.dumps(plan).encode("utf-8")).decode("ascii")

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--itach-config",
            str(itach_path),
            "--plan-b64",
            b64,
            "--live",
        ]
    )
    assert code == 2


def test_itach_example_exists():
    path = ROOT / "config" / "itach.example.yaml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "encoder_to_output" in text
    assert "ENC-01" in text
