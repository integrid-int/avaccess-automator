#!/usr/bin/env python3
"""Pull/parse Spectrum Greensboro lineup → Gold (TV Platinum) JSON + JS module."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
import urllib.request
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

DEFAULT_SOURCE_URL = "https://tvchannelsguide.com/spectrum/greensboro-nc"
DEFAULT_PACKAGE_COLUMN = "TV Platinum"
MUSIC_NAME_RE = re.compile(
    r"music\s*choice|sonic\s*tap|stingray\s*music",
    re.IGNORECASE,
)
REQUIRED_NAME_SUBSTR = ("ESPN", "wfmy", "wghp", "wxii", "wxlv")


def _split_row(line: str) -> list[str] | None:
    line = line.strip()
    if not line.startswith("|") or line.count("|") < 4:
        return None
    cells = [c.strip() for c in line.strip("|").split("|")]
    return cells


def parse_tvchannelsguide_markdown(
    text: str, *, package_column: str = DEFAULT_PACKAGE_COLUMN
) -> list[dict[str, Any]]:
    """Parse tvchannelsguide Greensboro markdown dump into channel dicts."""
    lines = text.splitlines()
    header_idx = None
    headers: list[str] = []
    for i, line in enumerate(lines):
        cells = _split_row(line)
        if not cells:
            continue
        if cells[0] == "Ch #" and "Channel" in cells and package_column in cells:
            header_idx = i
            headers = cells
            break
    if header_idx is None:
        raise ValueError(f"Could not find lineup table header with {package_column!r}")

    pkg_idx = headers.index(package_column)
    # Markdown export often omits the empty Ch # cell, shifting later columns left by 1.
    name_idx = headers.index("Channel")
    cat_idx = headers.index("Category")

    table_rows: list[list[str]] = []
    for line in lines[header_idx + 1 :]:
        cells = _split_row(line)
        if not cells:
            if table_rows:
                break
            continue
        if set(cells[0]) <= {"-"}:
            continue
        if cells[0] == "Ch #":
            break
        # Align to header width when Ch # column is missing from the row.
        if len(cells) == len(headers) - 1 and not cells[0].isdigit():
            cells = [""] + cells
        table_rows.append(cells)

    before = "\n".join(lines[:header_idx])
    numbers = re.findall(r"^(\d+)\s*$", before, re.M)
    if len(numbers) < len(table_rows):
        raise ValueError(
            f"Not enough channel numbers before table "
            f"({len(numbers)} nums vs {len(table_rows)} rows)"
        )
    numbers = numbers[-len(table_rows) :]

    channels: list[dict[str, Any]] = []
    for number, cells in zip(numbers, table_rows, strict=True):
        if len(cells) <= max(pkg_idx, cat_idx, name_idx):
            continue
        name = cells[name_idx].strip()
        category = cells[cat_idx].strip()
        included = cells[pkg_idx].strip() == "✓"
        music = category.lower() == "music" or bool(MUSIC_NAME_RE.search(name))
        channels.append(
            {
                "number": str(number),
                "name": name,
                "category": category,
                "included": included,
                "music": music,
            }
        )
    return channels


def filter_lineup(
    channels: list[dict[str, Any]], *, exclude_music: bool = True
) -> list[dict[str, Any]]:
    """Keep package-included channels; drop music; normalize ids."""
    out: list[dict[str, Any]] = []
    seen: set[str] = set()
    for ch in channels:
        if not ch.get("included"):
            continue
        if exclude_music and ch.get("music"):
            continue
        number = str(ch["number"])
        if number in seen:
            raise ValueError(f"Duplicate channel number: {number}")
        seen.add(number)
        out.append(
            {
                "id": f"ch-{number}",
                "number": number,
                "name": str(ch["name"]),
                "category": str(ch["category"]),
                "music": False,
            }
        )
    return out


def validate_lineup(channels: list[dict[str, Any]]) -> None:
    if len(channels) < 100:
        raise ValueError(f"Lineup too small: {len(channels)} channels (need >= 100)")
    names_l = " ".join(c["name"].lower() for c in channels)
    missing = [s for s in REQUIRED_NAME_SUBSTR if s.lower() not in names_l]
    if missing:
        raise ValueError(f"Lineup missing required channels: {missing}")


def build_lineup_payload(
    channels: list[dict[str, Any]],
    *,
    source: str,
    package: str = "gold",
    zip_code: str = "27403",
    generated_at: dt.datetime | None = None,
) -> dict[str, Any]:
    validate_lineup(channels)
    if generated_at is None:
        generated_at = dt.datetime.now(tz=dt.timezone.utc)
    return {
        "zip": zip_code,
        "package": package,
        "packageColumn": DEFAULT_PACKAGE_COLUMN,
        "source": source,
        "generatedAt": generated_at.astimezone(dt.timezone.utc).isoformat(),
        "channels": channels,
    }


def write_js_module(channels: list[dict[str, Any]], path: Path) -> None:
    payload = json.dumps(channels, indent=2)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "// Generated by scripts/avaccess/pull_spectrum_lineup.py — do not edit by hand.\n"
        f"export const GUIDE_CHANNELS = {payload};\n",
        encoding="utf-8",
    )


def fetch_url(url: str) -> str:
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "avaccess-automator-lineup-pull/1.0"},
    )
    with urllib.request.urlopen(req, timeout=45) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--from-markdown", type=Path, help="Local markdown/HTML dump")
    parser.add_argument("--url", default="", help="Optional live URL (may be CF-blocked)")
    parser.add_argument(
        "--package-column",
        default=DEFAULT_PACKAGE_COLUMN,
        help="Package column to treat as Gold (default: TV Platinum)",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=ROOT / "config" / "spectrum_lineup_27403.json",
    )
    parser.add_argument(
        "--www-out",
        type=Path,
        default=ROOT
        / "homeassistant"
        / "config"
        / "www"
        / "avaccess"
        / "spectrum_lineup_27403.json",
    )
    parser.add_argument(
        "--js-out",
        type=Path,
        default=ROOT
        / "homeassistant"
        / "config"
        / "www"
        / "panels"
        / "spectrum-lineup-data.js",
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Validate existing --out JSON without regenerating from source",
    )
    args = parser.parse_args(argv)

    try:
        if args.check:
            data = json.loads(args.out.read_text(encoding="utf-8"))
            validate_lineup(data.get("channels") or [])
            print(f"OK {args.out} ({len(data['channels'])} channels)")
            return 0

        source_label = ""
        if args.from_markdown:
            text = args.from_markdown.read_text(encoding="utf-8")
            source_label = str(args.from_markdown)
        elif args.url:
            text = fetch_url(args.url)
            source_label = args.url
        else:
            text = fetch_url(DEFAULT_SOURCE_URL)
            source_label = DEFAULT_SOURCE_URL

        raw = parse_tvchannelsguide_markdown(
            text, package_column=args.package_column
        )
        channels = filter_lineup(raw, exclude_music=True)
        payload = build_lineup_payload(channels, source=source_label)

        for path in (args.out, args.www_out):
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(
                json.dumps(payload, indent=2) + "\n", encoding="utf-8"
            )
            print(path)
        write_js_module(channels, args.js_out)
        print(args.js_out)
        print(f"{len(channels)} channels (Gold/{args.package_column}, no music)")
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        print(f"pull_spectrum_lineup failed: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
