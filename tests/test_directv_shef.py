#!/usr/bin/env python3
"""Offline tests for DirecTV SHEF helpers and HA bundle generation."""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.directv_shef import parse_channel, shef_get, summarize_tuned
from scripts.generate_ha_bundle import build_package, load_yaml, resolve_presets


ROOT = Path(__file__).resolve().parent.parent


class ParseChannelTests(unittest.TestCase):
    def test_major_only(self) -> None:
        self.assertEqual(parse_channel("206"), (206, 65535))

    def test_major_minor_dot(self) -> None:
        self.assertEqual(parse_channel("229.1"), (229, 1))

    def test_major_minor_dash(self) -> None:
        self.assertEqual(parse_channel("229-1"), (229, 1))


class SummarizeTunedTests(unittest.TestCase):
    def test_summary(self) -> None:
        text = summarize_tuned(
            {"title": "NFL Football", "callsign": "WGHP", "major": 8, "minor": 65535}
        )
        self.assertIn("WGHP", text)
        self.assertIn("8-65535", text)


class ShefGetTests(unittest.TestCase):
    def test_builds_tune_url(self) -> None:
        class FakeResp:
            def read(self) -> bytes:
                return json.dumps({"status": {"code": 200, "msg": "OK."}}).encode()

            def __enter__(self):
                return self

            def __exit__(self, *_args):
                return False

        captured = {}

        def fake_urlopen(req, timeout=0):  # noqa: ANN001
            captured["url"] = req.full_url
            return FakeResp()

        with patch("scripts.directv_shef.urllib.request.urlopen", fake_urlopen):
            payload = shef_get("192.168.10.151", 8080, "/tv/tune", {"major": 206, "minor": 65535})
        self.assertEqual(payload["status"]["code"], 200)
        self.assertEqual(
            captured["url"],
            "http://192.168.10.151:8080/tv/tune?major=206&minor=65535",
        )

    def test_connection_error(self) -> None:
        def boom(*_args, **_kwargs):
            raise URLError("timed out")

        with patch("scripts.directv_shef.urllib.request.urlopen", boom):
            with self.assertRaises(SystemExit):
                shef_get("192.168.10.151", 8080, "/info/mode")


class BundleGenerationTests(unittest.TestCase):
    def test_directv_transport_emits_tune_shell_command(self) -> None:
        inventory = load_yaml(ROOT / "config" / "inventory.example.yaml")
        channels = load_yaml(ROOT / "config" / "channels.example.yaml")
        profile, presets = resolve_presets(inventory, None)
        self.assertIn("1_all", presets)
        package = build_package(
            inventory=inventory,
            channels_cfg=channels,
            profile_override=profile,
            inventory_ha_path="/config/avaccess/config/inventory.yaml",
        )
        self.assertIn("avaccess_directv_tune", package["shell_command"])
        tune_script = package["script"]["avaccess_tune_channel"]
        dumped = yaml.safe_dump(tune_script)
        self.assertIn("shell_command.avaccess_directv_tune", dumped)
        self.assertNotIn("shell_command.avaccess_itach_send_channel", dumped)


if __name__ == "__main__":
    unittest.main()
