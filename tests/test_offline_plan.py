#!/usr/bin/env python3
"""Offline coverage for DirecTV/AVAccess test plan sections A, C, and E.

No AV LAN or H25 hardware required. Matrix dry-runs use a temp inventory
derived from config/inventory.example.yaml with REPLACE_ME hostnames filled
in so apply_preset/route_targets can emit msg_b_reconnect payloads.
"""

from __future__ import annotations

import datetime as dt
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from zoneinfo import ZoneInfo

import yaml

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.generate_ha_bundle import build_package, load_yaml, resolve_presets
from scripts.sync_weekly_schedule import (
    Candidate,
    build_channel_classification,
    build_class_priority,
    choose_best_candidate,
    classify_channel,
    derive_game_id,
    map_channel_number,
    parse_teams,
    parse_xmltv,
    pick_channels_for_window,
)

FIXTURES = ROOT / "tests" / "fixtures"
XMLTV_BLACKOUT = FIXTURES / "xmltv_blackout_27403.xml"
SYNC_BLACKOUT = FIXTURES / "schedule_sync_blackout.yaml"
SUNDAY_2026_09_20 = dt.date(2026, 9, 20)
TZ_NY = ZoneInfo("America/New_York")


def _run(args: list[str], cwd: Path = ROOT) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        check=False,
    )


def _write_commissioned_inventory(dest: Path) -> Path:
    """Copy inventory.example.yaml with unique hostnames (dry-run still checks REPLACE_ME)."""
    data = yaml.safe_load((ROOT / "config" / "inventory.example.yaml").read_text())
    for item in data["encoders"]:
        item["hostname"] = f"IPE935-{item['id']}"
        item["mac"] = f"aa:aa:aa:aa:aa:{item['id'].split('-')[1]}"
    for item in data["receivers"]:
        item["hostname"] = f"IPD935-{item['id']}"
        item["mac"] = f"bb:bb:bb:bb:bb:{item['id'].split('-')[1]}"
    dest.write_text(yaml.safe_dump(data, sort_keys=False))
    return dest


def _blackout_inputs() -> tuple[dict, dict[str, list[str]], list]:
    sync_cfg = load_yaml(SYNC_BLACKOUT)
    channels_meta, programmes = parse_xmltv(XMLTV_BLACKOUT.read_bytes(), tz=TZ_NY)
    return sync_cfg, channels_meta, programmes


def _pick_blackout(prefer_local: bool, class_priority: dict[str, int] | None = None):
    sync_cfg, channels_meta, programmes = _blackout_inputs()
    if class_priority is None:
        class_priority = build_class_priority(sync_cfg)
    afternoon = sync_cfg["afternoon_window"]
    start = dt.datetime.strptime(afternoon["start"], "%H:%M").time()
    end = dt.datetime.strptime(afternoon["end"], "%H:%M").time()
    return pick_channels_for_window(
        channels_meta=channels_meta,
        programmes=programmes,
        tz=TZ_NY,
        sunday=SUNDAY_2026_09_20,
        keywords=list(sync_cfg["nfl_keywords"]),
        map_cfg=sync_cfg["channel_number_map"],
        class_rules=build_channel_classification(sync_cfg),
        class_priority=class_priority,
        window=(start, end),
        prefer_local_for_blackout=prefer_local,
    )


