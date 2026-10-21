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
import copy
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


PRESET_DISPLAY_NAMES = {
    "1_all": "ALL",
    "2_four_programs": "4 Programs",
    "3_nine_programs": "9 Programs",
}

# Valid MDI names (mdi:television-multiple does not exist and renders blank).
ROUTE_ICON = "mdi:monitor-multiple"


def friendly_preset_name(preset_key: str) -> str:
    """Human-readable Control-tab label; script entity_ids still use slug(preset_key)."""
    if preset_key in PRESET_DISPLAY_NAMES:
        return PRESET_DISPLAY_NAMES[preset_key]
    pretty = preset_key.replace("_", " ").strip()
    if pretty.lower().startswith("preset "):
        return pretty
    return f"Preset {pretty}"


def friendly_program_name(program_key: str) -> str:
    """Human-readable Control-tab label; script data still uses the raw program key."""
    match = re.fullmatch(r"program_([a-z])", program_key, re.IGNORECASE)
    if match:
        return f"Program {match.group(1).upper()}"
    pretty = program_key.replace("_", " ").strip()
    if pretty.lower().startswith("program "):
        return pretty
    return f"Program {pretty}"


def friendly_channel_names(channels: dict[str, Any]) -> dict[str, str]:
    """Map channel key -> unique operator-facing label (used as input_select option)."""
    out: dict[str, str] = {}
    seen: set[str] = set()
    for channel_key, info in channels.items():
        label = str((info or {}).get("label") or channel_key) if isinstance(info, dict) else str(channel_key)
        if label in seen:
            label = f"{label} ({channel_key})"
        seen.add(label)
        out[str(channel_key)] = label
    return out


def friendly_program_names(program_keys: list[str]) -> dict[str, str]:
    """Map program key -> unique operator-facing label (used as input_select option)."""
    out: dict[str, str] = {}
    seen: set[str] = set()
    for key in program_keys:
        label = friendly_program_name(key)
        if label in seen:
            label = f"{label} ({key})"
        seen.add(label)
        out[key] = label
    return out


def _key_from_option(field: str, entity: str, label_to_key: str) -> str:
    """Jinja: accept a raw key or a friendly input_select label and return the raw key."""
    return (
        f"{{% set raw = ({field} | default(states('{entity}'), true)) | string %}}"
        f"{{{{ {label_to_key}[raw] if raw in {label_to_key} else raw | lower }}}}"
    )


def staging_now_playing_entity_id(media_player_entity: str) -> str:
    """Map a missing DirecTV media_player to a dummy template sensor object id."""
    object_id = slug(str(media_player_entity).split(".", 1)[-1])
    return f"sensor.{object_id}"


def remap_encoder_media_player_for_staging(encoder_media_player: dict[str, Any]) -> dict[str, str]:
    if not isinstance(encoder_media_player, dict):
        return {}
    return {
        str(enc_id): staging_now_playing_entity_id(str(entity_id))
        for enc_id, entity_id in encoder_media_player.items()
    }


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
    required_keys = ("program_to_encoder", "channels")
    for key in required_keys:
        if key not in channels_cfg:
            raise SystemExit(f"channels file missing required key: {key}")
    if not isinstance(channels_cfg["channels"], dict) or not channels_cfg["channels"]:
        raise SystemExit("channels must be a non-empty mapping")
    ir_transport = str(
        channels_cfg.get("source_transport") or channels_cfg.get("ir_transport") or "directv_shef"
    ).strip().lower()
    if ir_transport not in {"ha_remote", "itach_tcp", "directv_shef"}:
        raise SystemExit("ir_transport/source_transport must be ha_remote, itach_tcp, or directv_shef")
    if ir_transport == "ha_remote" and "encoder_ir_entity" not in channels_cfg:
        raise SystemExit("channels file missing required key for ha_remote mode: encoder_ir_entity")
    if ir_transport == "directv_shef" and not channels_cfg.get("directv_config_path"):
        raise SystemExit("directv_shef mode requires directv_config_path")


