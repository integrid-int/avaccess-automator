#!/usr/bin/env python3
"""Prepare a cloud/staging Home Assistant config that loads the AVAccess UI.

This does not talk to DirecTV or AVAccess hardware. Shell commands are stubbed
so operators can find Lovelace/layout bugs on an iPad or browser first.

Usage:
  python3 scripts/prepare_ha_staging.py
  docker compose -f homeassistant/staging/docker-compose.yml up
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from typing import Any

import yaml

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "homeassistant" / "staging"
CONFIG = STAGING / "config"


CONFIGURATION_YAML = """# Cloud/staging Home Assistant config for AVAccess UI testing.
# Shell commands are stubs. Do not point this instance at production AV gear.

default_config:

homeassistant:
  name: AVAccess Staging
  latitude: 36.0726
  longitude: -79.7920
  elevation: 0
  time_zone: America/New_York
  unit_system: us_customary
  currency: USD
  packages: !include_dir_named packages

http:
  use_x_forwarded_for: true
  trusted_proxies:
    - 127.0.0.1
    - ::1
    - 172.16.0.0/12
    - 10.0.0.0/8

lovelace:
  mode: yaml
  dashboards:
    avaccess-matrix:
      mode: yaml
      title: AVAccess Matrix
      icon: mdi:video-input-component
      show_in_sidebar: true
      filename: dashboards/avaccess_matrix.yaml

logger:
  default: info
  logs:
    homeassistant.components.shell_command: debug
    homeassistant.components.script: debug
"""

COMPOSE_YAML = """services:
  homeassistant:
    image: ghcr.io/home-assistant/home-assistant:stable
    container_name: avaccess-ha-staging
    restart: unless-stopped
    ports:
      - "8123:8123"
    volumes:
      - ./config:/config
    environment:
      TZ: America/New_York
"""


def _legacy_template_blocks(sensors_cfg: Any) -> bool:
    """True when YAML still has `sensor: [{platform: template, sensors: ...}]`."""
    if sensors_cfg is None:
        return False
    blocks = sensors_cfg if isinstance(sensors_cfg, list) else [sensors_cfg]
    return any(
        isinstance(block, dict) and block.get("platform") == "template" and "sensors" in block
        for block in blocks
    )


def package_has_legacy_template_sensors(package_path: Path) -> bool:
    """Safety-net probe: generator now emits modern `template:` sensors directly."""
    if not package_path.is_file():
        return False
    data = yaml.safe_load(package_path.read_text())
    if not isinstance(data, dict):
        return False
    return _legacy_template_blocks(data.get("sensor"))


def migrate_legacy_template_sensors(package_path: Path) -> None:
    """HA 2026+ rejects `sensor: platform: template`. Rewrite to modern `template:`.

    Keep this as a safety net for already-legacy YAML. New `--ui-staging` packages
    from generate_ha_bundle.apply_ui_staging_stubs should already be modern.
    """
    raw = package_path.read_text()
    data = yaml.safe_load(raw)
    if not isinstance(data, dict):
        return

    sensors_cfg = data.get("sensor")
    if not _legacy_template_blocks(sensors_cfg):
        return

    migrated: list[dict[str, Any]] = []
    remaining: list[Any] = []
    blocks = sensors_cfg if isinstance(sensors_cfg, list) else [sensors_cfg]
    for block in blocks:
        if isinstance(block, dict) and block.get("platform") == "template" and "sensors" in block:
            for object_id, spec in block["sensors"].items():
                if not isinstance(spec, dict):
                    continue
                migrated.append(
                    {
                        "default_entity_id": f"sensor.{object_id}",
                        "name": spec.get("friendly_name", object_id),
                        "unique_id": f"staging_{object_id}",
                        "state": spec.get("value_template", ""),
                        "icon": spec.get("icon_template", "mdi:satellite-uplink"),
                    }
                )
        else:
            remaining.append(block)

    if not migrated:
        return

    if remaining:
        data["sensor"] = remaining
    else:
        data.pop("sensor", None)

    new_block = {"sensor": migrated}
    existing = data.get("template")
    if existing is None:
        data["template"] = [new_block]
    elif isinstance(existing, list):
        existing.append(new_block)
    else:
        data["template"] = [existing, new_block]

    header = ""
    if raw.startswith("#"):
        header_lines = []
        for line in raw.splitlines():
            if line.startswith("#") or line.strip() == "":
                header_lines.append(line)
            else:
                break
        header = "\n".join(header_lines).rstrip() + "\n"
    package_path.write_text(header + yaml.safe_dump(data, sort_keys=False, width=120, allow_unicode=False))


def main() -> None:
    (CONFIG / "packages").mkdir(parents=True, exist_ok=True)
    (CONFIG / "dashboards").mkdir(parents=True, exist_ok=True)
    (CONFIG / "www").mkdir(parents=True, exist_ok=True)
    (STAGING).mkdir(parents=True, exist_ok=True)

    (CONFIG / "configuration.yaml").write_text(CONFIGURATION_YAML)
    (STAGING / "docker-compose.yml").write_text(COMPOSE_YAML)

    cmd = [
        sys.executable,
        str(ROOT / "scripts" / "generate_ha_bundle.py"),
        "--inventory",
        str(ROOT / "config" / "inventory.example.yaml"),
        "--channels",
        str(ROOT / "config" / "channels.example.yaml"),
        "--ui-staging",
        "--out-package",
        str(CONFIG / "packages" / "avaccess_matrix.yaml"),
        "--out-dashboard",
        str(CONFIG / "dashboards" / "avaccess_matrix.yaml"),
    ]
    subprocess.run(cmd, check=True)
    package_path = CONFIG / "packages" / "avaccess_matrix.yaml"
    # Safety net only: skip when generate already wrote modern `template:` sensors.
    if package_has_legacy_template_sensors(package_path):
        migrate_legacy_template_sensors(package_path)
    print(f"Staging config ready: {CONFIG}")
    print("Start with:")
    print(f"  docker compose -f {STAGING / 'docker-compose.yml'} up -d")
    print("Then open http://<host>:8123 , complete onboarding, and use the AVAccess Matrix sidebar dashboard.")
    print("Default staging owner: operator / avaccess-staging")
    print("  python3 scripts/complete_ha_onboarding.py")
    print("  python3 scripts/complete_ha_onboarding.py --dry-run")


if __name__ == "__main__":
    main()
