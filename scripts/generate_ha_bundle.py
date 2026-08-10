#!/usr/bin/env python3
"""Generate Home Assistant package + dashboard from AVAccess configs.

Usage:
  python3 scripts/generate_ha_bundle.py \
    --inventory config/inventory.yaml \
    --channels config/channels.yaml \
    --out-package homeassistant/packages/avaccess_matrix.yaml \
    --out-dashboard homeassistant/dashboards/avaccess_matrix.yaml
"""

from __future__ import annotations

import argparse
import re
from pathlib import Path
from typing import Any

import yaml


def load_yaml(path: Path) -> dict[str, Any]:
    data = yaml.safe_load(path.read_text())
    if not isinstance(data, dict):
        raise SystemExit(f"Expected YAML mapping in {path}")
    return data


def slug(value: str) -> str:
    s = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    return s or "item"


def resolve_presets(inventory: dict[str, Any], profile_override: str | None) -> tuple[str | None, dict[str, Any]]:
    """Return (profile_name, presets) from inventory with backward compatibility."""
    mapping_profiles = inventory.get("mapping_profiles")
    if not mapping_profiles:
        presets = inventory.get("presets")
        if not isinstance(presets, dict) or not presets:
            raise SystemExit("Inventory must include non-empty 'presets' or 'mapping_profiles'")
        return None, presets

    profiles = mapping_profiles.get("profiles", {})
    if not isinstance(profiles, dict) or not profiles:
        raise SystemExit("mapping_profiles.profiles must be a non-empty mapping")

    selected = profile_override or mapping_profiles.get("active")
    if not selected:
        selected = next(iter(profiles))
    if selected not in profiles:
        available = ", ".join(profiles.keys())
        raise SystemExit(f"Unknown profile '{selected}'. Available: {available}")

    profile_data = profiles[selected]
    presets = profile_data.get("presets", {})
    if not isinstance(presets, dict) or not presets:
        raise SystemExit(f"mapping_profiles.profiles.{selected}.presets must be non-empty")

    return selected, presets


def validate_channels(channels_cfg: dict[str, Any]) -> None:
    required_keys = ("program_to_encoder", "encoder_ir_entity", "channels")
    for key in required_keys:
        if key not in channels_cfg:
            raise SystemExit(f"channels file missing required key: {key}")
    if not isinstance(channels_cfg["channels"], dict) or not channels_cfg["channels"]:
        raise SystemExit("channels must be a non-empty mapping")


def build_package(
    inventory: dict[str, Any],
    channels_cfg: dict[str, Any],
    profile_override: str | None,
    inventory_ha_path: str,
) -> dict[str, Any]:
    selected_profile, presets = resolve_presets(inventory, profile_override)
    validate_channels(channels_cfg)

    program_to_encoder = channels_cfg["program_to_encoder"]
    encoder_ir_entity = channels_cfg["encoder_ir_entity"]
    channels = channels_cfg["channels"]
    suffix_commands = channels_cfg.get("suffix_commands", ["ok"])
    digit_delay = channels_cfg.get("digit_delay", "00:00:00.25")

    program_keys = list(program_to_encoder.keys())
    channel_keys = list(channels.keys())
    if not program_keys:
        raise SystemExit("program_to_encoder must include at least one program")

    shell_command: dict[str, str] = {}
    scripts: dict[str, Any] = {}

    profile_part = f" --profile {selected_profile}" if selected_profile else ""
    for preset_key in presets.keys():
        preset_slug = slug(preset_key)
        shell_name = f"avaccess_preset_{preset_slug}"
        shell_command[shell_name] = (
            f"python3 /config/avaccess/scripts/apply_preset.py "
            f"--inventory {inventory_ha_path}{profile_part} --preset {preset_key}"
        )
        scripts[shell_name] = {
            "alias": f"AVAccess Preset {preset_key}",
            "mode": "single",
            "sequence": [{"service": f"shell_command.{shell_name}"}],
        }

    scripts["avaccess_set_program"] = {
        "alias": "AVAccess select program",
        "mode": "single",
        "fields": {
            "program": {"description": "Program key from program_to_encoder", "example": program_keys[0]}
        },
        "sequence": [
            {
                "service": "input_select.select_option",
                "data": {"entity_id": "input_select.avaccess_program", "option": "{{ program }}"},
            }
        ],
    }

    scripts["avaccess_tune_channel"] = {
        "alias": "AVAccess tune channel on Xumo",
        "mode": "queued",
        "fields": {
            "program": {
                "description": "Program key (optional; uses selected program when omitted)",
                "example": program_keys[0],
            },
            "channel": {"description": "Channel key from channels map", "example": channel_keys[0]},
        },
        "variables": {
            "program_to_encoder": program_to_encoder,
            "encoder_ir_entity": encoder_ir_entity,
            "channels": channels,
            "suffix_commands": suffix_commands,
            "program_key": "{{ (program | default(states('input_select.avaccess_program'), true)) | lower }}",
            "channel_key": "{{ (channel | default(states('input_select.avaccess_channel'), true)) | lower }}",
            "selected_encoder": "{{ program_to_encoder[program_key] if program_key in program_to_encoder else none }}",
            "remote_entity": "{{ encoder_ir_entity[selected_encoder] if selected_encoder in encoder_ir_entity else none }}",
            "channel_number": "{{ channels[channel_key]['number'] if channel_key in channels else none }}",
            "digit_delay": digit_delay,
        },
        "sequence": [
            {
                "choose": [
                    {
                        "conditions": "{{ remote_entity is not none and channel_number is not none }}",
                        "sequence": [
                            {
                                "repeat": {
                                    "for_each": "{{ (channel_number | string | list) + suffix_commands }}",
                                    "sequence": [
                                        {
                                            "service": "remote.send_command",
                                            "data": {
                                                "entity_id": "{{ remote_entity }}",
                                                "command": "{{ repeat.item }}",
                                            },
                                        },
                                        {"delay": "{{ digit_delay }}"},
                                    ],
                                }
                            }
                        ],
                    }
                ],
                "default": [
                    {
                        "service": "system_log.write",
                        "data": {
                            "level": "warning",
                            "message": (
                                "AVAccess tune failed; check program/channel maps. "
                                "program={{ program_key }} channel={{ channel_key }}"
                            ),
                        },
                    }
                ],
            }
        ],
    }

    scripts["avaccess_tune_selected_channel"] = {
        "alias": "AVAccess tune selected channel",
        "mode": "single",
        "sequence": [
            {
                "service": "script.avaccess_tune_channel",
                "data": {"channel": "{{ states('input_select.avaccess_channel') }}"},
            }
        ],
    }

    for channel_key, channel_info in channels.items():
        ch_slug = slug(channel_key)
        label = channel_info.get("label", channel_key)
        scripts[f"avaccess_tune_{ch_slug}"] = {
            "alias": f"AVAccess tune {label}",
            "mode": "single",
            "sequence": [
                {
                    "service": "input_select.select_option",
                    "data": {"entity_id": "input_select.avaccess_channel", "option": channel_key},
                },
                {"service": "script.avaccess_tune_selected_channel"},
            ],
        }

    package = {
        "input_select": {
            "avaccess_program": {
                "name": "AVAccess Program",
                "options": program_keys,
                "initial": program_keys[0],
                "icon": "mdi:view-grid-plus",
            },
            "avaccess_channel": {
                "name": "AVAccess Channel",
                "options": channel_keys,
                "initial": channel_keys[0],
                "icon": "mdi:television-guide",
            },
        },
        "shell_command": shell_command,
        "script": scripts,
    }
    return package


