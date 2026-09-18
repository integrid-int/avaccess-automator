"""Inventory loaders and validation helpers for AVAccess live routing."""

from __future__ import annotations

from pathlib import Path

import yaml


def load_inventory(path: Path) -> dict:
    """Load inventory YAML from ``path``."""
    with Path(path).open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh)
    if not isinstance(data, dict):
        raise ValueError(f"Inventory at {path} must be a mapping")
    return data


def tv_to_rx_id(tv: int) -> str:
    """Map TV number 1..35 to zero-padded receiver id (``RX-01`` … ``RX-35``)."""
    return f"RX-{int(tv):02d}"


def rx_ids_for_tvs(tvs: list[int]) -> list[str]:
    """Convert a list of TV numbers to receiver ids."""
    return [tv_to_rx_id(t) for t in tvs]


def striped_rx_ids(stripe_count: int, encoder_ordinal: int) -> list[str]:
    """Return RX ids for one encoder stripe (same formula as JS ``stripedTvs``)."""
    tvs = [t for t in range(1, 36) if (t - 1) % stripe_count == (encoder_ordinal - 1)]
    return [tv_to_rx_id(t) for t in tvs]


def _device_by_id(devices: list[dict] | None, device_id: str) -> dict | None:
    if not devices:
        return None
    for device in devices:
        if isinstance(device, dict) and device.get("id") == device_id:
            return device
    return None


def _hostname_issue(device_id: str, device: dict | None) -> str | None:
    if device is None:
        return f"Missing device {device_id}"
    hostname = device.get("hostname")
    if hostname is None or hostname == "":
        return f"Missing hostname for {device_id}"
    if "REPLACE_ME" in str(hostname):
        return f"Hostname for {device_id} still contains REPLACE_ME: {hostname}"
    return None


def _network_issues(inventory: dict) -> list[str]:
    """Require non-empty network.broadcast and network.udp_switch_port."""
    errors: list[str] = []
    net = inventory.get("network") if isinstance(inventory, dict) else None
    if not isinstance(net, dict):
        return ["Missing network.broadcast", "Missing network.udp_switch_port"]
    broadcast = net.get("broadcast")
    if broadcast is None or str(broadcast).strip() == "":
        errors.append("Missing or empty network.broadcast")
    port = net.get("udp_switch_port")
    if port is None or str(port).strip() == "":
        errors.append("Missing or empty network.udp_switch_port")
    return errors


def validate_inventory_for_plan(
    inventory: dict, plan: dict
) -> tuple[bool, list[str]]:
    """Validate that every ENC/RX referenced by ``plan`` has a real hostname."""
    errors: list[str] = []
    errors.extend(_network_issues(inventory))
    encoders = inventory.get("encoders") if isinstance(inventory, dict) else None
    receivers = inventory.get("receivers") if isinstance(inventory, dict) else None
    slots = plan.get("slots") if isinstance(plan, dict) else None
    if not isinstance(slots, list):
        return False, [*errors, "Plan has no slots list"]

    for slot in slots:
        if not isinstance(slot, dict):
            errors.append("Invalid slot entry")
            continue
        encoder_id = slot.get("encoderId")
        if not encoder_id:
            errors.append("Slot missing encoderId")
        else:
            issue = _hostname_issue(
                str(encoder_id), _device_by_id(encoders, str(encoder_id))
            )
            if issue:
                errors.append(issue)

        tvs = slot.get("tvs") or []
        if not isinstance(tvs, list):
            errors.append(f"Slot {encoder_id or '?'} has invalid tvs")
            continue
        for tv in tvs:
            rx_id = tv_to_rx_id(int(tv))
            issue = _hostname_issue(rx_id, _device_by_id(receivers, rx_id))
            if issue:
                errors.append(issue)

    return (len(errors) == 0, errors)


def is_inventory_live_ready(inventory: dict) -> tuple[bool, list[str]]:
    """True only if all 10 encoders and 35 receivers have real hostnames."""
    errors: list[str] = []
    errors.extend(_network_issues(inventory))
    encoders = inventory.get("encoders") if isinstance(inventory, dict) else None
    receivers = inventory.get("receivers") if isinstance(inventory, dict) else None

    for i in range(1, 11):
        enc_id = f"ENC-{i:02d}"
        issue = _hostname_issue(enc_id, _device_by_id(encoders, enc_id))
        if issue:
            errors.append(issue)

    for i in range(1, 36):
        rx_id = tv_to_rx_id(i)
        issue = _hostname_issue(rx_id, _device_by_id(receivers, rx_id))
        if issue:
            errors.append(issue)

    return (len(errors) == 0, errors)
