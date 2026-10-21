#!/usr/bin/env python3
"""Execute a Track A RoutePlan: DirecTV SHEF tune per slot, then UDP reconnect."""

from __future__ import annotations

import argparse
import base64
import binascii
import copy
import importlib.util
import json
import re
import sys
import time
from pathlib import Path
from typing import Any, Callable

_ROOT = Path(__file__).resolve().parents[2]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

import yaml

from scripts.avaccess.enrich_plan import enrich_route_plan
from scripts.avaccess import udp_reconnect
from scripts.avaccess.inventory_lib import load_inventory, validate_inventory_for_plan

# Home Assistant kills a shell_command after 60 s and the caller then gets no
# report at all, even for slots whose TVs already switched. Live stops starting
# slots early enough to print its report inside this budget; the rest of the
# 60 s covers interpreter start-up and HA overhead.
LIVE_TIME_BUDGET_S = 50.0


class PreflightError(Exception):
    """Raised when live execution cannot start (invalid inventory / plan)."""

    def __init__(self, errors: list[str]):
        self.errors = list(errors)
        super().__init__(
            "; ".join(self.errors) if self.errors else "Preflight failed"
        )


def _load_shef_module() -> Any:
    """Load SHEF helpers from repo package or HA overlay next to this file."""
    try:
        from scripts import directv_shef as shef

        return shef
    except ImportError:
        pass
    here = Path(__file__).resolve().parent
    candidates = [
        here / "directv_shef.py",
        here.parent / "directv_shef.py",
    ]
    for path in candidates:
        if not path.is_file():
            continue
        spec = importlib.util.spec_from_file_location("directv_shef", path)
        if spec is None or spec.loader is None:
            continue
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        return mod
    raise ImportError(
        "directv_shef.py not found (expected scripts.directv_shef or overlay "
        "next to execute_route_plan.py)"
    )


def send_directv_tune(
    *,
    channel: str,
    encoder_id: str,
    directv: dict,
    dry_run: bool = False,
    timeout: float | None = None,
) -> Any:
    """Module-level SHEF tuner (monkeypatch target for tests).

    Raises on non-success SHEF body status, and (unless ``verify_tune: false``
    in directv config) when /tv/getTuned does not confirm the channel, so the
    caller fails the slot before any UDP send.
    """
    shef = _load_shef_module()
    try:
        major, minor = shef.parse_channel(str(channel))
        recv = shef.resolve_receiver(directv, encoder_id)
    except SystemExit as exc:
        raise ValueError(str(exc) or "SHEF config/channel invalid") from exc
    if timeout is None:
        timeout = float(directv.get("timeout_seconds") or shef.DEFAULT_TIMEOUT)
    if dry_run:
        print(
            f"[dry-run] SHEF {recv.get('host')}:{recv.get('port')} "
            f"GET /tv/tune?major={major}&minor={minor} encoder={encoder_id}"
        )
        return {
            "dry_run": True,
            "encoder": encoder_id,
            "major": major,
            "minor": minor,
            "host": recv.get("host"),
        }
    verify = bool(directv.get("verify_tune", True))
    try:
        return shef.tune_and_verify(recv, major, minor, timeout, verify=verify)
    except SystemExit as exc:
        raise RuntimeError(str(exc) or "SHEF tune failed") from exc


def send_udp_reconnect(**kwargs: Any) -> Any:
    """Module-level UDP sender (monkeypatch target for tests)."""
    return udp_reconnect.send_udp_reconnect(**kwargs)


def worst_case_slot_seconds(directv: dict) -> float:
    """Longest one live slot can take: SHEF tune plus every getTuned poll timing out."""
    shef = _load_shef_module()
    timeout = float(directv.get("timeout_seconds") or shef.DEFAULT_TIMEOUT)
    if not bool(directv.get("verify_tune", True)):
        return timeout
    attempts = max(1, int(getattr(shef, "VERIFY_ATTEMPTS", 3)))
    delay = float(getattr(shef, "VERIFY_DELAY_S", 0.5))
    return timeout * (1 + attempts) + delay * (attempts - 1)


