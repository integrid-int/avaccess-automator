"""WP-D: server Live interlock, b64 argument safety, live UDP re-enrich (unittest)."""

from __future__ import annotations

import base64
import importlib.util
import io
import json
import re
import shlex
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from pathlib import Path
from unittest.mock import patch

import yaml

from scripts.avaccess import execute_route_plan as erp
from scripts.avaccess import save_tv_sets

try:
    import jinja2
    from jinja2.sandbox import ImmutableSandboxedEnvironment
except ImportError:  # pragma: no cover - jinja2 ships with HA, not requirements-dev
    jinja2 = None

ROOT = Path(__file__).resolve().parents[1]
ROUTING_PACKAGE = ROOT / "homeassistant" / "config" / "packages" / "avaccess_routing.yaml"
WRAPPER = ROOT / "homeassistant" / "config" / "avaccess" / "run_execute_route_plan.py"
LIVE_ENTITY = "input_boolean.avaccess_live_commit"


def _load_wrapper():
    spec = importlib.util.spec_from_file_location("ha_wrapper_live_interlock", WRAPPER)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _inventory() -> dict:
    return {
        "network": {"broadcast": "255.255.255.255", "udp_switch_port": 5010},
        "encoders": [{"id": "ENC-01", "hostname": "IPE935-AAA"}],
        "receivers": [
            {"id": "RX-01", "hostname": "IPD935-001"},
            {"id": "RX-02", "hostname": "IPD935-002"},
        ],
    }


def _directv() -> dict:
    return {
        "encoder_to_receiver": {"ENC-01": "H25-01"},
        "receivers": {"H25-01": {"host": "192.168.10.151"}},
    }


def _plan(udp: dict | None) -> dict:
    return {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": 1,
                "encoderId": "ENC-01",
                "program": {"id": "c", "label": "ESPN", "channelNumber": "206"},
                "tvs": [1, 2],
                "tune": {"channelNumber": "206"},
                "udp": udp,
                "status": "planned",
            }
        ],
        "warnings": [],
    }


def _b64(obj) -> str:
    return base64.b64encode(json.dumps(obj).encode()).decode()


class LiveUdpReenrichTests(unittest.TestCase):
    def _run(self, plan, *, live):
        udp_calls = []
        with patch.object(erp, "send_directv_tune", lambda **kw: None), patch.object(
            erp, "send_udp_reconnect", lambda **kw: udp_calls.append(kw)
        ):
            report = erp.execute_plan(plan, inventory=_inventory(), directv=_directv(), live=live)
        return report, udp_calls

    def test_live_overwrites_caller_supplied_udp_hostnames(self):
        plan = _plan({"txHostname": "EVIL-TX", "rxHostnames": ["EVIL-RX-1", "EVIL-RX-9"]})
        report, udp_calls = self._run(plan, live=True)
        self.assertTrue(report["ok"], report)
        self.assertEqual(len(udp_calls), 1)
        self.assertEqual(udp_calls[0]["tx_hostname"], "IPE935-AAA")
        self.assertEqual(udp_calls[0]["rx_hostnames"], ["IPD935-001", "IPD935-002"])
        self.assertEqual(
            report["slots"][0]["udp"],
            {"txHostname": "IPE935-AAA", "rxHostnames": ["IPD935-001", "IPD935-002"]},
        )

    def test_live_does_not_mutate_caller_plan(self):
        plan = _plan({"txHostname": "EVIL-TX", "rxHostnames": ["EVIL-RX-1"]})
        self._run(plan, live=True)
        self.assertEqual(plan["slots"][0]["udp"]["txHostname"], "EVIL-TX")

    def test_live_prefilled_udp_for_unknown_tv_is_preflight_without_sends(self):
        plan = _plan({"txHostname": "IPE935-AAA", "rxHostnames": ["IPD935-001"]})
        plan["slots"][0]["tvs"] = [1, 34]
        sends = []
        with patch.object(erp, "send_directv_tune", lambda **kw: sends.append("shef")), patch.object(
            erp, "send_udp_reconnect", lambda **kw: sends.append("udp")
        ):
            with self.assertRaises(erp.PreflightError):
                erp.execute_plan(plan, inventory=_inventory(), directv=_directv(), live=True)
        self.assertEqual(sends, [])


