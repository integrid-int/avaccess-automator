"""Enrich RoutePlan slots with TX/RX UDP hostnames and tune targets."""

from __future__ import annotations

import copy

from scripts.avaccess.inventory_lib import (
    tv_to_rx_id,
    validate_inventory_for_plan,
)


def _device_hostname(devices: list[dict] | None, device_id: str) -> str:
    if not devices:
        raise ValueError(f"Missing device {device_id}")
    for device in devices:
        if isinstance(device, dict) and device.get("id") == device_id:
            hostname = device.get("hostname")
            if not hostname:
                raise ValueError(f"Missing hostname for {device_id}")
            return str(hostname)
    raise ValueError(f"Missing device {device_id}")


def enrich_route_plan(plan: dict, inventory: dict) -> dict:
    """Copy ``plan`` and fill each slot's ``udp`` / ``tune`` from inventory.

    Does not send network traffic. Raises ``ValueError`` if validation fails.
    """
    ok, errors = validate_inventory_for_plan(inventory, plan)
    if not ok:
        raise ValueError("; ".join(errors) if errors else "Inventory validation failed")

    out = copy.deepcopy(plan)
    encoders = inventory.get("encoders")
    receivers = inventory.get("receivers")
    slots = out.get("slots") or []

    for slot in slots:
        if not isinstance(slot, dict):
            continue
        encoder_id = str(slot.get("encoderId") or "")
        tx_hostname = _device_hostname(encoders, encoder_id)
        tvs = slot.get("tvs") or []
        rx_hostnames = [
            _device_hostname(receivers, tv_to_rx_id(int(tv))) for tv in tvs
        ]
        slot["udp"] = {
            "txHostname": tx_hostname,
            "rxHostnames": rx_hostnames,
        }

        program = slot.get("program") or {}
        channel_number = None
        if isinstance(program, dict):
            channel_number = program.get("channelNumber")
        if channel_number is not None and channel_number != "":
            slot["tune"] = {"channelNumber": str(channel_number)}

    return out