def build_package(
    inventory: dict[str, Any],
    channels_cfg: dict[str, Any],
    profile_override: str | None,
    inventory_ha_path: str,
) -> dict[str, Any]:
    selected_profile, presets = resolve_presets(inventory, profile_override)
    validate_channels(channels_cfg)

    program_to_encoder = channels_cfg["program_to_encoder"]
    ir_transport = str(
        channels_cfg.get("source_transport") or channels_cfg.get("ir_transport") or "directv_shef"
    ).strip().lower()
    encoder_ir_entity = channels_cfg.get("encoder_ir_entity", {})
    encoder_media_player = channels_cfg.get("encoder_media_player", {})
    channels = channels_cfg["channels"]
    suffix_commands = channels_cfg.get("suffix_commands", ["ok"])
    digit_delay = channels_cfg.get("digit_delay", "00:00:00.25")
    digit_delay_ms = int(channels_cfg.get("digit_delay_ms", 250))
    itach_config_path = str(channels_cfg.get("itach_config_path", "/config/avaccess/config/itach.yaml"))
    directv_config_path = str(
        channels_cfg.get("directv_config_path", "/config/avaccess/config/directv.yaml")
    )

    program_keys = list(program_to_encoder.keys())
    channel_keys = list(channels.keys())
    if not program_keys:
        raise SystemExit("program_to_encoder must include at least one program")
    program_labels = friendly_program_names(program_keys)
    channel_labels = friendly_channel_names(channels)
    program_label_to_key = {label: key for key, label in program_labels.items()}
    channel_label_to_key = {label: key for key, label in channel_labels.items()}
    program_key_template = _key_from_option("program", "input_select.avaccess_program", "program_label_to_key")
    channel_key_template = _key_from_option("channel", "input_select.avaccess_channel", "channel_label_to_key")

    shell_command: dict[str, str] = {}
    scripts: dict[str, Any] = {}

    profile_part = f" --profile {selected_profile}" if selected_profile else ""
    for preset_key in presets.keys():
        preset_slug = slug(preset_key)
        shell_name = f"avaccess_preset_{preset_slug}"
        shell_command[shell_name] = (
            f"python3 /config/avaccess/apply_preset.py "
            f"--inventory {inventory_ha_path}{profile_part} --preset {preset_key}"
        )
        scripts[shell_name] = {
            "alias": f"AVAccess Preset {preset_key}",
            "mode": "single",
            "sequence": [{"service": f"shell_command.{shell_name}"}],
        }

    preset_choices = []
    for preset_key in presets.keys():
        preset_name = friendly_preset_name(preset_key)
        preset_choices.append(
            {
                "conditions": (
                    "{{ states('input_select.avaccess_active_preset') == '" + preset_name + "' }}"
                ),
                "sequence": [{"service": f"script.avaccess_preset_{slug(preset_key)}"}],
            }
        )
    scripts["avaccess_apply_selected_preset"] = {
        "alias": "AVAccess apply selected preset",
        "mode": "single",
        "sequence": [
            {
                "choose": preset_choices,
                "default": [
                    {
                        "service": "system_log.write",
                        "data": {
                            "level": "warning",
                            "message": (
                                "AVAccess apply preset: pick ALL, 4 Programs, or 9 Programs first. "
                                "selected={{ states('input_select.avaccess_active_preset') }}"
                            ),
                        },
                    }
                ],
            }
        ],
    }

    shell_command["avaccess_route_targets"] = (
        "python3 /config/avaccess/route_targets.py "
        f"--inventory {inventory_ha_path} --encoder \"{{{{ encoder }}}}\" --targets \"{{{{ targets }}}}\""
    )
    if ir_transport == "itach_tcp":
        shell_command["avaccess_itach_send_channel"] = (
            "python3 /config/avaccess/scripts/send_xumo_ir_itach.py "
            f"--itach-config {itach_config_path} --encoder \"{{{{ encoder }}}}\" "
            "--digits \"{{ digits }}\" --suffix \"{{ suffix }}\" --digit-delay-ms {{ digit_delay_ms }}"
        )
    if ir_transport == "directv_shef":
        shell_command["avaccess_directv_tune"] = (
            "python3 /config/avaccess/directv_shef.py "
            f"--config {directv_config_path} tune --encoder \"{{{{ encoder }}}}\" "
            "--channel \"{{ channel }}\""
        )
        shell_command["avaccess_directv_get_tuned"] = (
            "python3 /config/avaccess/directv_shef.py "
            f"--config {directv_config_path} get-tuned --encoder \"{{{{ encoder }}}}\""
        )

    scripts["avaccess_set_program"] = {
        "alias": "AVAccess select program",
        "mode": "single",
        "fields": {
            "program": {"description": "Program key from program_to_encoder", "example": program_keys[0]}
        },
        "variables": {
            "program_key_to_label": program_labels,
            "program_label_to_key": program_label_to_key,
            "program_key": program_key_template,
        },
        "sequence": [
            {
                "service": "input_select.select_option",
                "data": {
                    "entity_id": "input_select.avaccess_program",
                    "option": "{{ program_key_to_label[program_key] if program_key in program_key_to_label else program }}",
                },
            }
        ],
    }

    tune_variables: dict[str, Any] = {
        "program_to_encoder": program_to_encoder,
        "channels": channels,
        "suffix_commands": suffix_commands,
        "program_label_to_key": program_label_to_key,
        "channel_label_to_key": channel_label_to_key,
        "program_key": program_key_template,
        "channel_key": channel_key_template,
        "selected_encoder": "{{ program_to_encoder[program_key] if program_key in program_to_encoder else none }}",
        "channel_number": "{{ channels[channel_key]['number'] if channel_key in channels else none }}",
        "digit_delay": digit_delay,
        "digit_delay_ms": digit_delay_ms,
        "suffix_text": "{{ suffix_commands | join(',') }}",
    }
    if ir_transport == "ha_remote":
        tune_variables["encoder_ir_entity"] = encoder_ir_entity
        tune_variables["remote_entity"] = (
            "{{ encoder_ir_entity[selected_encoder] if selected_encoder in encoder_ir_entity else none }}"
        )
        tune_sequence = [
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
                                "AVAccess tune failed (ha_remote); check program/channel/entity maps. "
                                "program={{ program_key }} channel={{ channel_key }}"
                            ),
                        },
                    }
                ],
            }
        ]
    elif ir_transport == "directv_shef":
        tune_sequence = [
            {
                "choose": [
                    {
                        "conditions": "{{ selected_encoder is not none and channel_number is not none }}",
                        "sequence": [
                            {
                                "service": "shell_command.avaccess_directv_tune",
                                "data": {
                                    "encoder": "{{ selected_encoder }}",
                                    "channel": "{{ channel_number }}",
                                },
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
                                "AVAccess tune failed (directv_shef); check program/channel/H25 maps. "
                                "program={{ program_key }} channel={{ channel_key }}"
                            ),
                        },
                    }
                ],
            }
        ]
    else:
        tune_sequence = [
            {
                "choose": [
                    {
                        "conditions": "{{ selected_encoder is not none and channel_number is not none }}",
                        "sequence": [
                            {
                                "service": "shell_command.avaccess_itach_send_channel",
                                "data": {
                                    "encoder": "{{ selected_encoder }}",
                                    "digits": "{{ channel_number }}",
                                    "suffix": "{{ suffix_text }}",
                                    "digit_delay_ms": "{{ digit_delay_ms }}",
                                },
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
                                "AVAccess tune failed (itach_tcp); check program/channel/itach maps. "
                                "program={{ program_key }} channel={{ channel_key }}"
                            ),
                        },
                    }
                ],
            }
        ]

    scripts["avaccess_tune_channel"] = {
        "alias": "AVAccess tune channel on source",
        "mode": "queued",
        "fields": {
            "program": {
                "description": "Program key (optional; uses selected program when omitted)",
                "example": program_keys[0],
            },
            "channel": {"description": "Channel key from channels map", "example": channel_keys[0]},
        },
        "variables": tune_variables,
        "sequence": tune_sequence,
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

    scripts["avaccess_route_program_to_tvs"] = {
        "alias": "AVAccess route program to TVs",
        "mode": "single",
        "fields": {
            "program": {
                "description": "Program key (optional; defaults to selected program)",
                "example": program_keys[0],
            },
            "targets": {
                "description": "Receiver IDs/hostnames list (optional; defaults to input_text)",
                "example": "RX-01,RX-02,RX-03",
            },
        },
        "variables": {
            "program_to_encoder": program_to_encoder,
            "program_label_to_key": program_label_to_key,
            "program_key": program_key_template,
            "selected_encoder": "{{ program_to_encoder[program_key] if program_key in program_to_encoder else none }}",
            "target_list": "{{ targets | default(states('input_text.avaccess_target_rxs'), true) }}",
        },
        "sequence": [
            {
                "choose": [
                    {
                        "conditions": "{{ selected_encoder is not none and (target_list | string | trim) != '' }}",
                        "sequence": [
                            {
                                "service": "shell_command.avaccess_route_targets",
                                "data": {
                                    "encoder": "{{ selected_encoder }}",
                                    "targets": "{{ target_list }}",
                                },
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
                                "AVAccess route failed; check selected program and target TVs. "
                                "program={{ program_key }} targets={{ target_list }}"
                            ),
                        },
                    }
                ],
            }
        ],
    }

    scripts["avaccess_route_selected_program_to_tvs"] = {
        "alias": "AVAccess route selected program to TVs",
        "mode": "single",
        "sequence": [{"service": "script.avaccess_route_program_to_tvs"}],
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
                    "data": {"entity_id": "input_select.avaccess_channel", "option": channel_labels[channel_key]},
                },
                {"service": "script.avaccess_tune_selected_channel"},
            ],
        }

    # Optional "favorite scenes" that combine preset recall + multi-program channel tune.
    favorites = channels_cfg.get("favorites", {})
    if favorites and not isinstance(favorites, dict):
        raise SystemExit("favorites must be a mapping when provided")
    preset_delay = channels_cfg.get("favorite_preset_delay", "00:00:02")
    preset_script_by_key = {k: f"script.avaccess_preset_{slug(k)}" for k in presets.keys()}
    for favorite_key, favorite in favorites.items():
        if not isinstance(favorite, dict):
            raise SystemExit(f"favorites.{favorite_key} must be a mapping")
        fav_slug = slug(favorite_key)
        fav_label = favorite.get("label", favorite_key)
        fav_preset = favorite.get("preset")
        fav_tunes = favorite.get("tunes", [])
        if not isinstance(fav_tunes, list):
            raise SystemExit(f"favorites.{favorite_key}.tunes must be a list")

        sequence: list[dict[str, Any]] = []
        if fav_preset:
            if fav_preset not in preset_script_by_key:
                available = ", ".join(presets.keys())
                raise SystemExit(
                    f"favorites.{favorite_key}.preset '{fav_preset}' not found in presets ({available})"
                )
            sequence.append({"service": preset_script_by_key[fav_preset]})
            sequence.append({"delay": preset_delay})

        for idx, tune in enumerate(fav_tunes, 1):
            if not isinstance(tune, dict):
                raise SystemExit(f"favorites.{favorite_key}.tunes[{idx}] must be a mapping")
            program = tune.get("program")
            channel = tune.get("channel")
            if not program or not channel:
                raise SystemExit(
                    f"favorites.{favorite_key}.tunes[{idx}] must include 'program' and 'channel'"
                )
            sequence.append(
                {
                    "service": "script.avaccess_tune_channel",
                    "data": {"program": str(program).lower(), "channel": str(channel).lower()},
                }
            )
            if tune.get("delay_after"):
                sequence.append({"delay": tune["delay_after"]})

        if not sequence:
            raise SystemExit(
                f"favorites.{favorite_key} has no actions. Define preset and/or tunes."
            )

        scripts[f"avaccess_favorite_{fav_slug}"] = {
            "alias": f"AVAccess Favorite {fav_label}",
            "mode": "single",
            "sequence": sequence,
        }

    package = {
        "input_select": {
            "avaccess_program": {
                "name": "AVAccess Program",
                "options": [program_labels[k] for k in program_keys],
                "initial": program_labels[program_keys[0]],
                "icon": "mdi:view-grid-plus",
            },
            "avaccess_channel": {
                "name": "AVAccess Channel",
                "options": [channel_labels[k] for k in channel_keys],
                "initial": channel_labels[channel_keys[0]],
                "icon": "mdi:television-guide",
            },
            "avaccess_active_preset": {
                "name": "AVAccess Active Preset",
                "options": ["None", *[friendly_preset_name(k) for k in presets.keys()]],
                "initial": "None",
                "icon": "mdi:video-switch",
            },
        },
        "input_text": {
            "avaccess_target_rxs": {
                "name": "AVAccess Target TVs",
                "max": 255,
                "initial": "RX-01, RX-02",
                "icon": ROUTE_ICON,
            }
        },
        "shell_command": shell_command,
        "script": scripts,
    }
    return package