class PlanB64Tests(unittest.TestCase):
    def test_decode_accepts_standard_base64_json(self):
        self.assertEqual(erp.decode_plan_b64(_b64({"slots": []})), {"slots": []})

    def test_decode_rejects_non_alphabet_and_empty(self):
        good = _b64({"slots": []})
        for bad in ("", f"{good} --live", f"{good}\n", "e30=;id", "e30=' --live '", "-e30=", "e3 0="):
            with self.subTest(bad=bad), self.assertRaises(erp.PreflightError):
                erp.decode_plan_b64(bad)

    def test_decode_rejects_alphabet_valid_but_not_json(self):
        with self.assertRaises(erp.PreflightError):
            erp.decode_plan_b64(base64.b64encode(b"not json").decode())

    def test_cli_injected_plan_b64_exits_2_without_sends(self):
        sends = []
        with tempfile.TemporaryDirectory() as td:
            inv = Path(td) / "inv.yaml"
            inv.write_text(yaml.safe_dump(_inventory()), encoding="utf-8")
            dtv = Path(td) / "directv.yaml"
            dtv.write_text(yaml.safe_dump(_directv()), encoding="utf-8")
            buf = io.StringIO()
            with patch.object(erp, "send_directv_tune", lambda **kw: sends.append("shef")), patch.object(
                erp, "send_udp_reconnect", lambda **kw: sends.append("udp")
            ), redirect_stdout(buf):
                code = erp.main(
                    [
                        "--inventory", str(inv),
                        "--directv-config", str(dtv),
                        "--plan-b64", _b64(_plan(None)) + " --live",
                        "--dry-run",
                    ]
                )
        self.assertEqual(code, 2)
        self.assertEqual(sends, [])
        self.assertIn("base64", json.loads(buf.getvalue())["errors"][0])

    def test_cli_rejects_abbreviated_live_flag(self):
        with redirect_stdout(io.StringIO()), patch("sys.stderr", io.StringIO()):
            with self.assertRaises(SystemExit) as ctx:
                erp.main(["--inventory", "x", "--directv-config", "y", "--plan-b64", "e30=", "--liv"])
        self.assertEqual(ctx.exception.code, 2)

    def test_save_tv_sets_rejects_non_base64(self):
        with tempfile.TemporaryDirectory() as td:
            out = Path(td) / "sets.json"
            for bad in ("", "e30= --out /tmp/x", "e30=\n"):
                with self.subTest(bad=bad), self.assertRaises(SystemExit):
                    save_tv_sets.main(["--sets-b64", bad, "--out", str(out)])
            self.assertFalse(out.exists())
            payload = {"sets": [{"id": "s", "name": "Patio", "tvs": [8, 9]}]}
            save_tv_sets.main(["--sets-b64", _b64(payload), "--out", str(out)])
            self.assertEqual(json.loads(out.read_text())["sets"][0]["tvs"], [8, 9])


