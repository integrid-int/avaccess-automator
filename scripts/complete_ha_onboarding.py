#!/usr/bin/env python3
"""Complete Home Assistant onboarding for the AVAccess staging instance.

Default staging owner:
  username: operator
  password: avaccess-staging

Does not start or stop Docker. POSTs to the HA onboarding API on
http://127.0.0.1:8123 (override with --base-url).

Usage:
  python3 scripts/complete_ha_onboarding.py --dry-run
  python3 scripts/complete_ha_onboarding.py
"""

from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen


DEFAULT_BASE_URL = "http://127.0.0.1:8123"
DEFAULT_USERNAME = "operator"
DEFAULT_PASSWORD = "avaccess-staging"
DEFAULT_NAME = "operator"


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL, help="HA origin (no trailing path).")
    parser.add_argument("--username", default=DEFAULT_USERNAME)
    parser.add_argument("--password", default=DEFAULT_PASSWORD)
    parser.add_argument("--name", default=DEFAULT_NAME, help="Display name for the owner account.")
    parser.add_argument("--language", default="en")
    parser.add_argument(
        "--client-id",
        default="",
        help="OAuth client_id. Defaults to <base-url>/",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print planned onboarding POSTs; do not contact Home Assistant.",
    )
    return parser.parse_args(argv)


def build_onboarding_plan(args: argparse.Namespace) -> list[dict[str, Any]]:
    base = str(args.base_url).rstrip("/")
    client_id = args.client_id or f"{base}/"
    return [
        {
            "path": "/api/onboarding/users",
            "method": "POST",
            "auth": False,
            "body": {
                "client_id": client_id,
                "name": args.name,
                "username": args.username,
                "password": args.password,
                "language": args.language,
            },
        },
        {
            "path": "/api/onboarding/core_config",
            "method": "POST",
            "auth": True,
            "body": {
                "location_name": "AVAccess Staging",
                "language": args.language,
                "country": "US",
                "timezone": "America/New_York",
                "unit_system": "us_customary",
                "currency": "USD",
            },
        },
        {"path": "/api/onboarding/analytics", "method": "POST", "auth": True, "body": {}},
        {
            "path": "/api/onboarding/integration",
            "method": "POST",
            "auth": True,
            "body": {
                "client_id": client_id,
                "redirect_uri": f"{base}/?auth_callback=1",
            },
        },
    ]


def _json_request(
    url: str,
    body: dict[str, Any] | None,
    *,
    token: str | None = None,
    form: bool = False,
) -> dict[str, Any] | list[Any] | str:
    headers = {"Accept": "application/json"}
    data: bytes | None
    if form:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        data = urlencode(body or {}).encode()
    else:
        headers["Content-Type"] = "application/json"
        data = json.dumps(body if body is not None else {}).encode()
    if token:
        headers["Authorization"] = f"Bearer {token}"
    req = Request(url, data=data, headers=headers, method="POST")
    with urlopen(req, timeout=30) as resp:
        raw = resp.read()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw.decode())
    except json.JSONDecodeError:
        return raw.decode()
    return parsed


def _exchange_auth_code(base: str, client_id: str, auth_code: str) -> str:
    payload = _json_request(
        f"{base}/auth/token",
        {"grant_type": "authorization_code", "code": auth_code, "client_id": client_id},
        form=True,
    )
    if not isinstance(payload, dict) or not payload.get("access_token"):
        raise SystemExit(f"Token exchange failed: {payload}")
    return str(payload["access_token"])


def run_onboarding(args: argparse.Namespace) -> None:
    base = str(args.base_url).rstrip("/")
    plan = build_onboarding_plan(args)
    token: str | None = None
    client_id = str(plan[0]["body"]["client_id"])
    for step in plan:
        url = f"{base}{step['path']}"
        print(f"POST {url}")
        try:
            payload = _json_request(
                url,
                step["body"],
                token=token if step["auth"] else None,
            )
        except HTTPError as exc:
            detail = exc.read().decode(errors="replace")
            raise SystemExit(f"{url} failed: HTTP {exc.code} {detail}") from exc
        except URLError as exc:
            raise SystemExit(f"{url} failed: {exc}") from exc
        if step["path"] == "/api/onboarding/users":
            auth_code = payload.get("auth_code") if isinstance(payload, dict) else None
            if not auth_code:
                raise SystemExit(f"Onboarding user step did not return auth_code: {payload}")
            token = _exchange_auth_code(base, client_id, str(auth_code))
    print(f"Onboarding complete. Owner: {args.username}")


def main(argv: list[str] | None = None) -> None:
    args = parse_args(argv if argv is not None else sys.argv[1:])
    plan = build_onboarding_plan(args)
    if args.dry_run:
        print("dry-run: planned Home Assistant onboarding POSTs (not sent)")
        print(f"base_url: {args.base_url}")
        print(f"username: {args.username}")
        for step in plan:
            print(f"{step['method']} {step['path']}")
            if step["body"]:
                print(json.dumps(step["body"], indent=2, sort_keys=True))
        return
    run_onboarding(args)


if __name__ == "__main__":
    main()