def _not_attempted_message(budget_s: float) -> str:
    return (
        f"Not attempted: the Live Take reached its {budget_s:.0f} s time limit "
        "before this slot. Nothing was sent; these TVs keep their previous source."
    )


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


def _slot_tune_channel(slot: dict) -> str | None:
    tune = slot.get("tune") if isinstance(slot, dict) else None
    if not isinstance(tune, dict):
        return None
    channel = tune.get("channelNumber")
    if channel is None:
        return None
    text = str(channel).strip()
    return text or None


def _missing_tune_errors(plan: dict) -> list[str]:
    errors: list[str] = []
    for slot in plan.get("slots") or []:
        if not isinstance(slot, dict):
            continue
        if _slot_tune_channel(slot) is not None:
            continue
        encoder_id = str(slot.get("encoderId") or "?")
        program = slot.get("program") if isinstance(slot.get("program"), dict) else {}
        label = program.get("label")
        suffix = f" ({label})" if label else ""
        errors.append(f"{encoder_id}{suffix}: missing tune channel")
    return errors


def _directv_map_errors(directv: dict, plan: dict) -> list[str]:
    """Slots that will SHEF-tune must have a mapped H25 before any UDP send."""
    mapping = directv.get("encoder_to_receiver")
    receivers = directv.get("receivers")
    if not isinstance(mapping, dict) or not isinstance(receivers, dict):
        return ["directv config needs encoder_to_receiver and receivers"]
    errors: list[str] = []
    for slot in plan.get("slots") or []:
        if not isinstance(slot, dict):
            continue
        tune = slot.get("tune") or {}
        channel = tune.get("channelNumber") if isinstance(tune, dict) else None
        if channel is None or str(channel) == "":
            continue
        encoder_id = str(slot.get("encoderId") or "")
        recv_id = mapping.get(encoder_id)
        recv = receivers.get(recv_id) if recv_id else None
        if not isinstance(recv, dict):
            errors.append(f"{encoder_id or '?'}: no DirecTV receiver mapped")
            continue
        if not str(recv.get("host") or "").strip():
            errors.append(f"{encoder_id}: receiver {recv_id} has empty host")
    return errors


