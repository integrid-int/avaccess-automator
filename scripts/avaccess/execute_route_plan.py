#!/usr/bin/env python3
"""Execute a Track A RoutePlan: IR tune per slot, then UDP reconnect."""

from __future__ import annotations

import argparse
import base64
import copy
import json
import sys
from pathlib import Path
from typing import Any

import yaml

from scripts.avaccess.enrich_plan import enrich_route_plan
from scripts.avaccess import ir_itach
from scripts.avaccess import udp_reconnect
from scripts.avaccess.inventory_lib import load_inventory, validate_inventory_for_plan


class PreflightError(Exception):
    """Raised when live execution cannot start (invalid inventory / plan)."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__(
            "; ".join(self.errors) if self.errors else "Preflight failed"
        )


def send_ir_digits(**kwargs: Any) -> Any:
    """Module-level IR sender (monkeypatch target for tests)."""
    return ir_itach.send_ir_digits(**kwargs)


def send_udp_reconnect(**kwargs: Any) -> Any:
    """Module-level UDP sender (monkeypatch target for tests)."""
    return udp_reconnect.send_udp_reconnect(**kwargs)


def _any_udp_null(plan: dict) -> bool:
    slots = plan.get("slots") or []
    for slot in slots:
        if isinstance(slot, dict) and slot.get("udp") is None:
            return True
    return False


def _network_settings(inventory: dict) -> tuple[str, int]:
    net = inventory.get("network") or {}
    broadcast = str(net.get("broadcast", "255.255.255.255"))
    port = int(net.get("udp_switch_port", 5010))
    return broadcast, port


def execute_plan(
    plan: dict,
    inventory: dict,
    itach: dict,
    *,
    live: bool = False,
    digit_delay_ms: int = 250,
    session_start: int = 1,
) -> dict:
    """Run IR then UDP for each slot; continue on errors; return a report."""
    working = copy.deepcopy(plan)

    if _any_udp_null(working):
        try:
            working = enrich_route_plan(working, inventory)
        except ValueError as exc:
            raise PreflightError([str(exc)]) from exc

    if live:
        ok, errors = validate_inventory_for_plan(inventory, working)
        if not ok:
            raise PreflightError(errors)

    broadcast, port = _network_settings(inventory)
    dry_run = not live
    session = int(session_start)
    report_errors: list[str] = []
    slots_out: list[dict] = []

    for slot in working.get("slots") or []:
        if not isinstance(slot, dict):
            msg = "Invalid slot entry"
            report_errors.append(msg)
            slots_out.append({"status": "error", "message": msg})
            continue

        slot_out = copy.deepcopy(slot)
        encoder_id = str(slot.get("encoderId") or "")
        try:
            tune = slot.get("tune") or {}
            channel = None
            if isinstance(tune, dict):
                channel = tune.get("channelNumber")
            if channel is not None and str(channel) != "":
                send_ir_digits(
                    digits=str(channel),
                    encoder_id=encoder_id,
                    itach=itach,
                    digit_delay_ms=digit_delay_ms,
                    dry_run=dry_run,
                )

            udp = slot.get("udp") or {}
            tx = str(udp.get("txHostname") or "")
            rxs = list(udp.get("rxHostnames") or [])
            if not tx or not rxs:
                raise ValueError(f"Slot {encoder_id or '?'} missing udp hostnames")

            send_udp_reconnect(
                tx_hostname=tx,
                rx_hostnames=rxs,
                broadcast=broadcast,
                port=port,
                session=session,
                dry_run=dry_run,
            )
            slot_out["status"] = "ok"
            if "message" in slot_out:
                del slot_out["message"]
        except Exception as exc:  # noqa: BLE001 — per-slot continue
            msg = str(exc)
            slot_out["status"] = "error"
            slot_out["message"] = msg
            report_errors.append(f"{encoder_id or '?'}: {msg}")
        finally:
            session += 1

        slots_out.append(slot_out)

    return {
        "ok": len(report_errors) == 0,
        "slots": slots_out,
        "errors": report_errors,
    }


def _load_plan(plan_file: Path | None, plan_b64: str | None) -> dict:
    if plan_file is not None:
        data = json.loads(Path(plan_file).read_text(encoding="utf-8"))
    elif plan_b64:
        raw = base64.b64decode(plan_b64)
        data = json.loads(raw.decode("utf-8"))
    else:
        raise PreflightError(["Provide --plan-file or --plan-b64"])
    if not isinstance(data, dict):
        raise PreflightError(["Plan JSON must be an object"])
    return data


def _load_yaml(path: Path) -> dict:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, dict):
        raise PreflightError([f"Expected YAML mapping in {path}"])
    return data


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--itach-config", type=Path, required=True)
    parser.add_argument("--plan-file", type=Path, default=None)
    parser.add_argument("--plan-b64", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=False)
    mode.add_argument("--live", action="store_true", default=False)
    parser.add_argument("--digit-delay-ms", type=int, default=250)
    parser.add_argument("--session-start", type=int, default=1)
    args = parser.parse_args(argv)

    live = bool(args.live)
    if not args.live and not args.dry_run:
        # Default hybrid posture: dry-run.
        live = False

    try:
        inventory = load_inventory(args.inventory)
        itach = _load_yaml(args.itach_config)
        plan = _load_plan(args.plan_file, args.plan_b64)
        report = execute_plan(
            plan,
            inventory=inventory,
            itach=itach,
            live=live,
            digit_delay_ms=int(args.digit_delay_ms),
            session_start=int(args.session_start),
        )
    except PreflightError as exc:
        print(
            json.dumps({"ok": False, "slots": [], "errors": exc.errors}),
            flush=True,
        )
        return 2
    except Exception as exc:  # noqa: BLE001
        print(
            json.dumps({"ok": False, "slots": [], "errors": [str(exc)]}),
            flush=True,
        )
        return 2

    print(json.dumps(report), flush=True)
    return 0 if report["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
