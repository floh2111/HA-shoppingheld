"""Sensoren: offene Artikel und nächster Einkaufstag."""

from __future__ import annotations

from datetime import date

from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.shoppingheld.const import DOMAIN, SCAN_INTERVAL

from .conftest import FakeServer


def _entity_id(hass: HomeAssistant, entry: MockConfigEntry, suffix: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id("sensor", DOMAIN, f"{entry.entry_id}_{suffix}")
    assert entity_id is not None
    return entity_id


async def test_open_items_sensor(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    state = hass.states.get(_entity_id(hass, setup_integration, "open_items"))
    assert state.state == "3"
    assert state.attributes["checked_items"] == 1
    assert state.attributes["total_items"] == 4


async def test_next_shopping_day(
    hass: HomeAssistant, setup_integration: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    entity_id = _entity_id(hass, setup_integration, "next_shopping_day")

    # Einkaufstage "5,6" = Freitag + Samstag. Samstag, 19.09.2026: heute zählt mit
    freezer.move_to("2026-09-19 10:00:00+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "2026-09-19"
    assert state.attributes["weekday"] == "Samstag"
    assert state.attributes["is_today"] is True and state.attributes["days_until"] == 0

    # Sonntag, 20.09.2026: nächster ist Freitag, 25.09.
    freezer.move_to("2026-09-20 10:00:00+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + 2 * SCAN_INTERVAL)
    await hass.async_block_till_done()
    state = hass.states.get(entity_id)
    assert state.state == "2026-09-25"
    assert state.attributes["weekday"] == "Freitag"
    assert state.attributes["days_until"] == 5 and state.attributes["is_today"] is False
    assert date.fromisoformat(state.state).weekday() == 4


async def test_no_shopping_days_gives_unknown(
    hass: HomeAssistant, config_entry: MockConfigEntry, server: FakeServer
) -> None:
    from homeassistant.setup import async_setup_component

    server.settings = {**server.settings, "shopping_days": ""}
    assert await async_setup_component(hass, "http", {})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert hass.states.get(_entity_id(hass, config_entry, "next_shopping_day")).state == "unknown"
