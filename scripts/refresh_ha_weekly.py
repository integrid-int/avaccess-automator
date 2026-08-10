#!/usr/bin/env python3
"""Run weekly schedule sync + regenerate Home Assistant bundle.

Example:
  python3 scripts/refresh_ha_weekly.py \
    --channels config/channels.yaml \
    --sync-config config/schedule_sync.yaml \
    --inventory config/inventory.yaml \
    --out-package /config/packages/avaccess_matrix.yaml \
    --out-dashboard /config/dashboards/avaccess_matrix.yaml \
    --dry-run
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def run(cmd: list[str], dry_run: bool) -> None:
    print("+", " ".join(cmd))
    if dry_run:
        return
    subprocess.run(cmd, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--channels", type=Path, required=True)
    parser.add_argument("--sync-config", type=Path, required=True)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--profile")
    parser.add_argument("--inventory-ha-path", default="/config/avaccess/config/inventory.yaml")
    parser.add_argument("--out-package", type=Path, required=True)
    parser.add_argument("--out-dashboard", type=Path, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    base = Path(__file__).resolve().parent
    sync_script = base / "sync_weekly_schedule.py"
    gen_script = base / "generate_ha_bundle.py"
    if not sync_script.exists() or not gen_script.exists():
        raise SystemExit("Required scripts missing.")

    sync_cmd = [
        sys.executable,
        str(sync_script),
        "--channels",
        str(args.channels),
        "--sync-config",
        str(args.sync_config),
    ]
    if args.dry_run:
        sync_cmd.append("--dry-run")
    run(sync_cmd, dry_run=False)

    if not args.dry_run:
        gen_cmd = [
            sys.executable,
            str(gen_script),
            "--inventory",
            str(args.inventory),
            "--channels",
            str(args.channels),
            "--inventory-ha-path",
            args.inventory_ha_path,
            "--out-package",
            str(args.out_package),
            "--out-dashboard",
            str(args.out_dashboard),
        ]
        if args.profile:
            gen_cmd.extend(["--profile", args.profile])
        run(gen_cmd, dry_run=False)

    if args.dry_run:
        print("Dry run completed (channels file not modified; bundle not regenerated).")
    else:
        print("Weekly refresh complete.")
        print("Reload scripts / shell_command or restart Home Assistant to apply package changes.")


if __name__ == "__main__":
    main()