def _selectable_buttons(
    name: str,
    icon: str,
    tap_action: dict[str, Any],
    entity: str,
    option: str,
) -> list[dict[str, Any]]:
    """One key. The card turns blue when the input_select matches this option."""
    del icon  # Stock HA icons are not the bar-panel key. The custom card paints the latch.
    return [_key_card(name, tap_action, variant="choice", selected_entity=entity, selected_state=option)]


def _key_card(
    name: str,
    tap_action: dict[str, Any],
    *,
    variant: str,
    detail: str | None = None,
    selected_entity: str | None = None,
    selected_state: str | None = None,
) -> dict[str, Any]:
    """Charcoal key from the Sports Routing panel. Action keys stay blue."""
    card: dict[str, Any] = {
        "type": "custom:avaccess-key",
        "name": name,
        "variant": variant,
        "tap_action": tap_action,
    }
    if detail:
        card["detail"] = detail
    if selected_entity:
        card["selected_entity"] = selected_entity
        card["selected_state"] = selected_state
    return card


def _build_channel_buttons(
    channels: dict[str, Any], channel_keys: list[str] | None = None, icon: str = "mdi:television-play"
) -> list[dict[str, Any]]:
    keys = channel_keys or list(channels.keys())
    labels = friendly_channel_names(channels)
    out: list[dict[str, Any]] = []
    for channel_key in keys:
        if channel_key not in channels:
            continue
        out.extend(
            _selectable_buttons(
                labels[channel_key],
                icon,
                {
                    "action": "call-service",
                    "service": "input_select.select_option",
                    "data": {
                        "entity_id": "input_select.avaccess_channel",
                        "option": labels[channel_key],
                    },
                },
                "input_select.avaccess_channel",
                labels[channel_key],
            )
        )
    return out


