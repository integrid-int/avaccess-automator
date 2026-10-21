"""Smoke tests for inventory YAML → JSON export (Live gate)."""

import tempfile
import unittest
from pathlib import Path

from scripts.avaccess.export_inventory_json import export_inventory_json, load_inventory_yaml

ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "config" / "inventory.example.yaml"


class ExportInventoryJsonTests(unittest.TestCase):
    def setUp(self):
        tmp = tempfile.TemporaryDirectory()
        self.addCleanup(tmp.cleanup)
        self.tmp_path = Path(tmp.name)

    def test_load_example_inventory_has_replace_me(self):
        data = load_inventory_yaml(EXAMPLE)
        assert "encoders" in data
        hostnames = [e.get("hostname", "") for e in data["encoders"]]
        assert any("REPLACE_ME" in h for h in hostnames)

    def test_export_inventory_json_roundtrip(self):
        out = self.tmp_path / "inventory.json"
        export_inventory_json(EXAMPLE, out)
        text = out.read_text(encoding="utf-8")
        assert "REPLACE_ME" in text
        assert '"encoders"' in text
