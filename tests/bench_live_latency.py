#!/usr/bin/env python3
"""Time a Live Take end to end against fake DirecTV H25 SHEF servers.

Runs homeassistant/config/avaccess/run_execute_route_plan.py the way HA's
shell_command does (--live --live-commit on), with one local HTTP server per
H25 and UDP aimed at an unused loopback port. Nothing leaves the machine.

Home Assistant kills a shell_command after 60 s and the panel then gets no
report, so every scenario must print its report well inside that.

Usage:
  python3 tests/bench_live_latency.py              # all scenarios, 9 slots
  python3 tests/bench_live_latency.py --slots 10 --scenario slow_verify
"""

from __future__ import annotations

import argparse
import base64
import json
import socket
import subprocess
import sys
import tempfile
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import yaml

ROOT = Path(__file__).resolve().parents[1]
WRAPPER = ROOT / "homeassistant" / "config" / "avaccess" / "run_execute_route_plan.py"
HA_SHELL_TIMEOUT_S = 60.0
SHEF_TIMEOUT_S = 4.0

OK_STATUS = {"code": 200, "commandResult": 0, "msg": "OK"}

# Per-receiver behavior:
#   (tune_delay_s, get_tuned_delay_s, getTuned call that first reports the new channel (0 = never), hang)
SCENARIOS: dict[str, dict] = {
    "healthy": {"default": (0.15, 0.05, 1, False)},
    "one_offline": {"default": (0.15, 0.05, 1, False), "H25-03": (0, 0, 0, True)},
    "all_offline": {"default": (0, 0, 0, True)},
    "slow_verify_ok": {"default": (0.2, 3.5, 3, False)},
    "slow_verify_mismatch": {"default": (0.2, 3.5, 0, False)},
}


class FakeShef(BaseHTTPRequestHandler):
    behavior: tuple[float, float, int, bool] = (0, 0, 1, False)
    tuned_major = 0
    get_tuned_calls = 0

    def log_message(self, *_args) -> None:  # noqa: D401
        return

    def do_GET(self) -> None:  # noqa: N802
        tune_delay, get_delay, match_on_call, hang = self.behavior
        cls = type(self)
        if hang:
            time.sleep(SHEF_TIMEOUT_S + 2)
            return
        url = urlparse(self.path)
        query = parse_qs(url.query)
        if url.path == "/tv/tune":
            time.sleep(tune_delay)
            cls.tuned_major = int(query.get("major", ["0"])[0])
            cls.get_tuned_calls = 0
            body = {"status": OK_STATUS}
        elif url.path == "/tv/getTuned":
            time.sleep(get_delay)
            cls.get_tuned_calls += 1
            matched = match_on_call and cls.get_tuned_calls >= match_on_call
            major = cls.tuned_major if matched else 2
            body = {"major": major, "minor": 65535, "callsign": "FAKE", "status": OK_STATUS}
        else:
            body = {"status": OK_STATUS}
        raw = json.dumps(body).encode()
        try:
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            self.end_headers()
            self.wfile.write(raw)
        except (BrokenPipeError, ConnectionResetError):
            pass


def start_receivers(scenario: dict, count: int) -> tuple[list[ThreadingHTTPServer], dict]:
    servers: list[ThreadingHTTPServer] = []
    receivers: dict = {}
    for n in range(1, count + 1):
        rid = f"H25-{n:02d}"
        behavior = scenario.get(rid, scenario["default"])
        handler = type(
            f"Shef{n}", (FakeShef,), {"behavior": behavior, "tuned_major": 0, "get_tuned_calls": 0}
        )
        server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server.daemon_threads = True
        threading.Thread(target=server.serve_forever, daemon=True).start()
        servers.append(server)
        receivers[rid] = {"host": "127.0.0.1", "port": server.server_address[1], "client_addr": "0"}
    return servers, receivers


class UdpCounter:
    """Counts msg_b_reconnect datagrams, i.e. TV groups that really switched."""

    def __init__(self) -> None:
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.bind(("127.0.0.1", 0))
        self.sock.settimeout(0.2)
        self.port = self.sock.getsockname()[1]
        self.count = 0
        self._stop = threading.Event()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                data, _ = self.sock.recvfrom(4096)
            except OSError:
                continue
            if data.startswith(b"msg_b_reconnect"):
                self.count += 1

    def close(self) -> int:
        time.sleep(0.3)
        self._stop.set()
        self._thread.join()
        self.sock.close()
        return self.count


