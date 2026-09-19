"""Manifest-Konsistenz und Bereitstellung der Dashboard-Karte."""

from __future__ import annotations

import json
from pathlib import Path

from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant

from custom_components.shoppingheld.const import CARD_URL_PATH, VERSION

COMPONENT = Path(__file__).parent.parent / "custom_components" / "shoppingheld"


def test_version_matches_manifest() -> None:
    manifest = json.loads((COMPONENT / "manifest.json").read_text())
    assert manifest["version"] == VERSION


def test_frontend_and_brand_files_exist() -> None:
    assert (COMPONENT / "frontend" / "shoppingheld-card.js").is_file()
    assert (COMPONENT / "brand" / "icon.png").is_file()


def test_translations_have_same_keys() -> None:
    def keys(node, prefix=""):
        if isinstance(node, dict):
            for key, value in node.items():
                yield from keys(value, f"{prefix}.{key}")
        else:
            yield prefix

    de = set(keys(json.loads((COMPONENT / "translations" / "de.json").read_text())))
    en = set(keys(json.loads((COMPONENT / "translations" / "en.json").read_text())))
    assert de == en


async def test_setup_registers_card(
    hass: HomeAssistant, setup_integration: MockConfigEntry, mock_frontend
) -> None:
    assert setup_integration.state is ConfigEntryState.LOADED
    mock_frontend["add_extra_js_url"].assert_called_once_with(hass, f"{CARD_URL_PATH}?v={VERSION}")


async def test_unload(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    assert await hass.config_entries.async_unload(setup_integration.entry_id)
    assert setup_integration.state is ConfigEntryState.NOT_LOADED