def execute_plan(
    plan: dict,
    inventory: dict,
    directv: dict,
    *,
    live: bool = False,
    session_start: int = 1,
    time_budget_s: float = LIVE_TIME_BUDGET_S,
    clock: Callable[[], float] = time.monotonic,
) -> dict:
    """Run SHEF tune then UDP for each slot; continue on errors; return a report.

    Live starts a slot only if it can finish, at its worst case, inside
    ``time_budget_s``; later slots are reported as not attempted.
    """
    started = clock()
    working = copy.deepcopy(plan)

    # Live never trusts caller-supplied udp hostnames; only inventory decides
    # which TX/RX boxes receive the reconnect.
    if live or _any_udp_null(working):
        try:
            working = enrich_route_plan(working, inventory)
        except ValueError as exc:
            raise PreflightError([str(exc)]) from exc

    if live:
        ok, errors = validate_inventory_for_plan(inventory, working)
        errors.extend(_directv_map_errors(directv, working))
        errors.extend(_missing_tune_errors(working))
        if not ok or errors:
            raise PreflightError(errors)
        slot_worst_s = worst_case_slot_seconds(directv)
        if slot_worst_s > time_budget_s:
            raise PreflightError(
                [
                    f"directv timeout_seconds {directv.get('timeout_seconds')} is too long: "
                    f"one slot can take {slot_worst_s:.1f} s, over the "
                    f"{time_budget_s:.0f} s Live limit. Use timeout_seconds 4."
                ]
            )

    broadcast, port = _network_settings(inventory)
    dry_run = not live
    session = int(session_start)
    report_errors: list[str] = []
    slots_out: list[dict] = []

    for slot in working.get("slots") or []:
        if not isinstance(slot, dict):
            msg = "Invalid slot entry"
            report_errors.append(msg)
            slots_out.append({"status": "error", "error": msg, "message": msg})
            continue

        slot_out = copy.deepcopy(slot)
        encoder_id = str(slot.get("encoderId") or "")
        slot_started = clock()
        if live and (slot_started - started) + slot_worst_s > time_budget_s:
            msg = _not_attempted_message(time_budget_s)
            slot_out["status"] = "error"
            slot_out["error"] = msg
            slot_out["message"] = msg
            report_errors.append(f"{encoder_id or '?'}: {msg}")
            slots_out.append(slot_out)
            continue
        try:
            channel = _slot_tune_channel(slot)
            if channel:
                send_directv_tune(
                    channel=channel,
                    encoder_id=encoder_id,
                    directv=directv,
                    dry_run=dry_run,
                )
            elif live:
                raise ValueError(f"Slot {encoder_id or '?'} missing tune channel")

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
            for key in ("error", "message"):
                if key in slot_out:
                    del slot_out[key]
        except Exception as exc:  # noqa: BLE001 — per-slot continue
            msg = str(exc)
            slot_out["status"] = "error"
            slot_out["error"] = msg
            slot_out["message"] = msg  # alias for older consumers
            report_errors.append(f"{encoder_id or '?'}: {msg}")
        finally:
            session += 1
            slot_out["elapsedMs"] = round((clock() - slot_started) * 1000)

        slots_out.append(slot_out)

    return {
        "ok": len(report_errors) == 0,
        "slots": slots_out,
        "errors": report_errors,
        "elapsedMs": round((clock() - started) * 1000),
    }


_B64_RE = re.compile(r"[A-Za-z0-9+/]+={0,2}")


def decode_plan_b64(plan_b64: str) -> dict:
    """Strict base64 JSON decode; rejects anything outside the b64 alphabet."""
    if not isinstance(plan_b64, str) or not _B64_RE.fullmatch(plan_b64):
        raise PreflightError(["plan_b64 is empty or not base64"])
    try:
        raw = base64.b64decode(plan_b64, validate=True)
        data = json.loads(raw.decode("utf-8"))
    except (binascii.Error, UnicodeDecodeError, ValueError) as exc:
        raise PreflightError([f"plan_b64 is not valid base64 JSON: {exc}"]) from exc
    return data


def _load_plan(plan_file: Path | None, plan_b64: str | None) -> dict:
    if plan_file is not None:
        data = json.loads(Path(plan_file).read_text(encoding="utf-8"))
    elif plan_b64 is not None:
        data = decode_plan_b64(plan_b64)
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
    parser = argparse.ArgumentParser(description=__doc__, allow_abbrev=False)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--directv-config", type=Path, required=True)
    parser.add_argument("--plan-file", type=Path, default=None)
    parser.add_argument("--plan-b64", default=None)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=False)
    mode.add_argument("--live", action="store_true", default=False)
    parser.add_argument("--session-start", type=int, default=1)
    parser.add_argument(
        "--time-budget",
        type=float,
        default=LIVE_TIME_BUDGET_S,
        help="Live only: seconds to finish all slots and print the report (HA kills at 60).",
    )
    args = parser.parse_args(argv)

    live = bool(args.live)
    if not args.live and not args.dry_run:
        # Default hybrid posture: dry-run.
        live = False

    try:
        inventory = load_inventory(args.inventory)
        directv = _load_yaml(args.directv_config)
        plan = _load_plan(args.plan_file, args.plan_b64)
        report = execute_plan(
            plan,
            inventory=inventory,
            directv=directv,
            live=live,
            session_start=int(args.session_start),
            time_budget_s=float(args.time_budget),
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
