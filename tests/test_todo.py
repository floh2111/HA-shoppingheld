"""To-do-Liste, Service add_item, Fehlerbehandlung."""

from __future__ import annotations

from datetime import timedelta

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.util import dt as dt_util

from custom_components.shoppingheld.const import DEFAULT_SCAN_INTERVAL, DOMAIN

SCAN_INTERVAL = timedelta(seconds=DEFAULT_SCAN_INTERVAL)

from .conftest import TOKEN, FakeServer

ENTITY = "todo.shoppingheld_einkaufsliste"


async def _get_items(hass: HomeAssistant) -> list[dict]:
    response = await hass.services.async_call(
        "todo", "get_items", {"entity_id": ENTITY}, blocking=True, return_response=True
    )
    return response[ENTITY]["items"]


async def test_requests_carry_bearer_token(
    hass: HomeAssistant, setup_integration: MockConfigEntry, aioclient_mock
) -> None:
    assert aioclient_mock.mock_calls
    for _method, _url, _data, headers in aioclient_mock.mock_calls:
        assert headers["Authorization"] == f"Bearer {TOKEN}"


async def test_todo_items(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    state = hass.states.get(ENTITY)
    assert state is not None
    assert state.state == "3"  # drei offene Artikel
    assert state.attributes["source"] == DOMAIN
    assert state.attributes["shopping_days"] == [5, 6]
    assert state.attributes["categories"]["milch"] == "Kühltheke"

    items = {item["uid"]: item for item in await _get_items(hass)}
    assert items["11"]["summary"] == "3× Apfel" and items["11"]["status"] == "needs_action"
    assert items["12"]["summary"] == "Bananen" and items["12"]["status"] == "completed"
    assert items["13"]["summary"] == "500 g Butter"

    # Rohdaten für die Karte enthalten die Kategorie
    card_items = {i["id"]: i for i in state.attributes["items"]}
    assert card_items[13]["category"] == "milchprodukte" and card_items[13]["unit"] == "g"


async def test_add_via_todo_service_guesses_category_and_amount(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    await hass.services.async_call("todo", "add_item", {"entity_id": ENTITY, "item": "2 Milch"}, blocking=True)

    assert {"action": "guess_category", "text": "Milch"} in server.actions
    assert {"action": "add", "text": "Milch", "amount": 2, "category": "milch"} in server.actions
    assert hass.states.get(ENTITY).state == "4"  # sofort neu geladen


async def test_add_item_service_with_fields(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    await hass.services.async_call(
        DOMAIN,
        "add_item",
        {"entity_id": ENTITY, "item": "Spülmittel", "amount": 3, "unit": "Flasche", "category": "haushalt"},
        blocking=True,
    )
    # explizite Kategorie: keine Server-Erkennung nötig
    assert not any(a["action"] == "guess_category" for a in server.actions)
    assert {"action": "add", "text": "Spülmittel", "amount": 3, "category": "haushalt", "unit": "Flasche"} in server.actions


async def test_add_item_service_parses_amount_from_text(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    await hass.services.async_call(DOMAIN, "add_item", {"entity_id": ENTITY, "item": "6x Eier"}, blocking=True)
    assert {"action": "add", "text": "Eier", "amount": 6, "category": "milch"} in server.actions


async def test_add_item_empty_name_rejected(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(DOMAIN, "add_item", {"entity_id": ENTITY, "item": "   "}, blocking=True)


async def test_complete_and_reopen(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    await hass.services.async_call(
        "todo", "update_item", {"entity_id": ENTITY, "item": "11", "status": "completed"}, blocking=True
    )
    assert {"action": "toggle", "id": 11} in server.actions
    assert hass.states.get(ENTITY).state == "2"

    # Schon erledigt -> erneutes "completed" darf NICHT nochmal umschalten (toggle flippt sonst zurück)
    server.actions.clear()
    await hass.services.async_call(
        "todo", "update_item", {"entity_id": ENTITY, "item": "11", "status": "completed"}, blocking=True
    )
    assert not any(a["action"] == "toggle" for a in server.actions)

    await hass.services.async_call(
        "todo", "update_item", {"entity_id": ENTITY, "item": "11", "status": "needs_action"}, blocking=True
    )
    assert hass.states.get(ENTITY).state == "3"


async def test_rename_not_supported(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "todo", "update_item", {"entity_id": ENTITY, "item": "11", "rename": "Birne"}, blocking=True
        )


async def test_delete(hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer) -> None:
    await hass.services.async_call("todo", "remove_item", {"entity_id": ENTITY, "item": ["11", "14"]}, blocking=True)
    assert {"action": "delete", "id": 11} in server.actions and {"action": "delete", "id": 14} in server.actions
    assert [i["uid"] for i in await _get_items(hass)] == ["12", "13"]


async def test_server_down_makes_entity_unavailable(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    server.status = 500
    async_fire_time_changed(hass, dt_util.utcnow() + SCAN_INTERVAL)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == STATE_UNAVAILABLE

    server.status = 200
    async_fire_time_changed(hass, dt_util.utcnow() + 2 * SCAN_INTERVAL)
    await hass.async_block_till_done()
    assert hass.states.get(ENTITY).state == "3"


async def test_revoked_token_starts_reauth(hass: HomeAssistant, config_entry: MockConfigEntry, server: FakeServer) -> None:
    from homeassistant.setup import async_setup_component

    assert await async_setup_component(hass, "http", {})
    server.status = 401
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()

    assert config_entry.state is ConfigEntryState.SETUP_ERROR
    flows = hass.config_entries.flow.async_progress_by_handler(DOMAIN)
    assert any(flow["context"]["source"] == "reauth" for flow in flows)
