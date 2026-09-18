#!/usr/bin/env python3
"""Offline tests for DirecTV SHEF helpers and HA bundle generation."""

from __future__ import annotations

import json
import subprocess
import sys
import tempfile
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
        profile, presets = resolve_presets(inventory, "numeric_v1")
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

    def test_ui_staging_stubs_shell_commands(self) -> None:
        from scripts.generate_ha_bundle import apply_ui_staging_stubs

        inventory = load_yaml(ROOT / "config" / "inventory.example.yaml")
        channels = load_yaml(ROOT / "config" / "channels.example.yaml")
        profile, _presets = resolve_presets(inventory, "numeric_v1")
        package = build_package(
            inventory=inventory,
            channels_cfg=channels,
            profile_override=profile,
            inventory_ha_path="/config/avaccess/config/inventory.yaml",
        )
        staged = apply_ui_staging_stubs(package)
        for name, cmd in staged["shell_command"].items():
            self.assertTrue(str(cmd).startswith("echo "), name)
            self.assertIn("STAGING", str(cmd))

    def test_favorite_scripts_call_tune_channel(self) -> None:
        inventory = load_yaml(ROOT / "config" / "inventory.example.yaml")
        channels = load_yaml(ROOT / "config" / "channels.example.yaml")
        profile, _presets = resolve_presets(inventory, "numeric_v1")
        package = build_package(
            inventory=inventory,
            channels_cfg=channels,
            profile_override=profile,
            inventory_ha_path="/config/avaccess/config/inventory.yaml",
        )
        favorites = {
            name: script
            for name, script in package["script"].items()
            if name.startswith("avaccess_favorite_")
        }
        self.assertTrue(favorites, "expected favorite scripts in the generated package")
        for name, script in favorites.items():
            dumped = yaml.safe_dump(script)
            self.assertIn("script.avaccess_tune_channel", dumped, name)


def _run_generate_ha_bundle(out_dir: Path, *, ui_staging: bool) -> tuple[Path, Path]:
    package_path = out_dir / "avaccess_matrix.yaml"
    dashboard_path = out_dir / "avaccess_matrix_dashboard.yaml"
    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_ha_bundle.py"),
        "--inventory",
        str(ROOT / "config" / "inventory.example.yaml"),
        "--channels",
        str(ROOT / "config" / "channels.example.yaml"),
        "--profile",
        "numeric_v1",
        "--out-package",
        str(package_path),
        "--out-dashboard",
        str(dashboard_path),
    ]
    if ui_staging:
        cmd.append("--ui-staging")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return package_path, dashboard_path


def _iter_cards(cards: list | None):
    for card in cards or []:
        if not isinstance(card, dict):
            continue
        yield card
        yield from _iter_cards(card.get("cards"))


def _buttons_calling(view: dict, service: str) -> list[dict]:
    found: list[dict] = []
    for card in _iter_cards(view.get("cards")):
        if card.get("type") != "button":
            continue
        tap = card.get("tap_action") or {}
        if tap.get("service") == service or str(tap.get("service", "")).startswith(service):
            found.append(card)
    return found


class GenerateHaBundleCliTests(unittest.TestCase):
    """Exercise generate_ha_bundle.py as a CLI, including written YAML files."""

    def test_ui_staging_cli_writes_echo_stubs_into_package_yaml(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=True)
            raw = package_path.read_text()
            self.assertIn("UI-STAGING", raw)
            package = yaml.safe_load(raw)
            commands = package["shell_command"]
            self.assertTrue(commands)
            for name, cmd in commands.items():
                self.assertTrue(str(cmd).startswith("echo "), name)
                self.assertIn("STAGING", str(cmd))
                self.assertNotIn("python3", str(cmd), name)

    def test_dashboard_yaml_contains_sports_views(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=False)
            dashboard = yaml.safe_load(dashboard_path.read_text())
            titles = {view.get("title") for view in dashboard.get("views", [])}
            for expected in ("NFL", "College Football", "Basketball"):
                self.assertIn(expected, titles)
            for view in dashboard.get("views", []):
                dumped = yaml.safe_dump(view)
                self.assertIn("Destination", dumped, view.get("title"))
                self.assertIn("Route Program -> TVs", dumped, view.get("title"))

    def test_control_tab_uses_friendly_preset_and_program_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=False)
            dashboard = yaml.safe_load(dashboard_path.read_text())
            control = next(view for view in dashboard["views"] if view.get("path") == "av-control")

            preset_buttons = _buttons_calling(control, "script.avaccess_preset_")
            self.assertEqual(
                [button["name"] for button in preset_buttons],
                ["Preset 1 ALL", "Preset 2 4 Programs", "Preset 3 9 Programs"],
            )
            self.assertEqual(
                [button["tap_action"]["service"] for button in preset_buttons],
                [
                    "script.avaccess_preset_1_all",
                    "script.avaccess_preset_2_four_programs",
                    "script.avaccess_preset_3_nine_programs",
                ],
            )

            program_buttons = _buttons_calling(control, "script.avaccess_set_program")
            self.assertEqual([button["name"] for button in program_buttons], [f"Program {letter}" for letter in "ABCDEFGHI"])
            for button, key in zip(program_buttons, "abcdefghi", strict=True):
                self.assertEqual(button["tap_action"]["service"], "script.avaccess_set_program")
                self.assertEqual(button["tap_action"]["data"]["program"], f"program_{key}")

    def test_production_dashboard_keeps_directv_media_players(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=False)
            dashboard = yaml.safe_dump(yaml.safe_load(dashboard_path.read_text()))
            package = yaml.safe_dump(yaml.safe_load(package_path.read_text()))
            self.assertIn("media_player.directv_h25_01", dashboard)
            self.assertIn("Now Playing", dashboard)
            self.assertNotIn("sensor.directv_h25_01", dashboard)
            self.assertNotIn("DirecTV not connected", package)

    def test_ui_staging_cli_uses_dummy_now_playing_sensors(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=True)
            package = yaml.safe_load(package_path.read_text())
            dashboard = yaml.safe_load(dashboard_path.read_text())
            dumped_dash = yaml.safe_dump(dashboard)
            dumped_pkg = yaml.safe_dump(package)

            self.assertNotIn("media_player.directv", dumped_dash)
            self.assertIn("Now Playing", dumped_dash)
            self.assertIn("sensor.directv_h25_01", dumped_dash)
            self.assertIn("sensor.directv_h25_09", dumped_dash)
            self.assertIn("directv_h25_01", dumped_pkg)
            self.assertIn("DirecTV not connected", dumped_pkg)

            titles = {view.get("title") for view in dashboard.get("views", [])}
            for expected in ("NFL", "College Football", "Basketball"):
                self.assertIn(expected, titles)
            self.assertIn("Destination", dumped_dash)
            self.assertIn("Route Program -> TVs", dumped_dash)


if __name__ == "__main__":
    unittest.main()
