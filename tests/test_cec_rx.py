"""CEC command building, live-commit refusal, and telnet session."""

from __future__ import annotations

import json
import unittest
from pathlib import Path

import yaml

from scripts.avaccess.cec_rx import (
    command_for,
    main,
    run_cec,
    send_rx_command,
    targets_for,
)

ROOT = Path(__file__).resolve().parents[1]
ROUTING = ROOT / "homeassistant" / "config" / "packages" / "avaccess_routing.yaml"


def _inventory():
    receivers = []
    for number in range(1, 4):
        receivers.append(
            {
                "id": f"RX-{number:02d}",
                "hostname": f"IPD935-00{number}",
                "ip": f"192.168.10.{100 + number}",
            }
        )
    receivers.append(
        {"id": "RX-04", "hostname": "IPD935-REPLACE_ME", "ip": "192.168.10.104"}
    )
    return {
        "network": {"telnet_port": 24},
        "receivers": receivers,
    }


class ScriptedSocket:
    def __init__(self, chunks):
        self.chunks = list(chunks)
        self.sent = bytearray()
        self.closed = False

    def recv(self, _size):
        if not self.chunks:
            return b""
        return self.chunks.pop(0)

    def sendall(self, data):
        self.sent.extend(data)

    def settimeout(self, _timeout):
        return None

    def close(self):
        self.closed = True


class CecRxTests(unittest.TestCase):
    def test_commands_match_the_api_guide(self):
        self.assertEqual(command_for("power-on"), "sinkpower on")
        self.assertEqual(command_for("power-off"), "sinkpower off")
        self.assertEqual(command_for("volume-up"), 'cec -s "40 44 41; 40 45"')
        self.assertEqual(command_for("volume-down"), 'cec -s "40 44 42; 40 45"')
        self.assertEqual(command_for("mute"), 'cec -s "40 44 43; 40 45"')

    def test_power_skips_uncommissioned_receivers(self):
        targets = targets_for(_inventory(), "power-on", 0)
        self.assertEqual([item["id"] for item in targets], ["RX-01", "RX-02", "RX-03"])

    def test_volume_targets_one_tv(self):
        targets = targets_for(_inventory(), "volume-up", 2)
        self.assertEqual(targets[0]["id"], "RX-02")
        self.assertEqual(targets[0]["ip"], "192.168.10.102")

    def test_live_commit_off_sends_nothing(self):
        calls = []
        report = run_cec(
            _inventory(),
            "power-on",
            live=True,
            live_commit="off",
            sender=lambda *args: calls.append(args),
        )
        self.assertTrue(report["refused"])
        self.assertEqual(calls, [])

    def test_dry_run_lists_targets_without_connecting(self):
        calls = []
        report = run_cec(
            _inventory(),
            "power-off",
            live=False,
            sender=lambda *args: calls.append(args),
        )
        self.assertTrue(report["dryRun"])
        self.assertEqual(report["targets"], ["RX-01", "RX-02", "RX-03"])
        self.assertEqual(calls, [])

    def test_live_power_records_a_failure_without_dropping_the_rest(self):
        def sender(ip, _port, command):
            self.assertEqual(command, "sinkpower on")
            if ip.endswith(".102"):
                raise TimeoutError("timed out")

        report = run_cec(
            _inventory(),
            "power-on",
            live=True,
            live_commit="on",
            sender=sender,
        )
        self.assertFalse(report["ok"])
        self.assertEqual(report["accepted"], 2)
        self.assertEqual(report["results"][1]["id"], "RX-02")
        self.assertIn("timed out", report["results"][1]["error"])

    def test_telnet_session_logs_in_and_answers_negotiation(self):
        sock = ScriptedSocket(
            [
                b"\xff\xfd\x01IPD935 login: ",
                b"Welcome.\r\n/ # ",
                b"/ # ",
            ]
        )

        def connect(_addr, _timeout):
            return sock

        send_rx_command("192.168.10.101", 24, "sinkpower on", connect=connect)
        self.assertIn(b"root\r\n", sock.sent)
        self.assertIn(b"sinkpower on\r\n", sock.sent)
        self.assertIn(bytes((255, 252, 1)), sock.sent)
        self.assertTrue(sock.closed)

    def test_cli_refuses_when_live_commit_is_off(self):
        import io
        from contextlib import redirect_stdout
        import tempfile

        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "inventory.yaml"
            path.write_text(yaml.safe_dump(_inventory()), encoding="utf-8")
            buffer = io.StringIO()
            with redirect_stdout(buffer):
                code = main(
                    ["--inventory", str(path), "--action", "power-on", "--live", "--live-commit", "off"]
                )
        self.assertEqual(code, 3)
        report = json.loads(buffer.getvalue())
        self.assertTrue(report["refused"])

    def test_routing_package_gates_cec_on_live_commit(self):
        package = yaml.safe_load(ROUTING.read_text(encoding="utf-8"))
        command = package["shell_command"]["avaccess_cec"]
        self.assertIn("avaccess/scripts/cec_rx.py", command)
        self.assertIn("input_boolean.avaccess_live_commit", command)
        script = package["script"]["avaccess_cec"]
        self.assertEqual(script["sequence"][0]["if"][0]["entity_id"], "input_boolean.avaccess_live_commit")