class WrapperLiveGateTests(unittest.TestCase):
    def setUp(self):
        self.mod = _load_wrapper()

    def test_live_refused_without_on(self):
        for argv in (
            ["--plan-b64", "e30=", "--live"],
            ["--plan-b64", "e30=", "--live", "--live-commit", "off"],
            ["--plan-b64", "e30=", "--live", "--live-commit", ""],
            ["--plan-b64", "e30=", "--live", "--live-commit=unavailable"],
            ["--plan-b64", "e30=", "--live", "--live-commit"],
        ):
            with self.subTest(argv=argv):
                self.assertIsNotNone(self.mod.live_refusal(argv))

    def test_live_allowed_only_with_on(self):
        self.assertIsNone(self.mod.live_refusal(["--live", "--live-commit", "on"]))
        self.assertIsNone(self.mod.live_refusal(["--live", "--live-commit=on"]))
        self.assertIsNone(self.mod.live_refusal(["--dry-run"]))

    def test_main_refuses_before_loading_executor(self):
        buf = io.StringIO()
        with patch.object(self.mod, "resolve_executor", side_effect=AssertionError("executor ran")), redirect_stdout(buf):
            with self.assertRaises(SystemExit) as ctx:
                self.mod.main(["--plan-b64", "e30=", "--live", "--live-commit", "off"])
        self.assertEqual(ctx.exception.code, self.mod.LIVE_REFUSED_EXIT)
        report = json.loads(buf.getvalue().strip().splitlines()[-1])
        self.assertFalse(report["ok"])
        self.assertIn("Live Commit is off", report["errors"][0])

    def test_main_on_forwards_live_without_gate_flag(self):
        seen = {}

        def fake_run_path(path, run_name=None):
            seen["argv"] = list(sys.argv)

        saved_argv = list(sys.argv)
        try:
            with patch.object(self.mod, "resolve_executor", return_value=Path("/x/execute_route_plan.py")), patch.object(
                self.mod.runpy, "run_path", fake_run_path
            ):
                self.mod.main(["--plan-b64", "e30=", "--live", "--live-commit", "on"])
        finally:
            sys.argv = saved_argv
        self.assertIn("--live", seen["argv"])
        self.assertNotIn("--live-commit", seen["argv"])
        self.assertNotIn("on", seen["argv"])


def _ha_env(states: dict[str, str]):
    env = ImmutableSandboxedEnvironment()

    def regex_match(value, find="", ignorecase=False):
        if not isinstance(value, str):
            value = str(value)
        return bool(re.compile(find, re.I if ignorecase else 0).match(value))

    env.filters["regex_match"] = regex_match
    env.globals["is_state"] = lambda entity_id, state: states.get(entity_id) == state
    return env


def _ha_shell_argv(command: str, states: dict[str, str], data: dict) -> list[str]:
    """Mirror HA shell_command: split prog off, render args, shlex.split, no shell."""
    prog, args = command.split(" ", 1)
    rendered = _ha_env(states).from_string(args).render(**data)
    return [prog, *shlex.split(rendered)]


def _arg_after(argv: list[str], flag: str) -> str:
    return argv[argv.index(flag) + 1]


