#!/usr/bin/env python3
"""Offline tests for DirecTV SHEF helpers and HA bundle generation."""

from __future__ import annotations

import io
import json
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch
from urllib.error import URLError

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts import directv_shef as shef
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

    def test_socket_timeout_names_host(self) -> None:
        def slow(*_args, **_kwargs):
            raise TimeoutError("timed out")

        with patch("scripts.directv_shef.urllib.request.urlopen", slow):
            with self.assertRaises(SystemExit) as ctx:
                shef_get("192.168.10.151", 8080, "/tv/tune")
        self.assertIn("192.168.10.151", str(ctx.exception))

    def test_http_200_with_error_body_status_raises(self) -> None:
        body = {"status": {"code": 403, "commandResult": 1, "msg": "Forbidden."}}
        with patch("scripts.directv_shef.urllib.request.urlopen", _fake_urlopen(lambda _url: body)):
            with self.assertRaises(SystemExit) as ctx:
                shef_get("192.168.10.151", 8080, "/tv/tune", {"major": 206})
        self.assertIn("403", str(ctx.exception))
        self.assertIn("Forbidden", str(ctx.exception))


def _fake_urlopen(responder, calls: list | None = None):
    """urlopen stand-in; ``responder(url)`` returns the JSON body dict."""

    class FakeResp:
        def __init__(self, payload: dict) -> None:
            self._payload = payload

        def read(self) -> bytes:
            return json.dumps(self._payload).encode()

        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

    def fake(req, timeout=0):  # noqa: ANN001
        if calls is not None:
            calls.append(req.full_url)
        return FakeResp(responder(req.full_url))

    return fake


_OK = {"code": 200, "commandResult": 0, "msg": "OK."}
_RECV = {"id": "H25-01", "host": "192.168.10.151", "port": 8080, "client_addr": "0"}


class CheckShefStatusTests(unittest.TestCase):
    def test_success(self) -> None:
        shef.check_shef_status({"status": dict(_OK)}, "u", require=True)

    def test_non_200_code_rejected(self) -> None:
        for code in (403, 500, "404"):
            with self.subTest(code=code):
                with self.assertRaises(SystemExit):
                    shef.check_shef_status({"status": {"code": code, "msg": "x"}}, "u")

    def test_nonzero_command_result_rejected(self) -> None:
        with self.assertRaises(SystemExit):
            shef.check_shef_status({"status": {"code": 200, "commandResult": 1}}, "u")

    def test_invalid_code_rejected(self) -> None:
        for status in ({"msg": "OK."}, {"code": "OK"}, "OK"):
            with self.subTest(status=status):
                with self.assertRaises(SystemExit):
                    shef.check_shef_status({"status": status}, "u")

    def test_missing_status_only_rejected_when_required(self) -> None:
        shef.check_shef_status({"major": 206}, "u")
        with self.assertRaises(SystemExit):
            shef.check_shef_status({}, "u", require=True)


class TuneStatusTests(unittest.TestCase):
    def test_cmd_tune_requires_status(self) -> None:
        with patch("scripts.directv_shef.urllib.request.urlopen", _fake_urlopen(lambda _u: {})):
            with self.assertRaises(SystemExit):
                shef.cmd_tune(_RECV, 206, 65535, 1.0)

    def test_cmd_tune_ok(self) -> None:
        with patch(
            "scripts.directv_shef.urllib.request.urlopen",
            _fake_urlopen(lambda _u: {"status": dict(_OK)}),
        ):
            self.assertEqual(shef.cmd_tune(_RECV, 206, 65535, 1.0)["status"]["code"], 200)