def write_configs(tmp: Path, receivers: dict, slots: int, udp_port: int) -> tuple[Path, Path, str]:
    inventory = {
        "network": {"broadcast": "127.0.0.1", "udp_switch_port": udp_port},
        "encoders": [{"id": f"ENC-{n:02d}", "hostname": f"IPE935-BENCH{n:02d}"} for n in range(1, 11)],
        "receivers": [{"id": f"RX-{n:02d}", "hostname": f"IPD935-BENCH{n:02d}"} for n in range(1, 36)],
    }
    directv = {
        "timeout_seconds": SHEF_TIMEOUT_S,
        "verify_tune": True,
        "encoder_to_receiver": {f"ENC-{n:02d}": f"H25-{n:02d}" for n in range(1, 11)},
        "receivers": receivers,
    }
    plan = {
        "mode": "adhoc",
        "commit": "live",
        "slots": [
            {
                "index": n,
                "encoderId": f"ENC-{n:02d}",
                "program": {"id": f"g{n}", "channelNumber": str(200 + n)},
                "tvs": [n],
                "tune": {"channelNumber": str(200 + n)},
                "udp": None,
                "status": "planned",
            }
            for n in range(1, slots + 1)
        ],
        "warnings": [],
    }
    inv_path = tmp / "inventory.yaml"
    dtv_path = tmp / "directv.yaml"
    inv_path.write_text(yaml.safe_dump(inventory))
    dtv_path.write_text(yaml.safe_dump(directv))
    plan_b64 = base64.b64encode(json.dumps(plan).encode()).decode()
    return inv_path, dtv_path, plan_b64


def run_scenario(name: str, slots: int) -> dict:
    servers, receivers = start_receivers(SCENARIOS[name], max(slots, 10))
    udp = UdpCounter()
    try:
        with tempfile.TemporaryDirectory() as tmp_name:
            inv, dtv, plan_b64 = write_configs(Path(tmp_name), receivers, slots, udp.port)
            cmd = [
                sys.executable, str(WRAPPER),
                "--inventory", str(inv), "--directv-config", str(dtv),
                "--plan-b64", plan_b64, "--live", "--live-commit", "on",
            ]
            start = time.monotonic()
            try:
                proc = subprocess.run(cmd, capture_output=True, text=True, timeout=HA_SHELL_TIMEOUT_S)
                timed_out = False
                stdout, code = proc.stdout, proc.returncode
            except subprocess.TimeoutExpired as exc:
                timed_out = True
                stdout = exc.stdout.decode() if isinstance(exc.stdout, bytes) else (exc.stdout or "")
                code = None
            wall = time.monotonic() - start
    finally:
        for server in servers:
            server.shutdown()
        udp_sent = udp.close()
    report = None
    for line in reversed([ln for ln in stdout.splitlines() if ln.strip()]):
        try:
            report = json.loads(line)
            break
        except json.JSONDecodeError:
            continue
    slots_out = (report or {}).get("slots") or []
    return {
        "scenario": name,
        "slots": slots,
        "wall_s": round(wall, 2),
        "killed_at_60s": timed_out,
        "returncode": code,
        "report": report is not None,
        "udp_sent": udp_sent,
        "ok_slots": sum(1 for s in slots_out if s.get("status") == "ok"),
        "error_slots": sum(1 for s in slots_out if s.get("status") == "error"),
        "first_error": ((report or {}).get("errors") or [None])[0],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--slots", type=int, default=9)
    parser.add_argument("--scenario", choices=sorted(SCENARIOS), action="append")
    args = parser.parse_args()
    worst = 0.0
    for name in args.scenario or list(SCENARIOS):
        result = run_scenario(name, args.slots)
        worst = max(worst, result["wall_s"])
        print(json.dumps(result), flush=True)
    return 0 if worst < HA_SHELL_TIMEOUT_S else 1


if __name__ == "__main__":
    sys.exit(main())
