#!/usr/bin/env python3
"""DirecTV H25 SHEF IP control (tune, status, remote keys).

Usage:
  python3 scripts/directv_shef.py --config config/directv.yaml probe --encoder ENC-01
  python3 scripts/directv_shef.py --config config/directv.yaml get-tuned --encoder ENC-01
  python3 scripts/directv_shef.py --config config/directv.yaml tune --encoder ENC-01 --channel 206
  python3 scripts/directv_shef.py --config config/directv.yaml send-key --encoder ENC-01 --key guide
  python3 scripts/directv_shef.py --config config/directv.yaml probe-all
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

import yaml


DEFAULT_PORT = 8080
DEFAULT_MINOR = 65535
DEFAULT_TIMEOUT = 4.0


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def parse_channel(raw: str) -> tuple[int, int]:
    text = str(raw).strip()
    if not text:
        raise SystemExit("Empty channel number")
    if "." in text:
        major_s, minor_s = text.split(".", 1)
        return int(major_s), int(minor_s)
    if "-" in text:
        major_s, minor_s = text.split("-", 1)
        return int(major_s), int(minor_s)
    return int(text), DEFAULT_MINOR


def resolve_receiver(cfg: dict[str, Any], encoder: str) -> dict[str, Any]:
    mapping = cfg.get("encoder_to_receiver", {})
    receivers = cfg.get("receivers", {})
    if not isinstance(mapping, dict) or not isinstance(receivers, dict):
        raise SystemExit("directv config needs mapping fields: encoder_to_receiver, receivers")
    recv_id = mapping.get(encoder)
    if not recv_id:
        raise SystemExit(f"Encoder '{encoder}' not mapped in encoder_to_receiver")
    recv = receivers.get(recv_id)
    if not isinstance(recv, dict):
        raise SystemExit(f"Receiver '{recv_id}' missing from receivers")
    host = str(recv.get("host", "")).strip()
    if not host:
        raise SystemExit(f"Receiver '{recv_id}' has empty host")
    return {
        "id": recv_id,
        "host": host,
        "port": int(recv.get("port", DEFAULT_PORT)),
        "client_addr": str(recv.get("client_addr", "0")),
        "label": str(recv.get("label", recv_id)),
    }


def shef_get(
    host: str,
    port: int,
    path: str,
    params: dict[str, Any] | None = None,
    timeout: float = DEFAULT_TIMEOUT,
) -> dict[str, Any]:
    query = urllib.parse.urlencode({k: v for k, v in (params or {}).items() if v is not None})
    url = f"http://{host}:{port}{path}"
    if query:
        url = f"{url}?{query}"
    req = urllib.request.Request(url, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace") if exc.fp else str(exc)
        raise SystemExit(f"SHEF HTTP {exc.code} for {url}: {detail}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"SHEF connection failed for {url}: {exc.reason}") from exc
    try:
        data = json.loads(body) if body.strip() else {}
    except json.JSONDecodeError as exc:
        raise SystemExit(f"SHEF returned non-JSON from {url}: {body[:200]}") from exc
    if not isinstance(data, dict):
        raise SystemExit(f"SHEF unexpected payload from {url}")
    return data


def cmd_probe(recv: dict[str, Any], timeout: float) -> dict[str, Any]:
    options = shef_get(recv["host"], recv["port"], "/info/getOptions", timeout=timeout)
    mode = shef_get(recv["host"], recv["port"], "/info/mode", timeout=timeout)
    return {"options": options, "mode": mode}


def cmd_get_tuned(recv: dict[str, Any], timeout: float) -> dict[str, Any]:
    return shef_get(
        recv["host"],
        recv["port"],
        "/tv/getTuned",
        params={"clientAddr": recv["client_addr"]},
        timeout=timeout,
    )


def cmd_tune(recv: dict[str, Any], major: int, minor: int, timeout: float) -> dict[str, Any]:
    return shef_get(
        recv["host"],
        recv["port"],
        "/tv/tune",
        params={"major": major, "minor": minor, "clientAddr": recv["client_addr"]},
        timeout=timeout,
    )


def cmd_send_key(recv: dict[str, Any], key: str, hold: str, timeout: float) -> dict[str, Any]:
    return shef_get(
        recv["host"],
        recv["port"],
        "/remote/processKey",
        params={"key": key, "hold": hold, "clientAddr": recv["client_addr"]},
        timeout=timeout,
    )


def summarize_tuned(payload: dict[str, Any]) -> str:
    title = payload.get("title") or payload.get("episodeTitle") or ""
    callsign = payload.get("callsign") or ""
    major = payload.get("major")
    minor = payload.get("minor")
    return f"ch={major}-{minor} {callsign} | {title}".strip()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--timeout", type=float, default=DEFAULT_TIMEOUT)
    dry = argparse.ArgumentParser(add_help=False)
    dry.add_argument("--dry-run", action="store_true")
    sub = parser.add_subparsers(dest="command", required=True)

    p_probe = sub.add_parser("probe", parents=[dry])
    p_probe.add_argument("--encoder", required=True)

    p_tuned = sub.add_parser("get-tuned", parents=[dry])
    p_tuned.add_argument("--encoder", required=True)

    p_tune = sub.add_parser("tune", parents=[dry])
    p_tune.add_argument("--encoder", required=True)
    p_tune.add_argument("--channel", required=True, help="Major, or major.minor / major-minor")
    p_tune.add_argument("--verify", action="store_true")

    p_key = sub.add_parser("send-key", parents=[dry])
    p_key.add_argument("--encoder", required=True)
    p_key.add_argument("--key", required=True)
    p_key.add_argument("--hold", default="keyPress")

    sub.add_parser("probe-all", parents=[dry])

    args = parser.parse_args()
    cfg = load_yaml(args.config)

    if args.command == "probe-all":
        mapping = cfg.get("encoder_to_receiver", {})
        if not isinstance(mapping, dict) or not mapping:
            raise SystemExit("encoder_to_receiver is empty")
        failures = 0
        for encoder in mapping:
            recv = resolve_receiver(cfg, encoder)
            print(f"=== {encoder} -> {recv['id']} {recv['host']}:{recv['port']} ===")
            if args.dry_run:
                print("[dry-run] would GET /info/getOptions and /info/mode")
                continue
            try:
                result = cmd_probe(recv, timeout=args.timeout)
                print(json.dumps(result.get("mode", {}), indent=2))
            except SystemExit as exc:
                failures += 1
                print(f"FAIL: {exc}", file=sys.stderr)
        if failures:
            raise SystemExit(f"probe-all completed with {failures} failure(s)")
        return

    recv = resolve_receiver(cfg, str(args.encoder))
    if args.dry_run:
        print(
            f"[dry-run] encoder={args.encoder} receiver={recv['id']} "
            f"{recv['host']}:{recv['port']} command={args.command}"
        )
        if args.command == "tune":
            major, minor = parse_channel(args.channel)
            print(f"[dry-run] GET /tv/tune?major={major}&minor={minor}")
        return

    if args.command == "probe":
        print(json.dumps(cmd_probe(recv, timeout=args.timeout), indent=2))
        return
    if args.command == "get-tuned":
        tuned = cmd_get_tuned(recv, timeout=args.timeout)
        print(summarize_tuned(tuned))
        print(json.dumps(tuned, indent=2))
        return
    if args.command == "tune":
        major, minor = parse_channel(args.channel)
        result = cmd_tune(recv, major, minor, timeout=args.timeout)
        print(json.dumps(result, indent=2))
        if args.verify:
            tuned = cmd_get_tuned(recv, timeout=args.timeout)
            print("now:", summarize_tuned(tuned))
        return
    if args.command == "send-key":
        print(json.dumps(cmd_send_key(recv, args.key, args.hold, timeout=args.timeout), indent=2))
        return


if __name__ == "__main__":
    main()
