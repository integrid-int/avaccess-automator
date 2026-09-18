"""Global Cache iTach IP2IR helpers for Xumo channel digits."""

from __future__ import annotations

import socket
import time
from typing import Any


def parse_command_list(raw: str) -> list[str]:
    out: list[str] = []
    for token in raw.replace(" ", ",").split(","):
        t = token.strip()
        if t:
            out.append(t)
    return out


def build_sequence(digits: str, suffix_tokens: list[str] | None = None) -> list[str]:
    cmds = [ch for ch in str(digits).strip() if ch.strip()]
    return cmds + list(suffix_tokens or [])


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
                raise ValueError(f"IR code key '{cmd_key}' not found in iTach config")
            payload = code_map[cmd_key]
            sendir = f"sendir,{module}:{connector},{seq},{payload}\r"
            sock.sendall(sendir.encode("ascii"))
            try:
                sock.recv(4096)
            except socket.timeout:
                pass
            seq += 1
            if delay_ms > 0:
                time.sleep(delay_ms / 1000.0)


def resolve_encoder_output(
    itach: dict[str, Any], encoder_id: str
) -> tuple[str, int, int, int]:
    """Return (host, port, module, connector) for ``encoder_id``."""
    controllers = itach.get("controllers") or {}
    encoder_to_output = itach.get("encoder_to_output") or {}
    if not isinstance(controllers, dict) or not isinstance(encoder_to_output, dict):
        raise ValueError("itach config missing controllers/encoder_to_output maps")

    output_key = encoder_to_output.get(encoder_id)
    if not output_key:
        raise ValueError(f"Encoder '{encoder_id}' missing in encoder_to_output map")
    if output_key not in controllers:
        raise ValueError(f"Output '{output_key}' missing from controllers map")

    out_cfg = controllers[output_key] or {}
    host = str(out_cfg.get("host", "")).strip()
    port = int(out_cfg.get("port", 4998))
    module = int(out_cfg.get("module", 1))
    connector = int(out_cfg.get("connector", 1))
    if not host:
        raise ValueError(f"Controller '{output_key}' has empty host")
    return host, port, module, connector


def send_ir_digits(
    *,
    digits: str,
    encoder_id: str,
    itach: dict[str, Any],
    digit_delay_ms: int = 250,
    suffix: str = "ok",
    dry_run: bool = False,
) -> list[str]:
    """Send channel digits (+ suffix) via iTach for ``encoder_id``.

    Returns the command sequence that was (or would be) sent.
    """
    codes = itach.get("codes") or {}
    if not isinstance(codes, dict):
        raise ValueError("itach config: 'codes' must be a mapping")

    suffix_tokens = parse_command_list(str(suffix))
    sequence = build_sequence(digits, suffix_tokens=suffix_tokens)
    if not sequence:
        raise ValueError("No commands generated from digits/suffix")

    host, port, module, connector = resolve_encoder_output(itach, encoder_id)

    if dry_run:
        print(
            f"[dry-run] encoder={encoder_id} "
            f"target={host}:{port} module={module} connector={connector} "
            f"sequence={sequence}"
        )
        return sequence

    send_commands(
        host=host,
        port=port,
        module=module,
        connector=connector,
        code_map={str(k): str(v) for k, v in codes.items()},
        command_sequence=sequence,
        delay_ms=int(digit_delay_ms),
    )
    return sequence