def _now_playing_cards(encoder_media_player: dict[str, Any], ui_staging: bool) -> list[dict[str, Any]]:
    """Per-encoder rows, collapsed to one banner when every receiver reports the same idle status."""
    if not isinstance(encoder_media_player, dict) or not encoder_media_player:
        return []
    entity_ids = [str(entity_id) for entity_id in encoder_media_player.values()]
    entities = [{"entity": str(entity_id), "name": str(enc_id)} for enc_id, entity_id in encoder_media_player.items()]
    shared_status = "STAGING - DirecTV not connected" if ui_staging else "unavailable"
    banner_text = (
        "STAGING – DirecTV not connected" if ui_staging else "DirecTV receivers unavailable"
    )
    return [
        {
            "type": "conditional",
            "conditions": [
                {"condition": "state", "entity": entity_id, "state": shared_status} for entity_id in entity_ids
            ],
            "card": {
                "type": "markdown",
                "content": (
                    "### Now Playing (DirecTV)\n\n"
                    f"<ha-alert alert-type=\"warning\">All {len(entity_ids)} receivers: "
                    f"**{banner_text}**</ha-alert>"
                ),
            },
        },
        {
            "type": "conditional",
            "conditions": [
                {
                    "condition": "or",
                    "conditions": [
                        {"condition": "state", "entity": entity_id, "state_not": shared_status}
                        for entity_id in entity_ids
                    ],
                }
            ],
            "card": {"type": "entities", "title": "Now Playing (DirecTV)", "entities": entities},
        },
    ]