class VerifyTunedTests(unittest.TestCase):
    def test_tuned_matches(self) -> None:
        self.assertTrue(shef.tuned_matches({"major": 206, "minor": 65535}, 206, 65535))
        self.assertTrue(shef.tuned_matches({"major": "206"}, 206, 65535))
        self.assertTrue(shef.tuned_matches({"major": 229, "minor": 1}, 229, 1))
        self.assertFalse(shef.tuned_matches({"major": 229, "minor": 2}, 229, 1))
        self.assertFalse(shef.tuned_matches({"major": 212}, 206, 65535))
        self.assertFalse(shef.tuned_matches({}, 206, 65535))

    def test_retries_until_receiver_reports_channel(self) -> None:
        reports = iter([{"major": 212}, {"major": 206}])

        def responder(url: str) -> dict:
            self.assertIn("/tv/getTuned", url)
            return {"status": dict(_OK), **next(reports)}

        sleeps: list[float] = []
        with patch("scripts.directv_shef.urllib.request.urlopen", _fake_urlopen(responder)):
            tuned = shef.verify_tuned(_RECV, 206, 65535, 1.0, sleep=sleeps.append)
        self.assertEqual(tuned["major"], 206)
        self.assertEqual(sleeps, [shef.VERIFY_DELAY_S])

    def test_mismatch_raises_after_attempts(self) -> None:
        calls: list[str] = []
        with patch(
            "scripts.directv_shef.urllib.request.urlopen",
            _fake_urlopen(lambda _u: {"status": dict(_OK), "major": 212, "callsign": "ESPN2"}, calls),
        ):
            with self.assertRaises(SystemExit) as ctx:
                shef.verify_tuned(_RECV, 206, 65535, 1.0, attempts=3, sleep=lambda _s: None)
        self.assertEqual(len(calls), 3)
        self.assertIn("expected ch=206", str(ctx.exception))
        self.assertIn("ESPN2", str(ctx.exception))

    def test_tune_and_verify_without_verify_skips_get_tuned(self) -> None:
        calls: list[str] = []
        with patch(
            "scripts.directv_shef.urllib.request.urlopen",
            _fake_urlopen(lambda _u: {"status": dict(_OK)}, calls),
        ):
            result = shef.tune_and_verify(_RECV, 206, 65535, 1.0, verify=False)
        self.assertNotIn("tuned", result)
        self.assertEqual(len(calls), 1)
        self.assertIn("/tv/tune", calls[0])

    def test_cli_tune_verify_mismatch_exits_nonzero(self) -> None:
        def responder(url: str) -> dict:
            if "/tv/getTuned" in url:
                return {"status": dict(_OK), "major": 212}
            return {"status": dict(_OK)}

        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "directv.yaml"
            cfg.write_text(
                yaml.safe_dump(
                    {
                        "encoder_to_receiver": {"ENC-01": "H25-01"},
                        "receivers": {"H25-01": {"host": "192.168.10.151"}},
                    }
                )
            )
            argv = ["directv_shef.py", "--config", str(cfg), "tune", "--encoder", "ENC-01",
                    "--channel", "206", "--verify"]
            with patch.object(sys, "argv", argv), patch(
                "scripts.directv_shef.urllib.request.urlopen", _fake_urlopen(responder)
            ), patch("scripts.directv_shef.time.sleep", lambda _s: None), redirect_stdout(io.StringIO()):
                with self.assertRaises(SystemExit) as ctx:
                    shef.main()
        self.assertIn("verify failed", str(ctx.exception.code))