def build_dashboard(channels_cfg: dict[str, Any], presets: dict[str, Any]) -> dict[str, Any]:
    channels = channels_cfg["channels"]
    program_keys = list(channels_cfg["program_to_encoder"].keys())

    preset_buttons = []
    for preset_key in presets.keys():
        preset_slug = slug(preset_key)
        preset_buttons.append(
            {
                "type": "button",
                "name": preset_key,
                "icon": "mdi:video-switch",
                "tap_action": {"action": "call-service", "service": f"script.avaccess_preset_{preset_slug}"},
            }
        )

    program_buttons = []
    for program_key in program_keys:
        program_buttons.append(
            {
                "type": "button",
                "name": program_key,
                "icon": "mdi:monitor-dashboard",
                "tap_action": {
                    "action": "call-service",
                    "service": "script.avaccess_set_program",
                    "data": {"program": program_key},
                },
            }
        )

    channel_buttons = []
    for channel_key, info in channels.items():
        ch_slug = slug(channel_key)
        channel_buttons.append(
            {
                "type": "button",
                "name": info.get("label", channel_key),
                "icon": "mdi:television-play",
                "tap_action": {"action": "call-service", "service": f"script.avaccess_tune_{ch_slug}"},
            }
        )

    dashboard = {
        "title": "AVAccess Matrix",
        "views": [
            {
                "title": "AV Control",
                "path": "av-control",
                "icon": "mdi:video-input-component",
                "cards": [
                    {
                        "type": "entities",
                        "title": "Active Selection",
                        "entities": ["input_select.avaccess_program", "input_select.avaccess_channel"],
                    },
                    {"type": "grid", "title": "Presets", "columns": 3, "square": False, "cards": preset_buttons},
                    {"type": "grid", "title": "Programs", "columns": 3, "square": False, "cards": program_buttons},
                    {"type": "grid", "title": "Channels", "columns": 4, "square": False, "cards": channel_buttons},
                ],
            }
        ],
    }
    return dashboard


def write_yaml(path: Path, data: dict[str, Any], header: str) -> None:
    text = yaml.safe_dump(data, sort_keys=False, width=120, allow_unicode=False)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{header}\n{text}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--channels", type=Path, required=True)
    parser.add_argument("--profile", help="Optional mapping profile override.")
    parser.add_argument(
        "--inventory-ha-path",
        default="/config/avaccess/config/inventory.yaml",
        help="Path Home Assistant should use when calling apply_preset.py",
    )
    parser.add_argument("--out-package", type=Path, required=True)
    parser.add_argument("--out-dashboard", type=Path, required=True)
    args = parser.parse_args()

    inventory = load_yaml(args.inventory)
    channels_cfg = load_yaml(args.channels)
    selected_profile, presets = resolve_presets(inventory, args.profile)
    package = build_package(
        inventory=inventory,
        channels_cfg=channels_cfg,
        profile_override=selected_profile,
        inventory_ha_path=args.inventory_ha_path,
    )
    dashboard = build_dashboard(channels_cfg=channels_cfg, presets=presets)

    pkg_header = (
        "# Generated by scripts/generate_ha_bundle.py\n"
        "# Place under Home Assistant packages and include via packages: !include_dir_named packages\n"
    )
    dash_header = (
        "# Generated by scripts/generate_ha_bundle.py\n"
        "# Import into Lovelace (Raw configuration editor) or dashboard YAML mode\n"
    )
    write_yaml(args.out_package, package, pkg_header)
    write_yaml(args.out_dashboard, dashboard, dash_header)
    print(f"Wrote package: {args.out_package}")
    print(f"Wrote dashboard: {args.out_dashboard}")


if __name__ == "__main__":
    main()