def _label(text: str, variant: str = "section") -> dict[str, Any]:
    return {"type": "custom:avaccess-label", "text": text, "variant": variant}


def _selection_card(title: str) -> dict[str, Any]:
    return {
        "type": "entities",
        "title": title,
        "show_header_toggle": False,
        "entities": [
            {"entity": "input_select.avaccess_program", "name": "Program"},
            {"entity": "input_select.avaccess_channel", "name": "Channel"},
            {"entity": "input_text.avaccess_target_rxs", "name": "Target TVs"},
        ],
    }


def _stack(cards: list[dict[str, Any]]) -> dict[str, Any]:
    """One full-width column. Masonry would scatter these cards into uneven columns."""
    return {"type": "vertical-stack", "cards": cards}


def _panel_view(title: str, path: str, cards: list[dict[str, Any]]) -> dict[str, Any]:
    # No view icon: Home Assistant otherwise hides the title and shows a glyph only.
    return {
        "title": title,
        "path": path,
        "theme": "Avaccess Routing",
        "type": "panel",
        "cards": [_stack(cards)],
    }


def _keys(title: str, cards: list[dict[str, Any]], columns: int) -> dict[str, Any]:
    card: dict[str, Any] = {"type": "grid", "columns": columns, "square": False, "cards": cards}
    if title:
        card["title"] = title
    return card


