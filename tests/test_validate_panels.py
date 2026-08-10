from pathlib import Path

from scripts.validate_panels import validate_panels


def _write_config(config_dir: Path, module_url: str = "/local/panels/test-panel.js") -> None:
    config_dir.mkdir(parents=True, exist_ok=True)
    config_dir.joinpath("configuration.yaml").write_text(
        "\n".join(
            [
                "default_config:",
                "panel_custom:",
                "  - name: test-panel",
                "    sidebar_title: Test Panel",
                "    sidebar_icon: mdi:view-dashboard",
                "    url_path: test-panel",
                f"    module_url: {module_url}",
            ]
        ),
        encoding="utf-8",
    )


def _write_panel_asset(config_dir: Path, element_name: str = "test-panel") -> None:
    panel_file = config_dir / "www" / "panels" / "test-panel.js"
    panel_file.parent.mkdir(parents=True, exist_ok=True)
    panel_file.write_text(
        "\n".join(
            [
                f"class TestPanel extends HTMLElement {{}}",
                f"customElements.define('{element_name}', TestPanel);",
            ]
        ),
        encoding="utf-8",
    )


def test_validate_panels_accepts_valid_configuration(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_config(config_dir)
    _write_panel_asset(config_dir)

    errors = validate_panels(config_dir)

    assert errors == []


def test_validate_panels_rejects_missing_panel_asset(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_config(config_dir)

    errors = validate_panels(config_dir)

    assert len(errors) == 1
    assert "Panel module is missing" in errors[0]


def test_validate_panels_rejects_non_local_module_url(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_config(config_dir, module_url="https://example.com/panel.js")

    errors = validate_panels(config_dir)

    assert len(errors) == 1
    assert "must start with `/local/`" in errors[0]


def test_validate_panels_requires_matching_custom_element_name(tmp_path: Path) -> None:
    config_dir = tmp_path / "config"
    _write_config(config_dir)
    _write_panel_asset(config_dir, element_name="another-panel")

    errors = validate_panels(config_dir)

    assert len(errors) == 1
    assert "does not define matching custom element" in errors[0]
