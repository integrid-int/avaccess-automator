#!/usr/bin/env python3
"""Validate Home Assistant panel_custom registrations."""

from __future__ import annotations

import argparse
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import yaml


REQUIRED_PANEL_FIELDS = ("name", "sidebar_title", "url_path", "module_url")


@dataclass
class PanelValidationError:
    panel_name: str
    message: str

    def render(self) -> str:
        return f"[{self.panel_name}] {self.message}"


def _load_configuration(configuration_path: Path) -> dict:
    if not configuration_path.exists():
        raise FileNotFoundError(
            f"Home Assistant configuration file was not found: {configuration_path}"
        )

    with configuration_path.open("r", encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}

    if not isinstance(data, dict):
        raise ValueError(f"Expected mapping in {configuration_path}, got {type(data)}")

    return data


def _normalize_panel_entries(raw_panels: object) -> list[dict]:
    if raw_panels is None:
        return []

    if not isinstance(raw_panels, list):
        raise ValueError("`panel_custom` must be a list of panel definitions.")

    normalized: list[dict] = []
    for index, item in enumerate(raw_panels):
        if not isinstance(item, dict):
            raise ValueError(f"`panel_custom[{index}]` must be a mapping.")
        normalized.append(item)

    return normalized


def _file_from_module_url(config_dir: Path, module_url: str) -> Path:
    module_path = module_url.split("?", 1)[0]
    relative = module_path.removeprefix("/local/")
    return (config_dir / "www" / relative).resolve()


def _validate_custom_element(panel: dict, panel_file: Path) -> str | None:
    panel_name = str(panel.get("name", "<unnamed>"))
    source = panel_file.read_text(encoding="utf-8")
    quoted_name = f"customElements.define('{panel_name}'"
    double_quoted_name = f'customElements.define("{panel_name}"'

    if quoted_name in source or double_quoted_name in source:
        return None

    return (
        "Panel module does not define matching custom element "
        f"`{panel_name}` via customElements.define()."
    )


def validate_panels(config_dir: Path, configuration_file: str = "configuration.yaml") -> list[str]:
    """Return a list of validation errors. Empty list means valid."""

    config_dir = config_dir.resolve()
    configuration_path = config_dir / configuration_file
    data = _load_configuration(configuration_path)
    panels = _normalize_panel_entries(data.get("panel_custom"))

    errors: list[PanelValidationError] = []

    if not panels:
        errors.append(
            PanelValidationError(
                panel_name="global",
                message="No `panel_custom` entries were found in configuration.",
            )
        )
        return [error.render() for error in errors]

    for panel in panels:
        panel_name = str(panel.get("name", "<unnamed>"))

        for field in REQUIRED_PANEL_FIELDS:
            if not panel.get(field):
                errors.append(
                    PanelValidationError(
                        panel_name=panel_name,
                        message=f"Missing required field `{field}`.",
                    )
                )

        module_url = str(panel.get("module_url", ""))
        if module_url and not module_url.startswith("/local/"):
            errors.append(
                PanelValidationError(
                    panel_name=panel_name,
                    message="`module_url` must start with `/local/` for mounted panel assets.",
                )
            )
            continue

        if not module_url:
            continue

        panel_file = _file_from_module_url(config_dir, module_url)
        if not panel_file.exists():
            errors.append(
                PanelValidationError(
                    panel_name=panel_name,
                    message=f"Panel module is missing: {panel_file}",
                )
            )
            continue

        element_error = _validate_custom_element(panel, panel_file)
        if element_error:
            errors.append(PanelValidationError(panel_name=panel_name, message=element_error))

    return [error.render() for error in errors]


def _print_errors(errors: Iterable[str]) -> None:
    for error in errors:
        print(f"ERROR: {error}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Validate Home Assistant `panel_custom` entries and panel assets."
    )
    parser.add_argument(
        "--config-dir",
        default="homeassistant/config",
        help="Path to Home Assistant config directory (default: homeassistant/config).",
    )
    parser.add_argument(
        "--configuration-file",
        default="configuration.yaml",
        help="Configuration file name inside config dir (default: configuration.yaml).",
    )
    args = parser.parse_args()

    errors = validate_panels(Path(args.config_dir), args.configuration_file)
    if errors:
        _print_errors(errors)
        return 1

    print("Panel validation passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
