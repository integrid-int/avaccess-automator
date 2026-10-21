import base64
import json
from pathlib import Path

import pytest
import yaml

from scripts.avaccess import execute_route_plan as erp

ROOT = Path(__file__).resolve().parents[1]


def test_dry_run_sequences_shef_then_udp(monkeypatch):
    calls = []
    monkeypatch.setattr(
        erp,
        "send_directv_tune",
        lambda **kw: calls.append(("shef", kw["channel"], kw["encoder_id"])),
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
        directv={},
        live=False,
    )
    assert [c[0] for c in calls] == ["shef", "udp", "shef", "udp"]
    assert calls[0][1] == "206"
    assert report["slots"][0]["status"] == "ok"
    assert report["ok"] is True


def test_continues_after_slot_error(monkeypatch):
    def boom_shef(**kw):
        if kw["encoder_id"] == "ENC-01":
            raise RuntimeError("shef failed")
        return None

    monkeypatch.setattr(erp, "send_directv_tune", boom_shef)
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
        directv={},
        live=False,
    )
    assert report["ok"] is False
    assert report["slots"][0]["status"] == "error"
    assert report["slots"][0]["error"] == "shef failed"
    assert report["slots"][0]["message"] == "shef failed"
    assert report["slots"][1]["status"] == "ok"
    assert "error" not in report["slots"][1]
    assert any("shef failed" in e for e in report["errors"])


def test_live_preflight_fails_on_bad_inventory(monkeypatch):
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: None)
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
        erp.execute_plan(plan, inventory=inv, directv={}, live=True)


def _valid_live_inventory() -> dict:
    return {
        "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-AAA"}],
        "receivers": [{"id": "RX-01", "hostname": "IPD935-001"}],
    }


def _one_slot_plan() -> dict:
    return {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "g1", "channelNumber": "206"},
                "tvs": [1],
                "tune": {"channelNumber": "206"},
                "udp": {"txHostname": "IPE935-AAA", "rxHostnames": ["IPD935-001"]},
                "status": "planned",
            }
        ],
        "warnings": [],
    }


def test_live_preflight_fails_when_h25_unmapped(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(kw))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    with pytest.raises(erp.PreflightError) as excinfo:
        erp.execute_plan(
            _one_slot_plan(),
            inventory=_valid_live_inventory(),
            directv={"encoder_to_receiver": {}, "receivers": {}},
            live=True,
        )
    assert any("no DirecTV" in e or "mapped" in e for e in excinfo.value.errors)
    assert calls == []


def test_live_preflight_fails_when_h25_host_empty(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(kw))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    with pytest.raises(erp.PreflightError) as excinfo:
        erp.execute_plan(
            _one_slot_plan(),
            inventory=_valid_live_inventory(),
            directv={
                "encoder_to_receiver": {"ENC-01": "H25-01"},
                "receivers": {"H25-01": {"host": "  "}},
            },
            live=True,
        )
    assert any("empty host" in e for e in excinfo.value.errors)
    assert calls == []


def test_cli_live_unmapped_h25_exit_2(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(kw))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(_one_slot_plan()), encoding="utf-8")
    inv_path = tmp_path / "inv.yaml"
    inv_path.write_text(yaml.safe_dump(_valid_live_inventory()), encoding="utf-8")
    directv_path = tmp_path / "directv.yaml"
    directv_path.write_text(
        "encoder_to_receiver: {}\nreceivers: {}\n",
        encoding="utf-8",
    )

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--directv-config",
            str(directv_path),
            "--plan-file",
            str(plan_path),
            "--live",
        ]
    )
    assert code == 2
    assert calls == []
    report = json.loads(capsys.readouterr().out)
    assert any("no DirecTV" in e or "mapped" in e for e in report["errors"])


def test_live_preflight_fails_on_missing_network(monkeypatch):
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: None)
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
        erp.execute_plan(plan, inventory=inv, directv={}, live=True)
    assert any("broadcast" in e for e in excinfo.value.errors)
    assert any("udp_switch_port" in e for e in excinfo.value.errors)


def test_cli_dry_run_exit_0(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: None)
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
    directv_path = tmp_path / "directv.yaml"
    directv_path.write_text("receivers: {}\nencoder_to_receiver: {}\n")

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--directv-config",
            str(directv_path),
            "--plan-file",
            str(plan_path),
            "--dry-run",
        ]
    )
    assert code == 0
    out = json.loads(capsys.readouterr().out)
    assert out["ok"] is True


def test_cli_plan_b64_live_preflight_exit_2(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: None)
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
    directv_path = tmp_path / "directv.yaml"
    directv_path.write_text("receivers: {}\nencoder_to_receiver: {}\n")
    b64 = base64.b64encode(json.dumps(plan).encode("utf-8")).decode("ascii")

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--directv-config",
            str(directv_path),
            "--plan-b64",
            b64,
            "--live",
        ]
    )
    assert code == 2


