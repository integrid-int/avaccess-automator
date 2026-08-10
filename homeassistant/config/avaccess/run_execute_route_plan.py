#!/usr/bin/env python3
"""HA shell_command entrypoint for execute_route_plan (docker + local Core).

Docker compose mounts:
  scripts/avaccess -> /config/avaccess/scripts
  config/          -> /config/avaccess/config

Local Core (no mounts): resolves repo-root scripts/ and config/ via parents,
or uses checked-in symlinks under this directory when present.
"""

from __future__ import annotations

import runpy
import sys
import types
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _repo_root() -> Path | None:
    # homeassistant/config/avaccess -> parents[3] == repo root when checked out normally
    candidate = HERE.parents[3]
    marker = candidate / "scripts" / "avaccess" / "execute_route_plan.py"
    if marker.is_file():
        return candidate
    return None


def _ensure_scripts_avaccess_package(scripts_dir: Path) -> None:
    """Expose a directory of modules as import path scripts.avaccess.*."""
    if "scripts" not in sys.modules:
        scripts_pkg = types.ModuleType("scripts")
        scripts_pkg.__path__ = []  # type: ignore[attr-defined]
        sys.modules["scripts"] = scripts_pkg
    if "scripts.avaccess" not in sys.modules:
        av_pkg = types.ModuleType("scripts.avaccess")
        av_pkg.__path__ = [str(scripts_dir)]  # type: ignore[attr-defined]
        sys.modules["scripts.avaccess"] = av_pkg
    else:
        mod = sys.modules["scripts.avaccess"]
        paths = list(getattr(mod, "__path__", []))
        if str(scripts_dir) not in paths:
            paths.insert(0, str(scripts_dir))
            mod.__path__ = paths  # type: ignore[attr-defined]


def resolve_executor() -> Path:
    repo = _repo_root()
    if repo is not None:
        sys.path.insert(0, str(repo))
        return repo / "scripts" / "avaccess" / "execute_route_plan.py"

    mounted = HERE / "scripts" / "execute_route_plan.py"
    if mounted.is_file():
        _ensure_scripts_avaccess_package(mounted.parent)
        return mounted

    raise SystemExit(
        "execute_route_plan.py not found; expected repo scripts/avaccess or "
        "compose mount at avaccess/scripts"
    )


def _default_paths() -> tuple[Path, Path]:
    inventory = HERE / "config" / "inventory.yaml"
    itach = HERE / "config" / "itach.yaml"
    if inventory.is_file() and itach.is_file():
        return inventory, itach
    repo = _repo_root()
    if repo is not None:
        return repo / "config" / "inventory.yaml", repo / "config" / "itach.yaml"
    return inventory, itach


def _inject_default_args(argv: list[str]) -> list[str]:
    """Ensure --inventory / --itach-config are present for HA callers."""
    out = list(argv)
    inventory, itach = _default_paths()
    if "--inventory" not in out:
        out.extend(["--inventory", str(inventory)])
    if "--itach-config" not in out:
        out.extend(["--itach-config", str(itach)])
    return out


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    target = resolve_executor()
    forwarded = _inject_default_args(args)
    sys.argv = [str(target), *forwarded]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
