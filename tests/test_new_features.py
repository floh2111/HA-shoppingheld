"""Ereignisse, Binärsensoren, Buttons, set_amount, Basics/Vorschläge und einstellbares Intervall."""

from __future__ import annotations

from datetime import timedelta

import pytest
from freezegun.api import FrozenDateTimeFactory
from pytest_homeassistant_custom_component.common import (
    MockConfigEntry,
    async_capture_events,
    async_fire_time_changed,
)

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.helpers import entity_registry as er
from homeassistant.util import dt as dt_util

from custom_components.shoppingheld.const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    DOMAIN,
    EVENT_ITEM_ADDED,
    EVENT_LIST_COMPLETED,
)

from .conftest import BASE_URL, TOKEN, FakeServer

ENTITY = "todo.shoppingheld_einkaufsliste"
MINUTE = timedelta(seconds=60)


def _entity_id(hass: HomeAssistant, entry: MockConfigEntry, platform: str, suffix: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(platform, DOMAIN, f"{entry.entry_id}_{suffix}")
    assert entity_id is not None
    return entity_id


async def _poll(hass: HomeAssistant, freezer: FrozenDateTimeFactory, step: timedelta = MINUTE) -> None:
    freezer.tick(step)
    async_fire_time_changed(hass)
    await hass.async_block_till_done()


# --- Ereignisse ------------------------------------------------------------------------------
async def test_no_events_on_first_load(hass: HomeAssistant, config_entry: MockConfigEntry, server: FakeServer) -> None:
    from homeassistant.setup import async_setup_component

    added = async_capture_events(hass, EVENT_ITEM_ADDED)
    assert await async_setup_component(hass, "http", {})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert added == []


async def test_item_added_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer, freezer: FrozenDateTimeFactory
) -> None:
    added = async_capture_events(hass, EVENT_ITEM_ADDED)
    # jemand fügt in der App einen Artikel hinzu - die Integration merkt es beim nächsten Abruf
    server.items.append(
        {"id": 77, "text": "Eier", "amount": 10, "unit": "", "category": "milch", "checked": False}
    )
    await _poll(hass, freezer)
    assert len(added) == 1
    data = added[0].data
    assert data["text"] == "Eier" and data["amount"] == 10 and data["category"] == "milch"
    assert data["item_id"] == 77 and data["list_name"] == "Einkaufsliste"
    assert data["entry_id"] == setup_integration.entry_id

    # derselbe Stand noch einmal -> kein weiteres Ereignis
    await _poll(hass, freezer)
    assert len(added) == 1


