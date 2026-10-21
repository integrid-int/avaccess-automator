#!/usr/bin/env python3
"""apply_preset.py validates every route before sending any UDP datagram."""

from __future__ import annotations

import copy
import io
import sys
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import apply_preset as ap


def _inventory() -> dict:
    return {
        "network": {"broadcast": "192.168.10.255", "udp_switch_port": 5010},
        "encoders": [
            {"id": "ENC-01", "hostname": "IPE935-AAA"},
            {"id": "ENC-02", "hostname": "IPE935-BBB"},
            {"id": "ENC-03", "hostname": "IPE935-CCC"},
        ],
        "receivers": [{"id": f"RX-0{i}", "hostname": f"IPD935-00{i}"} for i in range(1, 7)],
        "presets": {
            "two": {
                "routes": {
                    "ENC-01": ["RX-01", "RX-02"],
                    "ENC-02": [],
                    "ENC-03": ["RX-03"],
                }
            },
        },
    }


def _with_routes(routes: dict) -> dict:
    inv = _inventory()
    inv["presets"]["bad"] = {"routes": routes}
    return inv


def _commissioned_example_inventory() -> dict:
    data = yaml.safe_load((ROOT / "config" / "inventory.example.yaml").read_text())
    for item in data["encoders"]:
        item["hostname"] = f"IPE935-{item['id']}"
    for item in data["receivers"]:
        item["hostname"] = f"IPD935-{item['id']}"
    return data


class ApplyPresetPreflightTests(unittest.TestCase):
    def _apply(self, inventory: dict, preset: str) -> tuple[list[bytes], str]:
        sent: list[bytes] = []
        buf = io.StringIO()
        with patch.object(ap, "send_udp", lambda payload, *_a, **_k: sent.append(payload)), redirect_stdout(buf):
            ap.apply_preset(inventory, preset, dry_run=False, delay_s=0, mapping_profile=None)
        return sent, buf.getvalue()

    def _assert_nothing_sent(self, inventory: dict, preset: str = "bad") -> str:
        sent: list[bytes] = []
        with patch.object(ap, "send_udp", lambda payload, *_a, **_k: sent.append(payload)), redirect_stdout(
            io.StringIO()
        ):
            with self.assertRaises(SystemExit) as ctx:
                ap.apply_preset(inventory, preset, dry_run=False, delay_s=0, mapping_profile=None)
        self.assertEqual(sent, [])
        return str(ctx.exception.code)

    def test_valid_preset_sends_every_route_with_sequential_sessions(self) -> None:
        sent, out = self._apply(_inventory(), "two")
        self.assertEqual(
            [p.decode("ascii") for p in sent],
            [
                "msg_b_reconnect IPE935-AAA:1:2 IPD935-001 IPD935-002",
                "msg_b_reconnect IPE935-CCC:2:1 IPD935-003",
            ],
        )
        self.assertIn("skip ENC-02", out)

    def test_unknown_receiver_in_later_route_sends_nothing(self) -> None:
        msg = self._assert_nothing_sent(
            _with_routes({"ENC-01": ["RX-01"], "ENC-02": ["RX-02"], "ENC-03": ["RX-99"]})
        )
        self.assertIn("RX-99", msg)
        self.assertIn("nothing sent", msg)

    def test_unknown_encoder_in_later_route_sends_nothing(self) -> None:
        msg = self._assert_nothing_sent(_with_routes({"ENC-01": ["RX-01"], "ENC-09": ["RX-02"]}))
        self.assertIn("ENC-09", msg)

    def test_placeholder_hostname_in_later_route_sends_nothing(self) -> None:
        inv = _with_routes({"ENC-01": ["RX-01"], "ENC-02": ["RX-02"]})
        inv["receivers"][1]["hostname"] = "IPD935-REPLACE_ME"
        msg = self._assert_nothing_sent(inv)
        self.assertIn("RX-02", msg)
        self.assertIn("REPLACE_ME", msg)

    def test_missing_or_malformed_hostnames_send_nothing(self) -> None:
        inv = _with_routes({"ENC-01": ["RX-01"], "ENC-02": ["RX-02"], "ENC-03": ["RX-03"]})
        inv["encoders"][1]["hostname"] = ""
        inv["receivers"][2]["hostname"] = "IPD935 003"
        msg = self._assert_nothing_sent(inv)
        self.assertIn("ENC-02", msg)
        self.assertIn("RX-03", msg)

    def test_all_errors_reported_together(self) -> None:
        msg = self._assert_nothing_sent(
            _with_routes({"ENC-01": ["RX-77"], "ENC-02": ["RX-88"], "ENC-03": "RX-03"})
        )
        for needle in ("RX-77", "RX-88", "ENC-03"):
            self.assertIn(needle, msg)

    def test_receiver_on_two_encoders_sends_nothing(self) -> None:
        msg = self._assert_nothing_sent(_with_routes({"ENC-01": ["RX-01", "RX-02"], "ENC-02": ["RX-02"]}))
        self.assertIn("RX-02", msg)
        self.assertIn("ENC-01", msg)
        self.assertIn("ENC-02", msg)

    def test_preset_without_routes_sends_nothing(self) -> None:
        inv = _inventory()
        inv["presets"]["bad"] = {"description": "empty"}
        self._assert_nothing_sent(inv)

    def test_example_presets_pass_preflight_when_commissioned(self) -> None:
        inv = _commissioned_example_inventory()
        for profile, data in inv["mapping_profiles"]["profiles"].items():
            for preset in data["presets"]:
                with self.subTest(profile=profile, preset=preset):
                    _profile, messages, _skipped = ap.plan_preset_messages(
                        copy.deepcopy(inv), preset, profile
                    )
                    self.assertTrue(messages)


if __name__ == "__main__":
    unittest.main()