def test_dry_run_shef_uses_example_config_without_network():
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
    directv = yaml.safe_load((ROOT / "config" / "directv.example.yaml").read_text())
    report = erp.execute_plan(
        plan,
        inventory={"network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010}},
        directv=directv,
        live=False,
    )
    assert report["ok"] is True
    assert report["slots"][0]["status"] == "ok"


def test_directv_example_exists():
    path = ROOT / "config" / "directv.example.yaml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "encoder_to_receiver" in text
    assert "ENC-01" in text
    assert "H25-01" in text


def _live_directv() -> dict:
    return {
        "encoder_to_receiver": {"ENC-01": "H25-01", "ENC-02": "H25-02"},
        "receivers": {
            "H25-01": {"host": "192.168.10.151"},
            "H25-02": {"host": "192.168.10.152"},
        },
    }


def _slot(*, encoder_id="ENC-01", tune=None, tvs=None, index=1, label="A @ B"):
    return {
        "index": index,
        "encoderId": encoder_id,
        "program": {
            "id": "g1",
            "label": label,
            "channel": "FOX",
            "channelNumber": (tune or {}).get("channelNumber") if isinstance(tune, dict) else None,
        },
        "tvs": tvs or [1],
        "tune": tune,
        "udp": {"txHostname": "IPE935-AAA", "rxHostnames": ["IPD935-001"]},
        "status": "planned",
    }


def test_live_preflight_rejects_empty_tune_without_udp(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw)))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append(("udp", kw)))

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [_slot(tune=None)],
        "warnings": [],
    }
    with pytest.raises(erp.PreflightError) as excinfo:
        erp.execute_plan(
            plan,
            inventory=_valid_live_inventory(),
            directv=_live_directv(),
            live=True,
        )
    assert any("tune" in e.lower() or "channel" in e.lower() for e in excinfo.value.errors)
    assert calls == []


def test_live_preflight_rejects_blank_tune_channel(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append("shef"))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [_slot(tune={"channelNumber": "  "})],
        "warnings": [],
    }
    with pytest.raises(erp.PreflightError):
        erp.execute_plan(
            plan,
            inventory=_valid_live_inventory(),
            directv=_live_directv(),
            live=True,
        )
    assert calls == []


def test_live_mixed_slots_missing_tune_is_preflight_no_udp(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw["encoder_id"])))
    monkeypatch.setattr(
        erp,
        "send_udp_reconnect",
        lambda **kw: calls.append(("udp", kw["tx_hostname"])),
    )
    plan = {
        "mode": "preset_2",
        "commit": "live",
        "slots": [
            _slot(encoder_id="ENC-01", tune={"channelNumber": "206"}, index=1),
            _slot(encoder_id="ENC-02", tune=None, index=2, tvs=[2], label="Open game"),
        ],
        "warnings": [],
    }
    with pytest.raises(erp.PreflightError) as excinfo:
        erp.execute_plan(
            plan,
            inventory=_valid_live_inventory(),
            directv=_live_directv(),
            live=True,
        )
    assert any("ENC-02" in e for e in excinfo.value.errors)
    assert calls == []


def test_live_slot_guard_skips_udp_when_tune_missing_after_preflight(monkeypatch):
    """Defense in depth: a live slot with empty tune must error without UDP."""
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw["encoder_id"])))
    monkeypatch.setattr(
        erp,
        "send_udp_reconnect",
        lambda **kw: calls.append(("udp", kw["tx_hostname"])),
    )
    monkeypatch.setattr(erp, "_missing_tune_errors", lambda plan: [])

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [_slot(tune=None)],
        "warnings": [],
    }
    report = erp.execute_plan(
        plan,
        inventory=_valid_live_inventory(),
        directv=_live_directv(),
        live=True,
    )
    assert report["ok"] is False
    assert report["slots"][0]["status"] == "error"
    assert "tune" in report["slots"][0]["error"].lower() or "channel" in report["slots"][0]["error"].lower()
    assert calls == []


def test_cli_live_empty_tune_exit_2(monkeypatch, tmp_path, capsys):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append(kw))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [_slot(tune=None)],
        "warnings": [],
    }
    plan_path = tmp_path / "plan.json"
    plan_path.write_text(json.dumps(plan), encoding="utf-8")
    inv_path = tmp_path / "inv.yaml"
    inv_path.write_text(yaml.safe_dump(_valid_live_inventory()), encoding="utf-8")
    directv_path = tmp_path / "directv.yaml"
    directv_path.write_text(yaml.safe_dump(_live_directv()), encoding="utf-8")

    code = erp.main(
        [
            "--inventory",
            str(inv_path),
            "--directv-config",
            str(directv_path),
            "--plan-file",
            str(plan_path),
            "--live",
        ]
    )
    assert code == 2
    assert calls == []
    report = json.loads(capsys.readouterr().out)
    assert report["ok"] is False
    assert any("tune" in e.lower() or "channel" in e.lower() for e in report["errors"])


def test_dry_run_empty_tune_does_not_preflight(monkeypatch):
    calls = []
    monkeypatch.setattr(erp, "send_directv_tune", lambda **kw: calls.append("shef"))
    monkeypatch.setattr(erp, "send_udp_reconnect", lambda **kw: calls.append("udp"))

    plan = {
        "mode": "adhoc",
        "commit": "dry_run",
        "slots": [_slot(tune=None)],
        "warnings": [],
    }
    report = erp.execute_plan(
        plan,
        inventory=_valid_live_inventory(),
        directv=_live_directv(),
        live=False,
    )
    assert report["ok"] is True
    assert "shef" not in calls
    assert calls == ["udp"]


def test_itach_example_is_unused_leftover():
    path = ROOT / "config" / "itach.example.yaml"
    assert path.is_file()
    text = path.read_text(encoding="utf-8")
    assert "encoder_to_output" in text
    assert "ENC-01" in text
