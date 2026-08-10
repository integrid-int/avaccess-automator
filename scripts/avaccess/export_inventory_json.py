#!/usr/bin/env python3
"""Export inventory YAML to JSON for the bartender Live gate (/local/avaccess/)."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_INPUT = ROOT / "config" / "inventory.example.yaml"
DEFAULT_OUTPUT = ROOT / "homeassistant" / "config" / "www" / "avaccess" / "inventory.json"


def load_inventory_yaml(path: Path) -> Any:
    data = yaml.safe_load(path.read_text(encoding="utf-8"))
    if data is None:
        raise ValueError(f"Empty inventory YAML: {path}")
    return data


def export_inventory_json(input_path: Path, output_path: Path) -> Path:
    data = load_inventory_yaml(input_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(data, indent=2, sort_keys=False) + "\n",
        encoding="utf-8",
    )
    return output_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=DEFAULT_INPUT,
        help="Inventory YAML path (default: config/inventory.example.yaml)",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=DEFAULT_OUTPUT,
        help="Output JSON path (default: homeassistant/config/www/avaccess/inventory.json)",
    )
    args = parser.parse_args(argv)
    try:
        out = export_inventory_json(args.input, args.output)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        print(f"export failed: {exc}", file=sys.stderr)
        return 1
    print(out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
