#!/usr/bin/env python3
"""HA shell_command entrypoint for execute_route_plan (docker + local Core).

Docker compose mounts:
  scripts/avaccess -> /config/avaccess/scripts
  scripts/directv_shef.py -> /config/avaccess/directv_shef.py
  config/          -> /config/avaccess/config

Do not mount directv_shef.py inside the read-only scripts directory.

Local Core (no mounts): resolves repo-root scripts/ and config/ via parents,
or uses checked-in symlinks under this directory when present.
"""

from __future__ import annotations

import importlib.util
import json
import runpy
import sys
import types
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _repo_root() -> Path | None:
    """Repo root when this file lives at homeassistant/config/avaccess.

    On HA OS and Docker, HERE is /config/avaccess (only two parents). Do not
    index parents[2] there — that raises IndexError before Live Send runs.
    """
    if len(HERE.parents) <= 2:
        return None
    candidate = HERE.parents[2]
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
    _ensure_directv_shef(scripts_dir)


def _ensure_directv_shef(scripts_dir: Path) -> None:
    """Register overlay directv_shef.py as scripts.directv_shef when present.

    The file is mounted next to the scripts dir (/config/avaccess/directv_shef.py),
    not inside the read-only scripts mount.
    """
    candidates = (
        scripts_dir.parent / "directv_shef.py",
        scripts_dir / "directv_shef.py",
    )
    shef_path = next((path for path in candidates if path.is_file()), None)
    if shef_path is None or "scripts.directv_shef" in sys.modules:
        return
    spec = importlib.util.spec_from_file_location("scripts.directv_shef", shef_path)
    if spec is None or spec.loader is None:
        return
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    sys.modules["scripts.directv_shef"] = mod
    scripts_pkg = sys.modules.get("scripts")
    if scripts_pkg is not None:
        setattr(scripts_pkg, "directv_shef", mod)


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
    directv = HERE / "config" / "directv.yaml"
    if inventory.is_file() and directv.is_file():
        return inventory, directv
    repo = _repo_root()
    if repo is not None:
        return repo / "config" / "inventory.yaml", repo / "config" / "directv.yaml"
    return inventory, directv


def _inject_default_args(argv: list[str]) -> list[str]:
    """Ensure --inventory / --directv-config are present for HA callers."""
    out = list(argv)
    inventory, directv = _default_paths()
    if "--inventory" not in out:
        out.extend(["--inventory", str(inventory)])
    if "--directv-config" not in out:
        out.extend(["--directv-config", str(directv)])
    return out


LIVE_REFUSED_EXIT = 3
LIVE_REFUSED_MESSAGE = "Live Commit is off in Home Assistant. Nothing was sent."


def split_live_commit(argv: list[str]) -> tuple[list[str], str | None]:
    """Remove ``--live-commit <state>`` (rendered by HA from the boolean)."""
    out: list[str] = []
    state: str | None = None
    i = 0
    while i < len(argv):
        arg = argv[i]
        if arg == "--live-commit":
            state = argv[i + 1] if i + 1 < len(argv) else ""
            i += 2
            continue
        if arg.startswith("--live-commit="):
            state = arg.split("=", 1)[1]
            i += 1
            continue
        out.append(arg)
        i += 1
    return out, state


def live_refusal(argv: list[str]) -> str | None:
    """Return a refusal message when --live is requested without the boolean on.

    The shell_command template renders ``--live-commit on|off`` from
    ``input_boolean.avaccess_live_commit`` at call time, so a caller that skips
    the panel or script still cannot go live while the boolean is off.
    """
    args, state = split_live_commit(argv)
    if "--live" not in args:
        return None
    if state == "on":
        return None
    return LIVE_REFUSED_MESSAGE


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    refusal = live_refusal(args)
    if refusal is not None:
        print(json.dumps({"ok": False, "slots": [], "errors": [refusal]}), flush=True)
        raise SystemExit(LIVE_REFUSED_EXIT)
    args, _ = split_live_commit(args)
    target = resolve_executor()
    forwarded = _inject_default_args(args)
    sys.argv = [str(target), *forwarded]
    runpy.run_path(str(target), run_name="__main__")


if __name__ == "__main__":
    main()
