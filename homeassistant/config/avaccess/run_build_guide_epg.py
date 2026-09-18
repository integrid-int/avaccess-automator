#!/usr/bin/env python3
"""HA shell_command entrypoint for build_guide_epg (docker + local Core).

Docker compose mounts:
  scripts/avaccess -> /config/avaccess/scripts
  config/          -> /config/avaccess/config

Local Core (no mounts): resolves repo-root scripts/ and config/ via parents,
or uses checked-in symlinks under this directory when present.

Note: this directory's ``scripts`` symlink/mount points at ``scripts/avaccess``,
so it must not remain on ``sys.path`` or ``import scripts`` loads the wrong tree.
"""

from __future__ import annotations

import sys
import types
from pathlib import Path


HERE = Path(__file__).resolve().parent


def _repo_root() -> Path | None:
    # homeassistant/config/avaccess -> parents[2] == repo root when checked out normally
    candidate = HERE.parents[2]
    marker = candidate / "scripts" / "avaccess" / "build_guide_epg.py"
    if marker.is_file():
        return candidate
    return None


def _drop_here_from_sys_path() -> None:
    """Remove this wrapper's directory so avaccess/scripts cannot shadow ``scripts``."""
    here = HERE.resolve()
    sys.path[:] = [p for p in sys.path if not p or Path(p).resolve() != here]


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


def _prepare_import() -> None:
    _drop_here_from_sys_path()
    repo = _repo_root()
    if repo is not None:
        sys.path.insert(0, str(repo))
        return

    mounted = HERE / "scripts"
    if (mounted / "build_guide_epg.py").is_file():
        _ensure_scripts_avaccess_package(mounted.resolve())
        return

    raise SystemExit(
        "build_guide_epg.py not found; expected repo scripts/avaccess or "
        "compose mount at avaccess/scripts"
    )


def _default_paths() -> tuple[Path, Path]:
    config = HERE / "config" / "guide_epg.yaml"
    out = HERE.parent / "www" / "avaccess" / "guide_epg.json"
    if config.is_file():
        return config, out
    repo = _repo_root()
    if repo is not None:
        return (
            repo / "config" / "guide_epg.yaml",
            repo / "homeassistant" / "config" / "www" / "avaccess" / "guide_epg.json",
        )
    return config, out


def _inject_default_args(argv: list[str]) -> list[str]:
    """Ensure --config / --out are present for HA callers."""
    out = list(argv)
    config, out_path = _default_paths()
    if "--config" not in out:
        out.extend(["--config", str(config)])
    if "--out" not in out:
        out.extend(["--out", str(out_path)])
    return out


def main(argv: list[str] | None = None) -> None:
    args = list(sys.argv[1:] if argv is None else argv)
    _prepare_import()
    forwarded = _inject_default_args(args)
    from scripts.avaccess.build_guide_epg import main as builder_main

    raise SystemExit(builder_main(forwarded))


if __name__ == "__main__":
    main()
