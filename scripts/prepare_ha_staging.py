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

ROOT = Path(__file__).resolve().parent.parent
STAGING = ROOT / "homeassistant" / "staging"
CONFIG = STAGING / "config"


CONFIGURATION_YAML = """# Cloud/staging Home Assistant config for AVAccess UI testing.
# Shell commands are stubs. Do not point this instance at production AV gear.

default_config:

homeassistant:
  name: AVAccess Staging
  unit_system: us
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
    print(f"Staging config ready: {CONFIG}")
    print("Start with:")
    print(f"  docker compose -f {STAGING / 'docker-compose.yml'} up -d")
    print("Then open http://<host>:8123 , complete onboarding, and use the AVAccess Matrix sidebar dashboard.")


if __name__ == "__main__":
    main()