class SectionADirectvCliDryRunTests(unittest.TestCase):
    def test_probe_dry_run_resolves_enc01_receiver(self) -> None:
        result = _run(
            [
                "scripts/directv_shef.py",
                "--config",
                "config/directv.example.yaml",
                "probe",
                "--encoder",
                "ENC-01",
                "--dry-run",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("ENC-01", out)
        self.assertIn("192.168.10.151", out)
        self.assertIn("command=probe", out)
        self.assertIn("[dry-run]", out)

    def test_tune_dry_run_emits_channel_206_url(self) -> None:
        result = _run(
            [
                "scripts/directv_shef.py",
                "--config",
                "config/directv.example.yaml",
                "tune",
                "--encoder",
                "ENC-02",
                "--channel",
                "206",
                "--dry-run",
            ]
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("ENC-02", out)
        self.assertIn("192.168.10.152", out)
        self.assertIn("command=tune", out)
        self.assertIn("GET /tv/tune?major=206&minor=65535", out)


class SectionCMatrixCliDryRunTests(unittest.TestCase):
    def test_apply_preset_1_all_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = _write_commissioned_inventory(Path(tmp) / "inventory.yaml")
            result = _run(
                [
                    "scripts/apply_preset.py",
                    "--inventory",
                    str(inventory),
                    "--preset",
                    "1_all",
                    "--profile",
                    "numeric_v1",
                    "--dry-run",
                    "--delay",
                    "0",
                ]
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("ENC-01", out)
        self.assertIn("msg_b_reconnect", out)
        self.assertIn("IPD935-RX-01", out)
        self.assertIn("[dry-run]", out)

    def test_route_targets_enc01_rx01_dry_run(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            inventory = _write_commissioned_inventory(Path(tmp) / "inventory.yaml")
            result = _run(
                [
                    "scripts/route_targets.py",
                    "--inventory",
                    str(inventory),
                    "--encoder",
                    "ENC-01",
                    "--targets",
                    "RX-01",
                    "--dry-run",
                ]
            )
        self.assertEqual(result.returncode, 0, result.stderr)
        out = result.stdout
        self.assertIn("msg_b_reconnect", out)
        self.assertIn("IPE935-ENC-01", out)
        self.assertIn("IPD935-RX-01", out)
        self.assertIn("RX-01", out)
        self.assertIn("[dry-run]", out)


class SectionAHaBundleTests(unittest.TestCase):
    def test_bundle_without_ui_staging_wires_directv_tune(self) -> None:
        inventory = load_yaml(ROOT / "config" / "inventory.example.yaml")
        channels = load_yaml(ROOT / "config" / "channels.example.yaml")
        profile, _presets = resolve_presets(inventory, "numeric_v1")
        package = build_package(
            inventory=inventory,
            channels_cfg=channels,
            profile_override=profile,
            inventory_ha_path="/config/avaccess/config/inventory.yaml",
        )
        tune_cmd = package["shell_command"]["avaccess_directv_tune"]
        self.assertIn("directv_shef.py", tune_cmd)
        self.assertIn("tune", tune_cmd)
        self.assertFalse(str(tune_cmd).strip().startswith("echo "))
        dumped = yaml.safe_dump(package["script"]["avaccess_tune_channel"])
        self.assertIn("shell_command.avaccess_directv_tune", dumped)


class SectionEBlackoutLocalFirstTests(unittest.TestCase):
    def test_fixture_classifies_wghp_local_and_ticket_705(self) -> None:
        sync_cfg, channels_meta, _programmes = _blackout_inputs()
        class_rules = build_channel_classification(sync_cfg)
        map_cfg = sync_cfg["channel_number_map"]

        wghp_id = "I8.wghp.greensboro.example"
        st_id = "I705.nflsundayticket.example"
        wghp_names = channels_meta[wghp_id]
        st_names = channels_meta[st_id]

        self.assertEqual(map_channel_number(wghp_id, wghp_names, map_cfg), "8")
        self.assertEqual(map_channel_number(st_id, st_names, map_cfg), "705")
        self.assertEqual(classify_channel(wghp_id, wghp_names, "8", class_rules), "local")
        self.assertEqual(classify_channel(st_id, st_names, "705", class_rules), "nfl_ticket")

    def test_same_matchup_and_kickoff_share_game_id(self) -> None:
        _sync_cfg, _channels_meta, programmes = _blackout_inputs()
        self.assertEqual(len(programmes), 2)
        kickoff = dt.datetime(2026, 9, 20, 13, 0, tzinfo=TZ_NY)
        ids = {derive_game_id(prog, kickoff) for prog in programmes}
        self.assertEqual(len(ids), 1)
        game_id = next(iter(ids))
        self.assertIn("panthers_vs_saints", game_id)
        self.assertEqual(parse_teams("Panthers vs Saints"), "panthers_vs_saints")

    def test_prefer_local_for_blackout_selects_channel_8_not_705(self) -> None:
        numbers, selected = _pick_blackout(prefer_local=True)
        self.assertEqual(numbers, ["8"])
        self.assertEqual(len(selected), 1)
        self.assertEqual(selected[0].channel_number, "8")
        self.assertEqual(selected[0].channel_class, "local")
        self.assertNotIn("705", numbers)

    def test_ticket_wins_when_local_preference_off_and_ticket_priority_first(self) -> None:
        numbers, selected = _pick_blackout(
            prefer_local=False,
            class_priority={"nfl_ticket": 0, "local": 1, "other": 999},
        )
        self.assertEqual(numbers, ["705"])
        self.assertEqual(selected[0].channel_number, "705")
        self.assertEqual(selected[0].channel_class, "nfl_ticket")

    def test_choose_best_candidate_local_nudge_vs_ticket_priority(self) -> None:
        kickoff = dt.datetime(2026, 9, 20, 13, 0, tzinfo=TZ_NY)
        local = Candidate(
            game_id="202609201300|panthers_vs_saints",
            start=kickoff,
            channel_number="8",
            channel_class="local",
            channel_id="I8.wghp.greensboro.example",
            channel_names=["WGHP FOX"],
            title="NFL Football",
            subtitle="Panthers vs Saints",
        )
        ticket = Candidate(
            game_id=local.game_id,
            start=kickoff,
            channel_number="705",
            channel_class="nfl_ticket",
            channel_id="I705.nflsundayticket.example",
            channel_names=["NFL Sunday Ticket 1"],
            title="NFL Football",
            subtitle="Panthers vs Saints",
        )
        ticket_first = {"nfl_ticket": 0, "local": 1, "other": 999}
        self.assertEqual(
            choose_best_candidate(
                [ticket, local], ticket_first, prefer_local_for_blackout=True
            ).channel_number,
            "8",
        )
        self.assertEqual(
            choose_best_candidate(
                [ticket, local], ticket_first, prefer_local_for_blackout=False
            ).channel_number,
            "705",
        )


if __name__ == "__main__":
    unittest.main()