class ExecutorShefStatusTests(unittest.TestCase):
    """Live executor: a failed or unconfirmed SHEF tune fails the slot before UDP."""

    def _inventory(self) -> dict:
        return {
            "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
            "encoders": [
                {"id": "ENC-01", "hostname": "IPE935-AAA"},
                {"id": "ENC-02", "hostname": "IPE935-BBB"},
            ],
            "receivers": [
                {"id": "RX-01", "hostname": "IPD935-001"},
                {"id": "RX-02", "hostname": "IPD935-002"},
            ],
        }

    def _directv(self, **extra) -> dict:
        return {
            "encoder_to_receiver": {"ENC-01": "H25-01", "ENC-02": "H25-02"},
            "receivers": {
                "H25-01": {"host": "192.168.10.151"},
                "H25-02": {"host": "192.168.10.152"},
            },
            "timeout_seconds": 1,
            **extra,
        }

    def _plan(self) -> dict:
        def slot(index: int, enc: str, tx: str, tv: int, channel: str) -> dict:
            return {
                "index": index,
                "encoderId": enc,
                "program": {"id": f"g{index}", "label": f"Game {index}", "channelNumber": channel},
                "tvs": [tv],
                "tune": {"channelNumber": channel},
                "udp": {"txHostname": tx, "rxHostnames": [f"IPD935-00{tv}"]},
                "status": "planned",
            }

        return {
            "mode": "adhoc",
            "commit": "live",
            "slots": [slot(1, "ENC-01", "IPE935-AAA", 1, "206"), slot(2, "ENC-02", "IPE935-BBB", 2, "212")],
            "warnings": [],
        }

    def _run(self, responder, directv: dict | None = None):
        from scripts.avaccess import execute_route_plan as erp

        udp: list[str] = []
        with patch("scripts.directv_shef.urllib.request.urlopen", _fake_urlopen(responder)), patch.object(
            erp, "send_udp_reconnect", lambda **kw: udp.append(kw["tx_hostname"])
        ), patch("scripts.directv_shef.time.sleep", lambda _s: None):
            report = erp.execute_plan(
                self._plan(),
                inventory=self._inventory(),
                directv=directv or self._directv(),
                live=True,
            )
        return report, udp

    def test_error_body_status_fails_slot_without_udp(self) -> None:
        def responder(url: str) -> dict:
            if "192.168.10.151" in url and "/tv/tune" in url:
                return {"status": {"code": 403, "commandResult": 1, "msg": "Forbidden."}}
            if "/tv/getTuned" in url:
                return {"status": dict(_OK), "major": 212, "minor": 65535}
            return {"status": dict(_OK)}

        report, udp = self._run(responder)
        self.assertFalse(report["ok"])
        self.assertEqual(report["slots"][0]["status"], "error")
        self.assertIn("403", report["slots"][0]["error"])
        self.assertEqual(report["slots"][1]["status"], "ok")
        self.assertEqual(udp, ["IPE935-BBB"])

    def test_verify_mismatch_fails_slot_without_udp(self) -> None:
        def responder(url: str) -> dict:
            if "/tv/getTuned" in url:
                return {"status": dict(_OK), "major": 212, "minor": 65535}
            return {"status": dict(_OK)}

        report, udp = self._run(responder)
        self.assertEqual(report["slots"][0]["status"], "error")
        self.assertIn("verify failed", report["slots"][0]["error"])
        self.assertEqual(report["slots"][1]["status"], "ok")
        self.assertEqual(udp, ["IPE935-BBB"])

    def test_verify_disabled_skips_get_tuned(self) -> None:
        urls: list[str] = []

        def responder(url: str) -> dict:
            urls.append(url)
            return {"status": dict(_OK)}

        report, udp = self._run(responder, directv=self._directv(verify_tune=False))
        self.assertTrue(report["ok"], report)
        self.assertEqual(udp, ["IPE935-AAA", "IPE935-BBB"])
        self.assertFalse(any("/tv/getTuned" in u for u in urls))


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
        if card.get("type") not in {"button", "custom:avaccess-key"}:
            continue
        tap = card.get("tap_action") or {}
        if tap.get("service") == service or str(tap.get("service", "")).startswith(service):
            found.append(card)
    return found


