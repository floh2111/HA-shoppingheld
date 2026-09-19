"""ShoppingHeld: Einkaufsliste als To-do-Liste, Sensoren und Dashboard-Karte."""

from __future__ import annotations

from pathlib import Path

from homeassistant.components.frontend import add_extra_js_url
from homeassistant.components.http import StaticPathConfig
from homeassistant.const import Platform
from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.typing import ConfigType

from .api import ShoppingHeldClient
from .const import CARD_URL_PATH, CONF_TOKEN, CONF_URL, DOMAIN, VERSION
from .coordinator import ShoppingHeldConfigEntry, ShoppingHeldCoordinator

PLATFORMS: list[Platform] = [Platform.TODO, Platform.SENSOR]

FRONTEND_DIR = Path(__file__).parent / "frontend"


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Dashboard-Karte "custom:shoppingheld-card" bereitstellen (ohne manuelles Hinzufügen einer Ressource)."""
    await hass.http.async_register_static_paths(
        [StaticPathConfig(CARD_URL_PATH, str(FRONTEND_DIR / "shoppingheld-card.js"), cache_headers=False)]
    )
    # ?v=... damit Browser/App nach einem Update die neue Version der Karte laden
    add_extra_js_url(hass, f"{CARD_URL_PATH}?v={VERSION}")
    return True


async def async_setup_entry(hass: HomeAssistant, entry: ShoppingHeldConfigEntry) -> bool:
    client = ShoppingHeldClient(
        async_get_clientsession(hass), entry.data[CONF_URL], entry.data[CONF_TOKEN]
    )
    coordinator = ShoppingHeldCoordinator(hass, entry, client)
    await coordinator.async_config_entry_first_refresh()
    entry.runtime_data = coordinator
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: ShoppingHeldConfigEntry) -> bool:
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
