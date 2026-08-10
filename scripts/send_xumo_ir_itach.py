#!/usr/bin/env python3
"""Send Xumo IR commands through Global Cache iTach IP2IR.

Usage:
  python3 scripts/send_xumo_ir_itach.py \
    --itach-config config/itach.yaml \
    --encoder ENC-01 \
    --digits 206 \
    --suffix ok \
    --digit-delay-ms 250
"""

from __future__ import annotations

import argparse
import socket
import time
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def parse_command_list(raw: str) -> list[str]:
    out: list[str] = []
    for token in raw.replace(" ", ",").split(","):
        t = token.strip()
        if t:
            out.append(t)
    return out


def build_sequence(digits: str, suffix_tokens: list[str]) -> list[str]:
    cmds = [ch for ch in str(digits).strip() if ch.strip()]
    return cmds + suffix_tokens


def send_commands(
    host: str,
    port: int,
    module: int,
    connector: int,
    code_map: dict[str, str],
    command_sequence: list[str],
    delay_ms: int,
) -> None:
    addr = (host, port)
    timeout_s = 2.0
    with socket.create_connection(addr, timeout=timeout_s) as sock:
        sock.settimeout(0.8)
        seq = 1
        for cmd_key in command_sequence:
            if cmd_key not in code_map:
                raise SystemExit(f"IR code key '{cmd_key}' not found in iTach config")
            payload = code_map[cmd_key]
            sendir = f"sendir,{module}:{connector},{seq},{payload}\r"
            sock.sendall(sendir.encode("ascii"))
            try:
                resp = sock.recv(4096).decode("ascii", errors="replace").strip()
                if resp:
                    print(f"iTach response: {resp}")
            except socket.timeout:
                # Response is optional for this workflow.
                pass
            seq += 1
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--itach-config", type=Path, required=True)
    parser.add_argument("--encoder", required=True, help="Encoder ID, e.g. ENC-01")
    parser.add_argument("--digits", required=True, help="Channel digits, e.g. 206")
    parser.add_argument("--suffix", default="ok", help="Comma-separated tail commands, e.g. ok or enter")
    parser.add_argument("--digit-delay-ms", type=int, default=250)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    cfg = load_yaml(args.itach_config)
    controllers = cfg.get("controllers", {})
    encoder_to_output = cfg.get("encoder_to_output", {})
    codes = cfg.get("codes", {})
    if not isinstance(controllers, dict) or not controllers:
        raise SystemExit("itach config: 'controllers' must be non-empty mapping")
    if not isinstance(encoder_to_output, dict) or not encoder_to_output:
        raise SystemExit("itach config: 'encoder_to_output' must be non-empty mapping")
    if not isinstance(codes, dict) or not codes:
        raise SystemExit("itach config: 'codes' must be non-empty mapping")

    encoder = str(args.encoder).strip()
    output_key = encoder_to_output.get(encoder)
    if not output_key:
        raise SystemExit(f"Encoder '{encoder}' missing in encoder_to_output map")
    if output_key not in controllers:
        raise SystemExit(f"Output '{output_key}' missing from controllers map")

    out_cfg = controllers[output_key]
    host = str(out_cfg.get("host", "")).strip()
    port = int(out_cfg.get("port", 4998))
    module = int(out_cfg.get("module", 1))
    connector = int(out_cfg.get("connector", 1))
    if not host:
        raise SystemExit(f"Controller '{output_key}' has empty host")

    suffix_tokens = parse_command_list(str(args.suffix))
    sequence = build_sequence(args.digits, suffix_tokens=suffix_tokens)
    if not sequence:
        raise SystemExit("No commands generated from digits/suffix")

    if args.dry_run:
        print(
            f"[dry-run] encoder={encoder} output={output_key} "
            f"target={host}:{port} module={module} connector={connector} sequence={sequence}"
        )
        return

    send_commands(
        host=host,
        port=port,
        module=module,
        connector=connector,
        code_map={str(k): str(v) for k, v in codes.items()},
        command_sequence=sequence,
        delay_ms=int(args.digit_delay_ms),
    )
    print(f"Sent {len(sequence)} IR command(s) via {output_key} for {encoder}")


if __name__ == "__main__":
    main()