class FriendlySelectOptionsTests(unittest.TestCase):
    def test_input_selects_use_friendly_labels_and_scripts_map_back(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            package_path, _dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=False)
            package = yaml.safe_load(package_path.read_text())
        program = package["input_select"]["avaccess_program"]
        channel = package["input_select"]["avaccess_channel"]
        self.assertEqual(program["options"][0], "Program A")
        self.assertIn("ESPN", channel["options"])
        self.assertNotIn("program_a", program["options"])
        self.assertNotIn("espn", channel["options"])
        tune_vars = package["script"]["avaccess_tune_channel"]["variables"]
        self.assertEqual(tune_vars["program_label_to_key"]["Program A"], "program_a")
        self.assertEqual(tune_vars["channel_label_to_key"]["ESPN"], "espn")
        self.assertEqual(
            package["script"]["avaccess_tune_espn"]["sequence"][0]["data"]["option"],
            "ESPN",
        )


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
                self.assertEqual(view.get("type"), "panel", view.get("title"))
                self.assertEqual(view.get("theme"), "Avaccess Routing", view.get("title"))
                self.assertEqual(view["cards"][0]["type"], "vertical-stack", view.get("title"))
                dumped = yaml.safe_dump(view, allow_unicode=True)
                self.assertIsNone(view.get("icon"), view.get("title"))
                self.assertIn("Sources", dumped, view.get("title"))
                self.assertIn("Actions", dumped, view.get("title"))
                if view.get("path") == "av-control":
                    self.assertIn("Displays", dumped, view.get("title"))
                self.assertIn("custom:avaccess-key", dumped, view.get("title"))
                self.assertIn("Route Program → TVs", dumped, view.get("title"))
                self.assertGreaterEqual(dumped.count("Route Program → TVs"), 2, view.get("title"))
                self.assertNotIn("mdi:television-multiple", dumped, view.get("title"))
                tune_services = {
                    (card.get("tap_action") or {}).get("service", "")
                    for card in _iter_cards(view.get("cards"))
                    if card.get("type") in {"button", "custom:avaccess-key"}
                    and str((card.get("tap_action") or {}).get("service", "")).startswith("script.avaccess_tune_")
                }
                self.assertEqual(tune_services, {"script.avaccess_tune_selected_channel"}, view.get("title"))
                selection_cards = [
                    card
                    for card in _iter_cards(view.get("cards"))
                    if card.get("type") == "entities"
                    and any(
                        (e.get("entity") if isinstance(e, dict) else e) == "input_select.avaccess_program"
                        for e in card.get("entities", [])
                    )
                ]
                self.assertEqual(len(selection_cards), 1, view.get("title"))

    def test_control_tab_uses_friendly_preset_and_program_names(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            _package_path, dashboard_path = _run_generate_ha_bundle(Path(tmp), ui_staging=False)
            dashboard = yaml.safe_load(dashboard_path.read_text())
            control = next(view for view in dashboard["views"] if view.get("path") == "av-control")

            preset_buttons = [
                button
                for button in _buttons_calling(control, "input_select.select_option")
                if (button.get("tap_action") or {}).get("data", {}).get("entity_id")
                == "input_select.avaccess_active_preset"
            ]
            self.assertEqual(
                [button["name"] for button in preset_buttons],
                ["ALL", "4 Programs", "9 Programs"],
            )
            for button in preset_buttons:
                self.assertEqual(button["tap_action"]["data"]["option"], button["name"])
            apply_buttons = _buttons_calling(control, "script.avaccess_apply_selected_preset")
            self.assertGreaterEqual(len(apply_buttons), 1)
            channel_buttons = [
                button
                for button in _buttons_calling(control, "input_select.select_option")
                if (button.get("tap_action") or {}).get("data", {}).get("entity_id")
                == "input_select.avaccess_channel"
            ]
            self.assertIn("ESPN", [button["name"] for button in channel_buttons])

            program_buttons = _buttons_calling(control, "script.avaccess_set_program")
            self.assertEqual([button["name"] for button in program_buttons], [f"Program {letter}" for letter in "ABCDEFGHI"])
            for button in program_buttons:
                self.assertEqual(button["variant"], "choice")
                self.assertEqual(button["selected_state"], button["name"])
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
            dumped_dash = yaml.safe_dump(dashboard, allow_unicode=True)
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
            self.assertIn("Actions", dumped_dash)
            self.assertIn("custom:avaccess-key", dumped_dash)
            self.assertIn("Route Program → TVs", dumped_dash)
            self.assertIn("All 9 receivers", dumped_dash)


if __name__ == "__main__":
    unittest.main()
