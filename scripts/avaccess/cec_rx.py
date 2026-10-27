"""HDMI-CEC power and volume through each AVAccess receiver.

Power uses ``sinkpower on`` / ``sinkpower off`` on every commissioned RX.
Volume and mute use ``cec -s`` on one RX. Telnet is port 24, user ``root``,
per the 4KIP200 API guide. Commands run in parallel so 35 sessions stay
inside Home Assistant's shell timeout.
"""

from __future__ import annotations

import argparse
import json
import socket
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

from scripts.avaccess.inventory_lib import load_inventory, tv_to_rx_id

POWER_COMMANDS = {
    "power-on": "sinkpower on",
    "power-off": "sinkpower off",
}
VOLUME_COMMANDS = {
    "volume-up": 'cec -s "40 44 41; 40 45"',
    "volume-down": 'cec -s "40 44 42; 40 45"',
    "mute": 'cec -s "40 44 43; 40 45"',
}
ACTIONS = {**POWER_COMMANDS, **VOLUME_COMMANDS}

IAC = 255
WILL, WONT, DO, DONT = 251, 252, 253, 254
SB, SE = 250, 240

DEFAULT_PORT = 24
DEFAULT_TIMEOUT = 5.0
DEFAULT_WORKERS = 8


def command_for(action: str) -> str:
    """Return the RX shell command for a panel action name."""
    try:
        return ACTIONS[action]
    except KeyError as exc:
        raise ValueError(f"Unknown CEC action: {action}") from exc


def _ipv4(value: object) -> bool:
    text = str(value or "").strip()
    parts = text.split(".")
    if len(parts) != 4:
        return False
    try:
        return all(part.isdigit() and 0 <= int(part) <= 255 for part in parts)
    except ValueError:
        return False


def _commissioned(device: dict) -> bool:
    hostname = str(device.get("hostname") or "")
    return bool(hostname.strip()) and "REPLACE_ME" not in hostname and _ipv4(device.get("ip"))


def targets_for(inventory: dict, action: str, tv: int) -> list[dict]:
    """Receivers that should receive ``action``.

    Power fans out to every commissioned RX. Volume and mute use one TV,
    numbered 1 through 35.
    """
    command_for(action)
    receivers = inventory.get("receivers") if isinstance(inventory, dict) else None
    if not isinstance(receivers, list):
        raise ValueError("Inventory has no receivers list")
    net = inventory.get("network") if isinstance(inventory.get("network"), dict) else {}
    port = int(net.get("telnet_port") or DEFAULT_PORT)
    if action in POWER_COMMANDS:
        chosen = [rx for rx in receivers if isinstance(rx, dict) and _commissioned(rx)]
    else:
        if not isinstance(tv, int) or tv < 1 or tv > 35:
            raise ValueError("Volume and mute need a TV from 1 to 35")
        rx_id = tv_to_rx_id(tv)
        match = next(
            (rx for rx in receivers if isinstance(rx, dict) and rx.get("id") == rx_id),
            None,
        )
        if match is None or not _commissioned(match):
            raise ValueError(f"{rx_id} is not a commissioned receiver")
        chosen = [match]
    return [
        {"id": str(rx["id"]), "ip": str(rx["ip"]).strip(), "port": port}
        for rx in chosen
    ]


def _consume_telnet(sock: socket.socket, buf: bytearray) -> tuple[bytes, bytearray]:
    """Drop Telnet negotiations and return the text plus any incomplete tail."""
    out = bytearray()
    index = 0
    while index < len(buf):
        if buf[index] != IAC:
            out.append(buf[index])
            index += 1
            continue
        if index + 1 >= len(buf):
            return bytes(out), buf[index:]
        cmd = buf[index + 1]
        if cmd == IAC:
            out.append(IAC)
            index += 2
            continue
        if cmd in (WILL, WONT, DO, DONT):
            if index + 2 >= len(buf):
                return bytes(out), buf[index:]
            reply = WONT if cmd in (DO, DONT) else DONT
            sock.sendall(bytes((IAC, reply, buf[index + 2])))
            index += 3
            continue
        if cmd == SB:
            end = -1
            for cursor in range(index + 2, len(buf) - 1):
                if buf[cursor] == IAC and buf[cursor + 1] == SE:
                    end = cursor
                    break
            if end < 0:
                return bytes(out), buf[index:]
            index = end + 2
            continue
        index += 2
    return bytes(out), bytearray()


