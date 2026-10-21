"""Live Take finishes and reports inside Home Assistant's 60 s shell_command limit."""

from __future__ import annotations

import base64
import io
import json
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.avaccess import execute_route_plan as erp


def _inventory(n: int = 9) -> dict:
    return {
        "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
        "encoders": [{"id": f"ENC-{i:02d}", "hostname": f"IPE935-{i:03d}"} for i in range(1, n + 1)],
        "receivers": [{"id": f"RX-{i:02d}", "hostname": f"IPD935-{i:03d}"} for i in range(1, n + 1)],
    }


def _directv(n: int = 9, **extra) -> dict:
    return {
        "encoder_to_receiver": {f"ENC-{i:02d}": f"H25-{i:02d}" for i in range(1, n + 1)},
        "receivers": {f"H25-{i:02d}": {"host": f"192.168.10.{150 + i}"} for i in range(1, n + 1)},
        **extra,
    }


def _plan(n: int = 9) -> dict:
    return {
        "mode": "adhoc",
        "slots": [
            {
                "index": i,
                "encoderId": f"ENC-{i:02d}",
                "program": {"id": f"g{i}", "channelNumber": str(200 + i)},
                "tvs": [i],
                "tune": {"channelNumber": str(200 + i)},
                "udp": None,
                "status": "planned",
            }
            for i in range(1, n + 1)
        ],
    }


class FakeClock:
    def __init__(self) -> None:
        self.now = 1000.0

    def __call__(self) -> float:
        return self.now


class LiveTimeBudgetTests(unittest.TestCase):
    def setUp(self) -> None:
        self.clock = FakeClock()
        self.tuned: list[str] = []
        self.udp: list[str] = []
        self.slot_seconds = 0.3

        def fake_tune(*, channel, encoder_id, directv, dry_run=False, timeout=None):
            self.clock.now += self.slot_seconds
            self.tuned.append(encoder_id)
            return {"ok": True}

        def fake_udp(**kw):
            self.udp.append(kw["tx_hostname"])

        for name, value in (("send_directv_tune", fake_tune), ("send_udp_reconnect", fake_udp)):
            patcher = patch.object(erp, name, value)
            patcher.start()
            self.addCleanup(patcher.stop)

    def run_live(self, **kwargs) -> dict:
        return erp.execute_plan(
            _plan(), _inventory(), _directv(), live=True, clock=self.clock, **kwargs
        )

    def test_worst_case_slot_covers_tune_and_every_verify_poll(self) -> None:
        # 4 s tune + 3 x 4 s getTuned + 2 x 0.5 s between polls
        self.assertAlmostEqual(erp.worst_case_slot_seconds({"timeout_seconds": 4}), 17.0)
        self.assertAlmostEqual(
            erp.worst_case_slot_seconds({"timeout_seconds": 4, "verify_tune": False}), 4.0
        )
        self.assertAlmostEqual(erp.worst_case_slot_seconds({}), 17.0)

    def test_healthy_slots_all_run_inside_the_budget(self) -> None:
        report = self.run_live()
        self.assertTrue(report["ok"])
        self.assertEqual(len(self.tuned), 9)
        self.assertEqual(len(self.udp), 9)

    def test_slow_receivers_stop_before_the_ha_timeout_and_report_skipped_slots(self) -> None:
        self.slot_seconds = 12.0
        report = self.run_live()

        # Slots start at 0, 12, 24 s; a 4th would start at 36 s and could run to 53 s.
        self.assertEqual(self.tuned, ["ENC-01", "ENC-02", "ENC-03"])
        self.assertEqual(len(self.udp), 3)
        self.assertFalse(report["ok"])
        statuses = [slot["status"] for slot in report["slots"]]
        self.assertEqual(statuses, ["ok"] * 3 + ["error"] * 6)
        skipped = report["slots"][3]
        self.assertIn("Not attempted", skipped["error"])
        self.assertIn("50 s", skipped["error"])
        self.assertEqual(skipped["message"], skipped["error"])
        self.assertEqual(len(report["errors"]), 6)
        self.assertTrue(report["errors"][0].startswith("ENC-04: Not attempted"))
        self.assertLessEqual(self.clock.now - 1000.0, erp.LIVE_TIME_BUDGET_S)

    def test_budget_can_be_set_per_call(self) -> None:
        self.slot_seconds = 12.0
        self.run_live(time_budget_s=30.0)
        # 17 s worst case: only a slot starting at or before 13 s fits in 30 s.
        self.assertEqual(self.tuned, ["ENC-01", "ENC-02"])

    def test_dry_run_ignores_the_budget(self) -> None:
        self.slot_seconds = 12.0
        report = erp.execute_plan(_plan(), _inventory(), _directv(), live=False, clock=self.clock)
        self.assertTrue(report["ok"])
        self.assertEqual(len(self.tuned), 9)

    def test_shef_timeout_too_long_for_the_budget_fails_preflight(self) -> None:
        with self.assertRaises(erp.PreflightError) as ctx:
            erp.execute_plan(
                _plan(), _inventory(), _directv(timeout_seconds=15), live=True, clock=self.clock
            )
        self.assertIn("timeout_seconds", ctx.exception.errors[0])
        self.assertEqual(self.tuned, [])
        self.assertEqual(self.udp, [])

    def test_report_records_elapsed_time(self) -> None:
        self.slot_seconds = 1.5
        report = self.run_live()
        self.assertEqual(report["slots"][0]["elapsedMs"], 1500)
        self.assertEqual(report["elapsedMs"], 13500)

    def test_cli_time_budget_flag_reaches_the_executor(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inv = Path(tmp) / "inventory.yaml"
            dtv = Path(tmp) / "directv.yaml"
            inv.write_text(yaml.safe_dump(_inventory()))
            dtv.write_text(yaml.safe_dump(_directv()))
            plan_b64 = base64.b64encode(json.dumps(_plan()).encode()).decode()
            seen = {}
            real = erp.execute_plan

            def spy(*args, **kwargs):
                seen.update(kwargs)
                return real(*args, **kwargs)

            buf = io.StringIO()
            with patch.object(erp, "execute_plan", spy), redirect_stdout(buf):
                code = erp.main(
                    [
                        "--inventory", str(inv), "--directv-config", str(dtv),
                        "--plan-b64", plan_b64, "--live", "--time-budget", "20",
                    ]
                )
        self.assertEqual(code, 0)
        self.assertEqual(seen["time_budget_s"], 20.0)


if __name__ == "__main__":
    unittest.main()
