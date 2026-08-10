#!/usr/bin/env python3
"""Apply AVAccess 4KIP200 matrix presets via UDP bulk reconnect (port 5010).

Usage:
  python3 apply_preset.py --inventory inventory.yaml --preset 1_all [--dry-run]

Protocol (API §8):
  msg_b_reconnect <TX_HOSTNAME>:<session>:<rx_count> <RX_HOSTNAME> ...
  sent as UDP datagram to broadcast:5010
"""

from __future__ import annotations

import argparse
import socket
import sys
import time
from pathlib import Path

try:
    import yaml
except ImportError:
    print("PyYAML required: pip install pyyaml", file=sys.stderr)
    sys.exit(1)


def load_inventory(path: Path) -> dict:
    data = yaml.safe_load(path.read_text())
    if not data:
        raise SystemExit(f"Empty inventory: {path}")
    return data


def index_by_id(items: list[dict]) -> dict[str, dict]:
    return {item["id"]: item for item in items}


def build_message(tx_hostname: str, session: int, rx_hostnames: list[str]) -> bytes:
    # msg_b_reconnect IPE935-...:1:2 IPD935-... IPD935-...
    header = f"msg_b_reconnect {tx_hostname}:{session}:{len(rx_hostnames)}"
    body = " ".join(rx_hostnames)
    return f"{header} {body}".encode("ascii")


def send_udp(payload: bytes, broadcast: str, port: int, dry_run: bool) -> None:
    if dry_run:
        print(f"[dry-run] UDP {broadcast}:{port} -> {payload.decode('ascii')}")
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (broadcast, port))
        print(f"sent ({len(payload)} bytes) -> {broadcast}:{port}")
        print(payload.decode("ascii"))
    finally:
        sock.close()


def apply_preset(inventory: dict, preset_name: str, dry_run: bool, delay_s: float) -> None:
    encoders = index_by_id(inventory["encoders"])
    receivers = index_by_id(inventory["receivers"])
    presets = inventory["presets"]
    if preset_name not in presets:
        raise SystemExit(
            f"Unknown preset '{preset_name}'. Available: {', '.join(presets)}"
        )

    net = inventory.get("network", {})
    broadcast = net.get("broadcast", "255.255.255.255")
    port = int(net.get("udp_switch_port", 5010))

    routes = presets[preset_name]["routes"]
    session = 1
    for enc_id, rx_ids in routes.items():
        if not rx_ids:
            print(f"skip {enc_id}: no receivers listed")
            continue
        enc = encoders[enc_id]
        rx_hostnames = []
        for rx_id in rx_ids:
            rx = receivers[rx_id]
            for key in ("hostname",):
                if "REPLACE_ME" in str(rx.get(key, "")):
                    raise SystemExit(f"{rx_id} still has REPLACE_ME placeholders")
            rx_hostnames.append(rx["hostname"])
        if "REPLACE_ME" in enc["hostname"]:
            raise SystemExit(f"{enc_id} still has REPLACE_ME placeholders")

        payload = build_message(enc["hostname"], session, rx_hostnames)
        print(f"\n=== {enc_id} -> {len(rx_hostnames)} RXs (session {session}) ===")
        send_udp(payload, broadcast, port, dry_run=dry_run)
        session += 1
        if delay_s > 0 and session <= len(routes):
            time.sleep(delay_s)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--inventory",
        type=Path,
        default=Path(__file__).resolve().parent.parent / "config" / "inventory.yaml",
    )
    parser.add_argument(
        "--preset",
        required=True,
        help="Preset key from inventory YAML (e.g. 1_all, 2_four_programs, 3_nine_programs)",
    )
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument(
        "--delay",
        type=float,
        default=0.15,
        help="Delay between group UDP sends (seconds)",
    )
    args = parser.parse_args()

    inventory = load_inventory(args.inventory)
    apply_preset(inventory, args.preset, dry_run=args.dry_run, delay_s=args.delay)


if __name__ == "__main__":
    main()
