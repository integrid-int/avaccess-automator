#!/usr/bin/env python3
"""Route one encoder to one or many receivers via AVAccess UDP reconnect.

Usage:
  python3 scripts/route_targets.py \
    --inventory config/inventory.yaml \
    --encoder ENC-01 \
    --targets RX-01,RX-02,RX-10
"""

from __future__ import annotations

import argparse
import socket
from pathlib import Path
from typing import Any

import yaml


def load_inventory(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def index_by(items: list[dict[str, Any]], key: str) -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for item in items:
        value = str(item.get(key, "")).strip()
        if value:
            out[value] = item
    return out


def parse_targets(raw: str) -> list[str]:
    tokens: list[str] = []
    for part in raw.replace("\n", ",").replace(" ", ",").split(","):
        token = part.strip()
        if token:
            tokens.append(token)
    # dedupe preserve order
    seen: set[str] = set()
    out: list[str] = []
    for t in tokens:
        if t in seen:
            continue
        seen.add(t)
        out.append(t)
    return out


def resolve_encoder(enc_token: str, encoders: list[dict[str, Any]]) -> dict[str, Any]:
    by_id = index_by(encoders, "id")
    by_host = index_by(encoders, "hostname")
    if enc_token in by_id:
        return by_id[enc_token]
    if enc_token in by_host:
        return by_host[enc_token]
    available = ", ".join(sorted(by_id.keys())[:10])
    raise SystemExit(f"Unknown encoder '{enc_token}'. Example IDs: {available}")


def resolve_receivers(tokens: list[str], receivers: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_id = index_by(receivers, "id")
    by_host = index_by(receivers, "hostname")
    resolved: list[dict[str, Any]] = []
    for token in tokens:
        if token in by_id:
            resolved.append(by_id[token])
            continue
        if token in by_host:
            resolved.append(by_host[token])
            continue
        raise SystemExit(f"Unknown receiver token '{token}'. Use RX ID (e.g., RX-01) or hostname.")
    return resolved


def build_message(tx_hostname: str, session: int, rx_hostnames: list[str]) -> bytes:
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


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--encoder", required=True, help="Encoder ID or hostname")
    parser.add_argument("--targets", required=True, help="Comma/space separated RX IDs or hostnames")
    parser.add_argument("--session", type=int, default=1)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    inv = load_inventory(args.inventory)
    encoders = inv.get("encoders", [])
    receivers = inv.get("receivers", [])
    if not isinstance(encoders, list) or not isinstance(receivers, list):
        raise SystemExit("Inventory must include list fields: encoders, receivers")

    encoder = resolve_encoder(str(args.encoder), encoders)
    if "REPLACE_ME" in str(encoder.get("hostname", "")):
        raise SystemExit(f"{encoder.get('id', 'encoder')} has REPLACE_ME hostname")

    target_tokens = parse_targets(str(args.targets))
    if not target_tokens:
        raise SystemExit("No target receivers parsed from --targets")
    rxs = resolve_receivers(target_tokens, receivers)
    rx_hostnames: list[str] = []
    for rx in rxs:
        host = str(rx.get("hostname", ""))
        if "REPLACE_ME" in host or not host:
            raise SystemExit(f"{rx.get('id', 'receiver')} has invalid hostname")
        rx_hostnames.append(host)

    net = inv.get("network", {})
    broadcast = str(net.get("broadcast", "255.255.255.255"))
    port = int(net.get("udp_switch_port", 5010))

    payload = build_message(str(encoder["hostname"]), int(args.session), rx_hostnames)
    send_udp(payload, broadcast=broadcast, port=port, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
