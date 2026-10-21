"""WP-C: live executor rejects empty/missing tune without UDP (unittest)."""

from __future__ import annotations

import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.avaccess import execute_route_plan as erp


def _live_inventory() -> dict:
    return {
        "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-AAA"}],
        "receivers": [{"id": "RX-01", "hostname": "IPD935-001"}],
    }


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


class LiveTuneGuardTests(unittest.TestCase):
    def test_live_preflight_rejects_empty_tune_without_udp(self):
        calls = []
        with patch.object(erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw))), patch.object(
            erp, "send_udp_reconnect", lambda **kw: calls.append(("udp", kw))
        ):
            plan = {"mode": "adhoc", "commit": "live", "slots": [_slot(tune=None)], "warnings": []}
            with self.assertRaises(erp.PreflightError) as ctx:
                erp.execute_plan(plan, inventory=_live_inventory(), directv=_live_directv(), live=True)
        self.assertTrue(any("tune" in e.lower() or "channel" in e.lower() for e in ctx.exception.errors))
        self.assertEqual(calls, [])

    def test_live_preflight_rejects_blank_tune_channel(self):
        calls = []
        with patch.object(erp, "send_directv_tune", lambda **kw: calls.append("shef")), patch.object(
            erp, "send_udp_reconnect", lambda **kw: calls.append("udp")
        ):
            plan = {
                "mode": "adhoc",
                "commit": "live",
                "slots": [_slot(tune={"channelNumber": "  "})],
                "warnings": [],
            }
            with self.assertRaises(erp.PreflightError):
                erp.execute_plan(plan, inventory=_live_inventory(), directv=_live_directv(), live=True)
        self.assertEqual(calls, [])

    def test_live_mixed_slots_missing_tune_is_preflight_no_udp(self):
        calls = []
        with patch.object(
            erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw["encoder_id"]))
        ), patch.object(
            erp, "send_udp_reconnect", lambda **kw: calls.append(("udp", kw["tx_hostname"]))
        ):
            plan = {
                "mode": "preset_2",
                "commit": "live",
                "slots": [
                    _slot(encoder_id="ENC-01", tune={"channelNumber": "206"}, index=1),
                    _slot(encoder_id="ENC-02", tune=None, index=2, tvs=[2], label="Open game"),
                ],
                "warnings": [],
            }
            with self.assertRaises(erp.PreflightError) as ctx:
                erp.execute_plan(plan, inventory=_live_inventory(), directv=_live_directv(), live=True)
        self.assertTrue(any("ENC-02" in e for e in ctx.exception.errors))
        self.assertEqual(calls, [])

    def test_live_slot_guard_skips_udp_when_tune_missing_after_preflight(self):
        calls = []
        with patch.object(
            erp, "send_directv_tune", lambda **kw: calls.append(("shef", kw["encoder_id"]))
        ), patch.object(
            erp, "send_udp_reconnect", lambda **kw: calls.append(("udp", kw["tx_hostname"]))
        ), patch.object(erp, "_missing_tune_errors", lambda plan: []):
            plan = {"mode": "adhoc", "commit": "live", "slots": [_slot(tune=None)], "warnings": []}
            report = erp.execute_plan(
                plan, inventory=_live_inventory(), directv=_live_directv(), live=True
            )
        self.assertFalse(report["ok"])
        self.assertEqual(report["slots"][0]["status"], "error")
        err = report["slots"][0]["error"].lower()
        self.assertTrue("tune" in err or "channel" in err)
        self.assertEqual(calls, [])

    def test_cli_live_empty_tune_exit_2(self):
        calls = []
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            plan = {"mode": "adhoc", "commit": "live", "slots": [_slot(tune=None)], "warnings": []}
            plan_path = tmp_path / "plan.json"
            plan_path.write_text(json.dumps(plan), encoding="utf-8")
            inv_path = tmp_path / "inv.yaml"
            inv_path.write_text(yaml.safe_dump(_live_inventory()), encoding="utf-8")
            directv_path = tmp_path / "directv.yaml"
            directv_path.write_text(yaml.safe_dump(_live_directv()), encoding="utf-8")
            buf = io.StringIO()
            with patch.object(erp, "send_directv_tune", lambda **kw: calls.append(kw)), patch.object(
                erp, "send_udp_reconnect", lambda **kw: calls.append("udp")
            ), redirect_stdout(buf):
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
        self.assertEqual(code, 2)
        self.assertEqual(calls, [])
        report = json.loads(buf.getvalue())
        self.assertFalse(report["ok"])
        self.assertTrue(any("tune" in e.lower() or "channel" in e.lower() for e in report["errors"]))

    def test_dry_run_empty_tune_does_not_preflight(self):
        calls = []
        with patch.object(erp, "send_directv_tune", lambda **kw: calls.append("shef")), patch.object(
            erp, "send_udp_reconnect", lambda **kw: calls.append("udp")
        ):
            plan = {"mode": "adhoc", "commit": "dry_run", "slots": [_slot(tune=None)], "warnings": []}
            report = erp.execute_plan(
                plan, inventory=_live_inventory(), directv=_live_directv(), live=False
            )
        self.assertTrue(report["ok"])
        self.assertNotIn("shef", calls)
        self.assertEqual(calls, ["udp"])


if __name__ == "__main__":
    unittest.main()
