"""AVAccess UDP reconnect helpers (msg_b_reconnect)."""

from __future__ import annotations

import socket


def build_reconnect_message(
    tx_hostname: str, session: int, rx_hostnames: list[str]
) -> bytes:
    """Build ``msg_b_reconnect {tx}:{session}:{n} {rx...}`` payload."""
    header = f"msg_b_reconnect {tx_hostname}:{session}:{len(rx_hostnames)}"
    body = " ".join(rx_hostnames)
    return f"{header} {body}".encode("ascii")


def send_udp(
    payload: bytes,
    *,
    broadcast: str,
    port: int,
    dry_run: bool = False,
) -> None:
    """Broadcast ``payload`` to ``broadcast:port``, or print when dry-run."""
    if dry_run:
        print(f"[dry-run] UDP {broadcast}:{port} -> {payload.decode('ascii')}")
        return
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        sock.sendto(payload, (broadcast, port))
    finally:
        sock.close()


def send_udp_reconnect(
    *,
    tx_hostname: str,
    rx_hostnames: list[str],
    broadcast: str,
    port: int,
    session: int,
    dry_run: bool = False,
) -> bytes:
    """Build and send a reconnect message; return the payload bytes."""
    payload = build_reconnect_message(tx_hostname, session, list(rx_hostnames))
    send_udp(payload, broadcast=broadcast, port=port, dry_run=dry_run)
    return payload
