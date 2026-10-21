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


def resolve_presets(inventory: dict, profile_override: str | None) -> tuple[str | None, dict]:
    """Return (profile_name, presets) with backward compatibility.

    Supported inventory styles:
    1) Legacy:
       presets: {...}
    2) Profile-based:
       mapping_profiles:
         active: numeric
         profiles:
           numeric:
             presets: {...}
           zones:
             presets: {...}
    """
    mapping_profiles = inventory.get("mapping_profiles")
    if not mapping_profiles:
        presets = inventory.get("presets")
        if not presets:
            raise SystemExit("Inventory must include 'presets' or 'mapping_profiles'")
        return None, presets

    profiles = mapping_profiles.get("profiles", {})
    if not profiles:
        raise SystemExit("mapping_profiles.profiles is empty")

    selected = profile_override or mapping_profiles.get("active")
    if not selected:
        selected = next(iter(profiles))
    if selected not in profiles:
        available = ", ".join(profiles.keys())
        raise SystemExit(
            f"Unknown mapping profile '{selected}'. Available profiles: {available}"
        )

    profile_data = profiles[selected]
    presets = profile_data.get("presets", {})
    if not presets:
        raise SystemExit(f"mapping_profiles.profiles.{selected}.presets is empty")
    return selected, presets


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


def _hostname_error(kind: str, item_id: str, item: dict) -> str | None:
    hostname = str(item.get("hostname") or "").strip()
    if not hostname:
        return f"{kind} {item_id} has no hostname"
    if "REPLACE_ME" in hostname:
        return f"{item_id} still has REPLACE_ME placeholders"
    try:
        hostname.encode("ascii")
    except UnicodeEncodeError:
        return f"{kind} {item_id} hostname is not ASCII: {hostname!r}"
    if any(ch.isspace() or ch == ":" for ch in hostname):
        return f"{kind} {item_id} hostname has invalid characters: {hostname!r}"
    return None


def plan_preset_messages(
    inventory: dict,
    preset_name: str,
    mapping_profile: str | None,
) -> tuple[str | None, list[tuple[str, int, bytes]], list[str]]:
    """Validate every route in the preset and build all UDP payloads.

    Returns (profile, messages, skipped) where messages are
    (encoder_id, rx_count, payload). Raises SystemExit listing every
    problem found, so no datagram is sent for a partially valid preset.
    """
    encoders = index_by_id(inventory.get("encoders") or [])
    receivers = index_by_id(inventory.get("receivers") or [])
    selected_profile, presets = resolve_presets(inventory, mapping_profile)
    if preset_name not in presets:
        raise SystemExit(
            f"Unknown preset '{preset_name}'. Available: {', '.join(presets)}"
        )

    preset = presets[preset_name]
    routes = preset.get("routes") if isinstance(preset, dict) else None
    if not isinstance(routes, dict) or not routes:
        raise SystemExit(f"Preset '{preset_name}' has no routes")

    errors: list[str] = []
    skipped: list[str] = []
    validated: list[tuple[str, str, list[str]]] = []
    claimed_rx: dict[str, str] = {}
    for enc_id, rx_ids in routes.items():
        enc_id = str(enc_id)
        if not rx_ids:
            skipped.append(enc_id)
            continue
        if not isinstance(rx_ids, list):
            errors.append(f"{enc_id}: receivers must be a list")
            continue
        route_errors: list[str] = []
        enc = encoders.get(enc_id)
        if enc is None:
            route_errors.append(f"{enc_id}: unknown encoder")
        else:
            err = _hostname_error("encoder", enc_id, enc)
            if err:
                route_errors.append(err)
        rx_hostnames: list[str] = []
        for rx_id in rx_ids:
            rx_id = str(rx_id)
            rx = receivers.get(rx_id)
            if rx is None:
                route_errors.append(f"{enc_id}: unknown receiver {rx_id}")
                continue
            err = _hostname_error("receiver", rx_id, rx)
            if err:
                route_errors.append(err)
                continue
            owner = claimed_rx.get(rx_id)
            if owner is not None:
                route_errors.append(f"{rx_id} assigned to both {owner} and {enc_id}")
                continue
            claimed_rx[rx_id] = enc_id
            rx_hostnames.append(str(rx["hostname"]).strip())
        if route_errors:
            errors.extend(route_errors)
            continue
        validated.append((enc_id, str(enc["hostname"]).strip(), rx_hostnames))

    if errors:
        raise SystemExit(
            f"Preset '{preset_name}' failed preflight; nothing sent:\n  "
            + "\n  ".join(errors)
        )

    messages = [
        (enc_id, len(rx_hostnames), build_message(tx, session, rx_hostnames))
        for session, (enc_id, tx, rx_hostnames) in enumerate(validated, start=1)
    ]
    return selected_profile, messages, skipped


def apply_preset(
    inventory: dict,
    preset_name: str,
    dry_run: bool,
    delay_s: float,
    mapping_profile: str | None,
) -> None:
    selected_profile, messages, skipped = plan_preset_messages(
        inventory, preset_name, mapping_profile
    )
    if selected_profile:
        print(f"using mapping profile: {selected_profile}")
    for enc_id in skipped:
        print(f"skip {enc_id}: no receivers listed")

    net = inventory.get("network", {})
    broadcast = net.get("broadcast", "255.255.255.255")
    port = int(net.get("udp_switch_port", 5010))

    for session, (enc_id, rx_count, payload) in enumerate(messages, start=1):
        print(f"\n=== {enc_id} -> {rx_count} RXs (session {session}) ===")
        send_udp(payload, broadcast, port, dry_run=dry_run)
        if delay_s > 0 and session < len(messages):
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
    parser.add_argument(
        "--profile",
        help="Optional mapping profile key (when inventory uses mapping_profiles).",
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
    apply_preset(
        inventory,
        args.preset,
        dry_run=args.dry_run,
        delay_s=args.delay,
        mapping_profile=args.profile,
    )


if __name__ == "__main__":
    main()