async def test_item_added_event_for_own_add(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    added = async_capture_events(hass, EVENT_ITEM_ADDED)
    await hass.services.async_call("shoppingheld", "add_item", {"entity_id": ENTITY, "item": "Milch"}, blocking=True)
    assert [e.data["text"] for e in added] == ["Milch"]


async def test_list_completed_event(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer, freezer: FrozenDateTimeFactory
) -> None:
    completed = async_capture_events(hass, EVENT_LIST_COMPLETED)
    # zwei von drei offenen abgehakt -> noch nicht komplett
    for item in server.items:
        if item["id"] in (11, 13):
            item["checked"] = True
    await _poll(hass, freezer)
    assert completed == []
    # letzter offener Artikel abgehakt -> Ereignis
    for item in server.items:
        item["checked"] = True
    await _poll(hass, freezer)
    assert len(completed) == 1 and completed[0].data["total_items"] == 4
    # bleibt es abgehakt, kommt es nicht noch einmal
    await _poll(hass, freezer)
    assert len(completed) == 1


async def test_empty_list_is_not_completed(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer, freezer: FrozenDateTimeFactory
) -> None:
    completed = async_capture_events(hass, EVENT_LIST_COMPLETED)
    server.items.clear()
    await _poll(hass, freezer)
    assert completed == []


# --- Binärsensoren ---------------------------------------------------------------------------
async def test_shopping_day_binary_sensors(
    hass: HomeAssistant, setup_integration: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    today = _entity_id(hass, setup_integration, "binary_sensor", "shopping_day_today")
    tomorrow = _entity_id(hass, setup_integration, "binary_sensor", "shopping_day_tomorrow")

    # Einkaufstage "5,6" = Freitag + Samstag. Donnerstag, 24.09.2026
    # (Zeitpunkte liegen nach "jetzt", sonst löst der Test-Helfer den geplanten Abruf nicht aus)
    freezer.move_to("2026-09-24 10:00:00+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + MINUTE)
    await hass.async_block_till_done()
    assert hass.states.get(today).state == "off"
    assert hass.states.get(tomorrow).state == "on"  # morgen ist Freitag

    # Freitag
    freezer.move_to("2026-09-25 10:00:00+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + 2 * MINUTE)
    await hass.async_block_till_done()
    assert hass.states.get(today).state == "on"
    assert hass.states.get(tomorrow).state == "on"  # Samstag

    # Sonntag
    freezer.move_to("2026-09-27 10:00:00+02:00")
    async_fire_time_changed(hass, dt_util.utcnow() + 3 * MINUTE)
    await hass.async_block_till_done()
    assert hass.states.get(today).state == "off"
    assert hass.states.get(tomorrow).state == "off"


async def test_binary_sensor_flips_at_midnight_without_server_poll(
    hass: HomeAssistant, setup_integration: MockConfigEntry, aioclient_mock, freezer: FrozenDateTimeFactory
) -> None:
    await hass.config.async_set_time_zone("Europe/Berlin")
    today = _entity_id(hass, setup_integration, "binary_sensor", "shopping_day_today")
    freezer.move_to("2026-09-24 23:59:00+02:00")  # Donnerstag
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(today).state == "off"

    # Regelmäßige Abfrage abschalten: der Wechsel darf nur vom Mitternachts-Timer kommen
    coordinator = setup_integration.runtime_data
    coordinator.update_interval = None
    coordinator._unschedule_refresh()
    requests_before = aioclient_mock.call_count
    freezer.move_to("2026-09-25 00:00:10+02:00")  # kurz nach Mitternacht, Freitag
    async_fire_time_changed(hass, dt_util.utcnow())
    await hass.async_block_till_done()
    assert hass.states.get(today).state == "on"
    assert aioclient_mock.call_count == requests_before  # kam vom Mitternachts-Timer, nicht vom Server


# --- Buttons ---------------------------------------------------------------------------------
async def test_add_basics_button(hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer) -> None:
    entity_id = _entity_id(hass, setup_integration, "button", "add_basics")
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    assert {"action": "add_basics"} in server.actions
    assert hass.states.get(ENTITY).state == "5"  # 3 offene + 2 Basics


async def test_clear_checked_button(hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer) -> None:
    entity_id = _entity_id(hass, setup_integration, "button", "clear_checked")
    await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)
    assert {"action": "clear_checked"} in server.actions
    assert [i["id"] for i in server.items] == [11, 13, 14]
    assert hass.states.get(ENTITY).state == "3"


async def test_button_error_is_reported(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    from homeassistant.exceptions import HomeAssistantError

    server.status = 500
    entity_id = _entity_id(hass, setup_integration, "button", "clear_checked")
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call("button", "press", {"entity_id": entity_id}, blocking=True)


# --- set_amount ------------------------------------------------------------------------------
async def test_set_amount_by_id(hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer) -> None:
    await hass.services.async_call(
        "shoppingheld", "set_amount", {"entity_id": ENTITY, "item": "11", "amount": 5}, blocking=True
    )
    assert {"action": "set_amount", "id": 11, "amount": 5} in server.actions
    items = hass.states.get(ENTITY).attributes["items"]
    assert next(i for i in items if i["id"] == 11)["amount"] == 5


async def test_set_amount_by_name_prefers_open_item(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    server.items.append({"id": 90, "text": "apfel", "amount": 1, "unit": "", "category": "gemuese", "checked": True})
    await hass.services.async_call(
        "shoppingheld", "set_amount", {"entity_id": ENTITY, "item": "APFEL", "amount": 2}, blocking=True
    )
    assert {"action": "set_amount", "id": 11, "amount": 2} in server.actions


async def test_set_amount_unknown_item(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "shoppingheld", "set_amount", {"entity_id": ENTITY, "item": "Ufo", "amount": 2}, blocking=True
        )


# --- Basics und Vorschläge (für die Karte) -----------------------------------------------------
async def test_basics_and_suggestions_attributes(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    attrs = hass.states.get(ENTITY).attributes
    # Anzeigename = Singular, sonst der Wörterbuch-Eintrag
    assert attrs["basics"] == [
        {"text": "Milch", "category": "milch"},
        {"text": "eier", "category": "milch"},
    ]
    assert attrs["suggestions"] == [{"text": "Kaffee"}]


async def test_missing_permission_for_basics_does_not_break_list(
    hass: HomeAssistant, config_entry: MockConfigEntry, server: FakeServer
) -> None:
    from homeassistant.config_entries import ConfigEntryState
    from homeassistant.setup import async_setup_component

    server.optional_failing = True  # z. B. Server noch ohne die neuen Token-Rechte
    assert await async_setup_component(hass, "http", {})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    assert config_entry.state is ConfigEntryState.LOADED
    attrs = hass.states.get(ENTITY).attributes
    assert attrs["basics"] == [] and attrs["suggestions"] == []
    assert hass.states.get(ENTITY).state == "3"


async def test_basics_are_refreshed_rarely(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer, freezer: FrozenDateTimeFactory
) -> None:
    server.actions.clear()
    for _ in range(3):
        await _poll(hass, freezer)
    assert not any(a["action"] in ("get_user_basics", "get_basics_suggestions") for a in server.actions)
    await _poll(hass, freezer, timedelta(minutes=31))
    assert sum(a["action"] == "get_user_basics" for a in server.actions) == 1


# --- Abfrageintervall --------------------------------------------------------------------------
async def test_options_flow_sets_interval_and_reloads(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    coordinator = setup_integration.runtime_data
    assert coordinator.update_interval == timedelta(seconds=60)

    result = await hass.config_entries.options.async_init(setup_integration.entry_id)
    assert result["type"] == "form" and result["step_id"] == "init"
    result = await hass.config_entries.options.async_configure(result["flow_id"], {CONF_SCAN_INTERVAL: 120})
    assert result["type"] == "create_entry"
    await hass.async_block_till_done()
    assert setup_integration.options[CONF_SCAN_INTERVAL] == 120
    assert setup_integration.runtime_data.update_interval == timedelta(seconds=120)


@pytest.mark.parametrize(
    ("stored", "expected"), [(5, 30), (9999, 300), ("abc", 60), (45, 45)]
)
async def test_interval_is_clamped(
    hass: HomeAssistant, server: FakeServer, stored: object, expected: int
) -> None:
    from homeassistant.setup import async_setup_component

    entry = MockConfigEntry(
        domain=DOMAIN,
        unique_id="shoppingheld.example.org/florian",
        data={CONF_URL: BASE_URL, CONF_TOKEN: TOKEN},
        options={CONF_SCAN_INTERVAL: stored},
    )
    assert await async_setup_component(hass, "http", {})
    entry.add_to_hass(hass)
    await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert entry.runtime_data.update_interval == timedelta(seconds=expected)