def _route_actions_card() -> dict[str, Any]:
    return _keys(
        "",
        [
            _key_card(
                "Tune Selected Program",
                {"action": "call-service", "service": "script.avaccess_tune_selected_channel"},
                variant="action",
                detail="Changes the DirecTV box only",
            ),
            _key_card(
                "Route Program → TVs",
                {"action": "call-service", "service": "script.avaccess_route_selected_program_to_tvs"},
                variant="action",
                detail="Points the TVs at that box",
            ),
            _key_card(
                "Apply Preset",
                {"action": "call-service", "service": "script.avaccess_apply_selected_preset"},
                variant="action",
                detail="Changes which TVs watch which box",
            ),
        ],
        1,
    )


def build_dashboard(
    channels_cfg: dict[str, Any],
    presets: dict[str, Any],
    ui_staging: bool = False,
) -> dict[str, Any]:
    channels = channels_cfg["channels"]
    program_keys = list(channels_cfg["program_to_encoder"].keys())
    program_labels = friendly_program_names(program_keys)
    encoder_media_player = channels_cfg.get("encoder_media_player", {})
    if ui_staging:
        encoder_media_player = remap_encoder_media_player_for_staging(encoder_media_player or {})
    now_playing = _now_playing_cards(encoder_media_player or {}, ui_staging)

    preset_buttons = []
    for preset_key in presets.keys():
        preset_name = friendly_preset_name(preset_key)
        preset_buttons.extend(
            _selectable_buttons(
                preset_name,
                "mdi:video-switch",
                {
                    "action": "call-service",
                    "service": "input_select.select_option",
                    "data": {"entity_id": "input_select.avaccess_active_preset", "option": preset_name},
                },
                "input_select.avaccess_active_preset",
                preset_name,
            )
        )

    program_buttons = []
    for program_key in program_keys:
        program_buttons.extend(
            _selectable_buttons(
                program_labels[program_key],
                "mdi:monitor-dashboard",
                {
                    "action": "call-service",
                    "service": "script.avaccess_set_program",
                    "data": {"program": program_key},
                },
                "input_select.avaccess_program",
                program_labels[program_key],
            )
        )

    channel_buttons = _build_channel_buttons(channels)

    favorites = channels_cfg.get("favorites", {})
    favorite_buttons = []
    if isinstance(favorites, dict):
        for favorite_key, favorite in favorites.items():
            fav_slug = slug(favorite_key)
            fav_label = (
                favorite.get("label", favorite_key)
                if isinstance(favorite, dict)
                else str(favorite_key)
            )
            favorite_buttons.append(
                _key_card(
                    fav_label,
                    {
                        "action": "call-service",
                        "service": f"script.avaccess_favorite_{fav_slug}",
                    },
                    variant="favorite",
                    detail="Runs now",
                )
            )

    # Full-width banks. A side-by-side column left the right half empty once Sources got long,
    # and the route keys scrolled off the top. The same route keys sit under Bar and again
    # after the lists so a commit is still on screen.
    control_cards: list[dict[str, Any]] = [
        _label("Bar", "room"),
        _selection_card("Selected"),
        *copy.deepcopy(now_playing),
        _label("Actions"),
        _route_actions_card(),
        _label("Displays"),
        _keys("", preset_buttons, 2),
        _label("Sources"),
        _keys("", program_buttons, 2),
        _keys("", channel_buttons, 2),
    ]
    if favorite_buttons:
        control_cards.extend(
            [
                _label("Favorites"),
                _keys("", favorite_buttons, 1),
            ]
        )
    control_cards.append(_route_actions_card())

    views: list[dict[str, Any]] = [_panel_view("AV Control", "av-control", control_cards)]

    sports_pages = channels_cfg.get("sports_pages", {})
    if isinstance(sports_pages, dict):
        for page_key, page_cfg in sports_pages.items():
            if not isinstance(page_cfg, dict):
                continue
            page_title = str(page_cfg.get("title", page_key.upper()))
            page_path = str(page_cfg.get("path", slug(page_key)))
            page_desc = str(page_cfg.get("description", "")).replace("->", "→")
            page_channels = page_cfg.get("channels", [])
            if not isinstance(page_channels, list) or not page_channels:
                continue
            buttons = _build_channel_buttons(channels, [str(c) for c in page_channels], icon="mdi:television-play")
            if not buttons:
                continue
            channel_columns = 2
            page_cards: list[dict[str, Any]] = [_label("Bar", "room")]
            if page_desc:
                page_cards.append({"type": "markdown", "content": page_desc})
            page_cards.extend(
                [
                    _selection_card("Selected"),
                    *copy.deepcopy(now_playing),
                    _label("Actions"),
                    _route_actions_card(),
                    _label("Sources"),
                    _keys(page_title, buttons, channel_columns),
                    _label("Actions"),
                    _route_actions_card(),
                ]
            )
            views.append(_panel_view(page_title, page_path, page_cards))

    dashboard = {"title": "AVAccess Matrix", "views": views}
    return dashboard


