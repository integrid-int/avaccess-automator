"""HA shell wrappers must not crash on the shallow /config/avaccess layout."""

from __future__ import annotations

import importlib.util
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
WRAPPER_DIR = ROOT / "homeassistant" / "config" / "avaccess"


def _load_wrapper(filename: str):
    path = WRAPPER_DIR / filename
    spec = importlib.util.spec_from_file_location(f"ha_wrapper_{path.stem}", path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class HaRouteWrappersTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def test_execute_wrapper_shallow_ha_path_has_no_repo_root(self):
        mod = _load_wrapper("run_execute_route_plan.py")
        mod.HERE = Path("/config/avaccess")
        assert len(mod.HERE.parents) <= 2
        assert mod._repo_root() is None

    def test_guide_wrapper_shallow_ha_path_has_no_repo_root(self):
        mod = _load_wrapper("run_build_guide_epg.py")
        mod.HERE = Path("/config/avaccess")
        assert len(mod.HERE.parents) <= 2
        assert mod._repo_root() is None

    def test_execute_wrapper_checkout_resolves_repo_root(self):
        mod = _load_wrapper("run_execute_route_plan.py")
        root = mod._repo_root()
        assert root == ROOT
        assert (root / "scripts" / "avaccess" / "execute_route_plan.py").is_file()

    def test_guide_wrapper_checkout_resolves_repo_root(self):
        mod = _load_wrapper("run_build_guide_epg.py")
        root = mod._repo_root()
        assert root == ROOT
        assert (root / "scripts" / "avaccess" / "build_guide_epg.py").is_file()

    def test_execute_wrapper_loads_shef_beside_scripts_mount(self):
        """HA mounts directv_shef.py next to the read-only scripts directory."""
        mod = _load_wrapper("run_execute_route_plan.py")
        here = self.tmp_path / "config" / "avaccess"
        scripts = here / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "execute_route_plan.py").write_text("# mount stub\n", encoding="utf-8")
        (scripts / "directv_shef.py").write_text(
            "OVERLAY_MARKER = 'inside'\n", encoding="utf-8"
        )
        (here / "directv_shef.py").write_text(
            "OVERLAY_MARKER = 'parent'\n", encoding="utf-8"
        )
        mod.HERE = here

        saved = sys.modules.pop("scripts.directv_shef", None)
        scripts_pkg = sys.modules.get("scripts")
        saved_attr = getattr(scripts_pkg, "directv_shef", None) if scripts_pkg else None
        av_mod = sys.modules.get("scripts.avaccess")
        saved_path = list(getattr(av_mod, "__path__", [])) if av_mod is not None else None
        try:
            found = mod.resolve_executor()
            loaded = sys.modules["scripts.directv_shef"]
            assert found == scripts / "execute_route_plan.py"
            assert loaded.OVERLAY_MARKER == "parent"
            assert Path(loaded.__file__).resolve() == (here / "directv_shef.py").resolve()
        finally:
            if saved is None:
                sys.modules.pop("scripts.directv_shef", None)
            else:
                sys.modules["scripts.directv_shef"] = saved
            scripts_pkg = sys.modules.get("scripts")
            if scripts_pkg is not None:
                if saved_attr is None and hasattr(scripts_pkg, "directv_shef"):
                    delattr(scripts_pkg, "directv_shef")
                elif saved_attr is not None:
                    setattr(scripts_pkg, "directv_shef", saved_attr)
            if av_mod is not None and saved_path is not None:
                av_mod.__path__ = saved_path

    def test_execute_wrapper_deep_path_without_marker_uses_mount(self):
        """A deep path whose parents[2] is not the repo must not raise IndexError."""
        mod = _load_wrapper("run_execute_route_plan.py")
        here = self.tmp_path / "a" / "b" / "c" / "config" / "avaccess"
        scripts = here / "scripts"
        scripts.mkdir(parents=True)
        (scripts / "execute_route_plan.py").write_text("# mount stub\n", encoding="utf-8")
        mod.HERE = here
        av_mod = sys.modules.get("scripts.avaccess")
        saved_path = list(getattr(av_mod, "__path__", [])) if av_mod is not None else None
        try:
            assert len(here.parents) > 2
            assert mod._repo_root() is None
            assert mod.resolve_executor() == scripts / "execute_route_plan.py"
        finally:
            if av_mod is not None and saved_path is not None:
                av_mod.__path__ = saved_path
