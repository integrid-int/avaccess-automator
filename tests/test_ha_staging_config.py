#!/usr/bin/env python3
"""Staging HA package format: modern template sensors and onboarding helper."""

from __future__ import annotations

import io
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_ha_bundle import apply_ui_staging_stubs, build_package, load_yaml, resolve_presets
from scripts.prepare_ha_staging import migrate_legacy_template_sensors


LEGACY_TEMPLATE_FIXTURE = """# leftover legacy package
sensor:
  - platform: template
    sensors:
      directv_h25_01:
        friendly_name: ENC-01
        value_template: "{{ 'STAGING - DirecTV not connected' }}"
        icon_template: mdi:satellite-uplink
"""


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
        "--out-package",
        str(package_path),
        "--out-dashboard",
        str(dashboard_path),
    ]
    if ui_staging:
        cmd.append("--ui-staging")
    subprocess.run(cmd, check=True, capture_output=True, text=True)
    return package_path, dashboard_path


def _template_sensor_dicts(package: dict) -> list[dict]:
    template = package.get("template")
    assert isinstance(template, list), "package.template must be a list"
    sensors: list[dict] = []
    for block in template:
        assert isinstance(block, dict)
        entries = block.get("sensor")
        assert isinstance(entries, list), "template block must use sensor: [dicts]"
        sensors.extend(entry for entry in entries if isinstance(entry, dict))
    return sensors


class ModernTemplateSensorTests(unittest.TestCase):
    def test_apply_ui_staging_stubs_emits_modern_template_sensors(self) -> None:
        inventory = load_yaml(ROOT / "config" / "inventory.example.yaml")
        channels = load_yaml(ROOT / "config" / "channels.example.yaml")
        profile, _presets = resolve_presets(inventory, None)
        package = build_package(
            inventory=inventory,
            channels_cfg=channels,
            profile_override=profile,
            inventory_ha_path="/config/avaccess/config/inventory.yaml",
        )
        staged = apply_ui_staging_stubs(
            package,
            encoder_media_player=channels.get("encoder_media_player", {}),
        )
        dumped = yaml.safe_dump(staged, sort_keys=False)
        self.assertNotIn("platform: template", dumped)
        self.assertNotIn("platform: template", yaml.safe_dump(staged.get("sensor", []), sort_keys=False))
        self.assertIn("template", staged)

        sensors = _template_sensor_dicts(staged)
        by_id = {item.get("default_entity_id"): item for item in sensors}
        self.assertIn("sensor.directv_h25_01", by_id)
        self.assertIn("sensor.directv_h25_09", by_id)
        first = by_id["sensor.directv_h25_01"]
        self.assertEqual(first["name"], "ENC-01")
        self.assertEqual(first["unique_id"], "staging_directv_h25_01")
        self.assertEqual(first["icon"], "mdi:satellite-uplink")
        self.assertIn("DirecTV not connected", str(first["state"]))

    def test_ui_staging_cli_package_yaml_has_template_not_legacy_platform(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=True)
            raw = package_path.read_text()
            self.assertIn("UI-STAGING", raw)
            self.assertIn("\ntemplate:", raw)
            self.assertNotIn("platform: template", raw)
            package = yaml.safe_load(raw)
            sensors = _template_sensor_dicts(package)
            entity_ids = {item.get("default_entity_id") for item in sensors}
            self.assertIn("sensor.directv_h25_01", entity_ids)
            self.assertIn("sensor.directv_h25_09", entity_ids)
            self.assertTrue(all(item.get("icon") == "mdi:satellite-uplink" for item in sensors))
            self.assertTrue(all(str(item.get("unique_id", "")).startswith("staging_") for item in sensors))

    def test_ui_staging_dashboard_labels_sunday_slot_9_nfl_s9(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=True)
            raw = dashboard_path.read_text()
            self.assertIn("NFL S9", raw)
            self.assertNotIn("S9 NFL Slot", raw)


class MigrateLegacyTemplateSensorsTests(unittest.TestCase):
    def test_migrate_legacy_template_sensors_converts_tiny_fixture(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "avaccess_matrix.yaml"
            path.write_text(LEGACY_TEMPLATE_FIXTURE)
            migrate_legacy_template_sensors(path)
            raw = path.read_text()
            self.assertNotIn("platform: template", raw)
            data = yaml.safe_load(raw)
            self.assertNotIn("sensor", data)
            sensors = _template_sensor_dicts(data)
            self.assertEqual(len(sensors), 1)
            sensor = sensors[0]
            self.assertEqual(sensor["default_entity_id"], "sensor.directv_h25_01")
            self.assertEqual(sensor["name"], "ENC-01")
            self.assertEqual(sensor["unique_id"], "staging_directv_h25_01")
            self.assertIn("DirecTV not connected", str(sensor["state"]))
            self.assertEqual(sensor["icon"], "mdi:satellite-uplink")

    def test_migrate_legacy_is_noop_when_already_modern(self) -> None:
        modern = {
            "template": [
                {
                    "sensor": [
                        {
                            "default_entity_id": "sensor.directv_h25_01",
                            "name": "ENC-01",
                            "unique_id": "staging_directv_h25_01",
                            "state": "STAGING - DirecTV not connected",
                            "icon": "mdi:satellite-uplink",
                        }
                    ]
                }
            ]
        }
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "already_modern.yaml"
            path.write_text(yaml.safe_dump(modern, sort_keys=False))
            before = path.read_text()
            migrate_legacy_template_sensors(path)
            self.assertEqual(path.read_text(), before)


class CompleteHaOnboardingTests(unittest.TestCase):
    def test_argument_defaults_and_dry_run(self) -> None:
        from scripts.complete_ha_onboarding import build_onboarding_plan, parse_args

        args = parse_args(["--dry-run"])
        self.assertEqual(args.username, "operator")
        self.assertEqual(args.password, "avaccess-staging")
        self.assertEqual(args.base_url, "http://127.0.0.1:8123")
        self.assertTrue(args.dry_run)

        plan = build_onboarding_plan(args)
        paths = [step["path"] for step in plan]
        self.assertEqual(
            paths,
            [
                "/api/onboarding/users",
                "/api/onboarding/core_config",
                "/api/onboarding/analytics",
                "/api/onboarding/integration",
            ],
        )
        user_body = plan[0]["body"]
        self.assertEqual(user_body["username"], "operator")
        self.assertEqual(user_body["password"], "avaccess-staging")
        self.assertEqual(user_body["client_id"], "http://127.0.0.1:8123/")
        core_body = plan[1]["body"]
        self.assertEqual(core_body["timezone"], "America/New_York")
        self.assertEqual(core_body["unit_system"], "us_customary")
        self.assertEqual(core_body["location_name"], "AVAccess Staging")

        from scripts.complete_ha_onboarding import main as onboarding_main

        buf = io.StringIO()
        with patch("sys.argv", ["complete_ha_onboarding.py", "--dry-run"]), redirect_stdout(buf):
            with patch("scripts.complete_ha_onboarding.urlopen") as urlopen:
                onboarding_main()
        urlopen.assert_not_called()
        output = buf.getvalue()
        self.assertIn("/api/onboarding/users", output)
        self.assertIn("operator", output)
        self.assertIn("dry-run", output.lower())


if __name__ == "__main__":
    unittest.main()