def apply_ui_staging_stubs(
    package: dict[str, Any],
    encoder_media_player: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Stub shell commands and inject dummy Now Playing sensors for cloud HA UI testing.

    Staging Lovelace cannot load official DirecTV media_player entities, so modern
    `template:` sensors reuse the media_player object id (sensor.directv_h25_01, ...)
    and the dashboard is remapped to those ids when --ui-staging is on.

    HA 2026.9 rejects legacy `sensor: platform: template`; emit the modern key here
    instead of relying on a post-process rewrite.
    """
    commands = package.get("shell_command", {})
    if isinstance(commands, dict):
        package["shell_command"] = {name: f'echo "STAGING {name}"' for name in commands}

    sensors: list[dict[str, Any]] = []
    if isinstance(encoder_media_player, dict):
        for enc_id, entity_id in encoder_media_player.items():
            object_id = slug(str(entity_id).split(".", 1)[-1])
            sensors.append(
                {
                    "default_entity_id": f"sensor.{object_id}",
                    "name": str(enc_id),
                    "unique_id": f"staging_{object_id}",
                    "state": "{{ 'STAGING - DirecTV not connected' }}",
                    "icon": "mdi:satellite-uplink",
                }
            )
    if sensors:
        new_block = {"sensor": sensors}
        existing = package.get("template")
        if existing is None:
            package["template"] = [new_block]
        elif isinstance(existing, list):
            existing.append(new_block)
        else:
            package["template"] = [existing, new_block]
    return package


def write_yaml(path: Path, data: dict[str, Any], header: str) -> None:
    text = yaml.safe_dump(data, sort_keys=False, width=120, allow_unicode=True)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"{header}\n{text}", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--inventory", type=Path, required=True)
    parser.add_argument("--channels", type=Path, required=True)
    parser.add_argument(
        "--profile",
        default="numeric_v1",
        help="Mapping profile for Lovelace presets (default numeric_v1). Track B bartender uses striped_v1 via inventory.active.",
    )
    parser.add_argument(
        "--inventory-ha-path",
        default="/config/avaccess/config/inventory.yaml",
        help="Path Home Assistant should use when calling apply_preset.py",
    )
    parser.add_argument("--out-package", type=Path, required=True)
    parser.add_argument("--out-dashboard", type=Path, required=True)
    parser.add_argument(
        "--ui-staging",
        action="store_true",
        help=(
            "Stub shell_command calls and replace DirecTV media_player Now Playing "
            "cards with dummy template sensors so a cloud HA instance can load the UI "
            "without AV LAN hardware."
        ),
    )
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
    if args.ui_staging:
        package = apply_ui_staging_stubs(
            package,
            encoder_media_player=channels_cfg.get("encoder_media_player", {}),
        )
    dashboard = build_dashboard(
        channels_cfg=channels_cfg,
        presets=presets,
        ui_staging=args.ui_staging,
    )

    pkg_header = (
        "# Generated by scripts/generate_ha_bundle.py\n"
        "# Place under Home Assistant packages and include via packages: !include_dir_named packages\n"
    )
    if args.ui_staging:
        pkg_header += (
            "# UI-STAGING: shell_command entries are echo stubs (no AV/DirecTV hardware required)\n"
            "# UI-STAGING: Now Playing uses HA 2026.9 template sensors instead of DirecTV media_player entities\n"
        )
    dash_header = (
        "# Generated by scripts/generate_ha_bundle.py\n"
        "# Import into Lovelace (Raw configuration editor) or dashboard YAML mode\n"
    )
    if args.ui_staging:
        dash_header += (
            "# UI-STAGING: Now Playing cards reference sensor.directv_* dummies, not media_player.directv_*\n"
        )
    write_yaml(args.out_package, package, pkg_header)
    write_yaml(args.out_dashboard, dashboard, dash_header)
    print(f"Wrote package: {args.out_package}")
    print(f"Wrote dashboard: {args.out_dashboard}")
    if args.ui_staging:
        print("UI staging stubs enabled (shell commands will not touch hardware).")


if __name__ == "__main__":
    main()