def _read_until(sock: socket.socket, marker: bytes, deadline: float) -> bytes:
    data = bytearray()
    pending = bytearray()
    while marker not in data:
        if time.monotonic() > deadline:
            raise TimeoutError(f"timed out waiting for {marker!r}")
        chunk = sock.recv(512)
        if not chunk:
            raise ConnectionError("receiver closed the connection")
        pending.extend(chunk)
        cleaned, pending = _consume_telnet(sock, pending)
        data.extend(cleaned)
    return bytes(data)


def send_rx_command(
    ip: str,
    port: int,
    command: str,
    timeout: float = DEFAULT_TIMEOUT,
    connect=socket.create_connection,
) -> None:
    """Log in as root and run one shell command. Raises on failure."""
    if any(char in command for char in "\r\n"):
        raise ValueError("CEC command must be a single line")
    deadline = time.monotonic() + timeout
    sock = connect((ip, int(port)), timeout)
    try:
        sock.settimeout(timeout)
        _read_until(sock, b"login:", deadline)
        sock.sendall(b"root\r\n")
        _read_until(sock, b"#", deadline)
        sock.sendall(command.encode("ascii") + b"\r\n")
        _read_until(sock, b"#", deadline)
    finally:
        sock.close()


def run_cec(
    inventory: dict,
    action: str,
    tv: int = 0,
    *,
    live: bool = False,
    live_commit: str = "off",
    sender=send_rx_command,
    workers: int = DEFAULT_WORKERS,
) -> dict:
    """Build the report the panel reads. No sockets unless ``live`` is allowed."""
    if live and live_commit != "on":
        return {
            "ok": False,
            "refused": True,
            "action": action,
            "errors": ["Live Commit is off in Home Assistant. Nothing was sent."],
            "results": [],
        }
    try:
        command = command_for(action)
        targets = targets_for(inventory, action, tv)
    except ValueError as exc:
        return {"ok": False, "action": action, "errors": [str(exc)], "results": []}
    if not targets:
        return {
            "ok": False,
            "action": action,
            "errors": ["No commissioned receivers to control."],
            "results": [],
        }
    if not live:
        return {
            "ok": True,
            "dryRun": True,
            "action": action,
            "command": command,
            "targets": [item["id"] for item in targets],
            "results": [],
        }

    results: list[dict] = []
    with ThreadPoolExecutor(max_workers=max(1, workers)) as pool:
        futures = {
            pool.submit(sender, item["ip"], item["port"], command): item for item in targets
        }
        for future in as_completed(futures):
            item = futures[future]
            try:
                future.result()
            except Exception as exc:  # noqa: BLE001 - one RX must not abort the rest
                results.append({"id": item["id"], "ok": False, "error": str(exc)})
            else:
                results.append({"id": item["id"], "ok": True})
    results.sort(key=lambda row: row["id"])
    failed = [row for row in results if not row["ok"]]
    return {
        "ok": not failed,
        "action": action,
        "accepted": len(results) - len(failed),
        "errors": [f"{row['id']}: {row['error']}" for row in failed],
        "results": results,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Send HDMI-CEC via AVAccess receivers")
    parser.add_argument("--inventory", required=True)
    parser.add_argument("--action", required=True)
    parser.add_argument("--tv", type=int, default=0)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--live-commit", default="off")
    args = parser.parse_args(argv)
    inventory = load_inventory(Path(args.inventory))
    report = run_cec(
        inventory,
        args.action,
        args.tv,
        live=args.live,
        live_commit=args.live_commit,
    )
    print(json.dumps(report))
    if report.get("refused"):
        return 3
    return 0 if report.get("ok") else 1


if __name__ == "__main__":
    raise SystemExit(main())
