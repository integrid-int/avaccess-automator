#!/usr/bin/env python3
"""Write custom_tv_sets.json from a base64 payload sent by the Sports Routing panel."""

from __future__ import annotations

import argparse
import base64
import json
from pathlib import Path

MAX_SETS = 8


def normalize(payload: dict) -> dict:
    raw = payload.get("sets") if isinstance(payload, dict) else None
    if not isinstance(raw, list):
        raise ValueError("sets must be a list")
    sets = []
    names = set()
    for item in raw:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()[:24]
        tvs = sorted({int(tv) for tv in item.get("tvs") or [] if isinstance(tv, int) or str(tv).isdigit()})
        tvs = [tv for tv in tvs if 1 <= tv <= 35]
        key = name.lower()
        if not name or not tvs or key in names:
            continue
        names.add(key)
        sets.append({"id": str(item.get("id") or f"set-{len(sets) + 1}"), "name": name, "tvs": tvs})
        if len(sets) >= MAX_SETS:
            break
    return {"source": "tv-sets", "sets": sets}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--sets-b64", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    decoded = base64.b64decode(args.sets_b64)
    payload = json.loads(decoded)
    if not isinstance(payload, dict):
        raise SystemExit("payload must be an object")
    document = normalize(payload)
    dest = Path(args.out)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