@unittest.skipIf(jinja2 is None, "jinja2 not installed")
class RoutingPackageTemplateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = yaml.safe_load(ROUTING_PACKAGE.read_text(encoding="utf-8"))
        cls.execute_cmd = cls.package["shell_command"]["avaccess_execute_route_plan"]
        cls.save_cmd = cls.package["shell_command"]["avaccess_save_tv_sets"]
        cls.wrapper = _load_wrapper()

    def test_live_with_boolean_off_renders_refused_gate(self):
        plan_b64 = _b64(_plan(None))
        argv = _ha_shell_argv(self.execute_cmd, {LIVE_ENTITY: "off"}, {"plan_b64": plan_b64, "live": True})
        self.assertEqual(_arg_after(argv, "--plan-b64"), plan_b64)
        self.assertEqual(_arg_after(argv, "--live-commit"), "off")
        self.assertIsNotNone(self.wrapper.live_refusal(argv[2:]))

    def test_live_with_boolean_missing_renders_refused_gate(self):
        argv = _ha_shell_argv(self.execute_cmd, {}, {"plan_b64": "e30=", "live": "true"})
        self.assertEqual(_arg_after(argv, "--live-commit"), "off")
        self.assertIsNotNone(self.wrapper.live_refusal(argv[2:]))

    def test_live_with_boolean_on_passes_gate(self):
        argv = _ha_shell_argv(self.execute_cmd, {LIVE_ENTITY: "on"}, {"plan_b64": "e30=", "live": True})
        self.assertIn("--live", argv)
        self.assertEqual(_arg_after(argv, "--live-commit"), "on")
        self.assertIsNone(self.wrapper.live_refusal(argv[2:]))

    def test_dry_run_has_no_live_flags(self):
        argv = _ha_shell_argv(self.execute_cmd, {LIVE_ENTITY: "on"}, {"plan_b64": "e30=", "live": False})
        self.assertIn("--dry-run", argv)
        self.assertNotIn("--live", argv)
        self.assertNotIn("--live-commit", argv)

    def test_injected_plan_b64_cannot_add_arguments(self):
        injections = (
            "e30= --live --live-commit on",
            "e30= --inventory /tmp/evil.yaml",
            "e30=' --live-commit 'on",
            'e30=" --live-commit "on',
            "e30=;touch /tmp/pwn",
            "$(id)",
        )
        for value in injections:
            with self.subTest(value=value):
                argv = _ha_shell_argv(self.execute_cmd, {LIVE_ENTITY: "off"}, {"plan_b64": value, "live": False})
                self.assertEqual(_arg_after(argv, "--plan-b64"), "")
                self.assertEqual(argv.count("--inventory"), 1)
                self.assertNotIn("--live", argv)
                self.assertNotIn("--live-commit", argv)
                self.assertNotIn("/tmp/evil.yaml", argv)

    def test_non_string_plan_b64_renders_empty(self):
        argv = _ha_shell_argv(self.execute_cmd, {}, {"plan_b64": 123, "live": False})
        self.assertEqual(_arg_after(argv, "--plan-b64"), "")

    def test_injected_sets_b64_cannot_add_arguments(self):
        good = _b64({"sets": []})
        argv = _ha_shell_argv(self.save_cmd, {}, {"sets_b64": good})
        self.assertEqual(_arg_after(argv, "--sets-b64"), good)
        for value in ("e30= --out /tmp/evil.json", "e30=' --out '/tmp/evil.json"):
            with self.subTest(value=value):
                argv = _ha_shell_argv(self.save_cmd, {}, {"sets_b64": value})
                self.assertEqual(_arg_after(argv, "--sets-b64"), "")
                self.assertEqual(argv.count("--out"), 1)
                self.assertEqual(_arg_after(argv, "--out"), "www/avaccess/custom_tv_sets.json")


class RoutingPackageScriptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.package = yaml.safe_load(ROUTING_PACKAGE.read_text(encoding="utf-8"))
        cls.script = cls.package["script"]["avaccess_live_execute"]

    def test_script_runs_live_only_when_boolean_on(self):
        step = self.script["sequence"][0]
        self.assertEqual(
            step["if"],
            [{"condition": "state", "entity_id": LIVE_ENTITY, "state": "on"}],
        )
        call = step["then"][0]
        self.assertEqual(call["action"], "shell_command.avaccess_execute_route_plan")
        self.assertIs(call["data"]["live"], True)
        self.assertEqual(call["response_variable"], "result")
        self.assertEqual(step["then"][-1], {"stop": "Live execute finished", "response_variable": "result"})

    def test_script_refusal_returns_failed_report_and_never_calls_shell(self):
        step = self.script["sequence"][0]
        actions = [a for a in step["else"] if "action" in a]
        self.assertEqual(actions, [])
        refused = step["else"][0]["variables"]["refused"]
        self.assertNotEqual(refused["returncode"], 0)
        report = json.loads(refused["stdout"].splitlines()[-1])
        self.assertFalse(report["ok"])
        self.assertIn("Live Commit is off", report["errors"][0])
        self.assertEqual(step["else"][-1]["response_variable"], "refused")

    def test_script_is_single_mode(self):
        self.assertEqual(self.script["mode"], "single")

    def test_script_keeps_a_night_of_live_take_traces(self):
        # HA keeps 5 traces per script by default; each trace holds the executor report.
        self.assertGreaterEqual(self.script["trace"]["stored_traces"], 50)


if __name__ == "__main__":
    unittest.main()
