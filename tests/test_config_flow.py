"""Einrichtung und erneute Anmeldung."""

from __future__ import annotations

import aiohttp
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
from homeassistant.setup import async_setup_component

from custom_components.shoppingheld.const import CONF_TOKEN, CONF_URL, DOMAIN

from .conftest import BASE_URL, TOKEN, FakeServer


async def _start(hass: HomeAssistant):
    assert await async_setup_component(hass, "http", {})
    return await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})


async def test_user_flow_success(hass: HomeAssistant, server: FakeServer) -> None:
    result = await _start(hass)
    assert result["type"] is FlowResultType.FORM

    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: "shoppingheld.example.org/", CONF_TOKEN: f" {TOKEN} "}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "ShoppingHeld (florian)"
    assert result["data"] == {CONF_URL: BASE_URL, CONF_TOKEN: TOKEN}  # URL normalisiert, Token getrimmt
    assert result["result"].unique_id == "shoppingheld.example.org/florian"


async def test_user_flow_invalid_auth(hass: HomeAssistant, server: FakeServer) -> None:
    server.status = 401
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_URL: BASE_URL, CONF_TOKEN: "shh_falsch"}
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "invalid_auth"}

    # Nach dem Korrigieren klappt es
    server.status = 200
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: BASE_URL, CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.CREATE_ENTRY


async def test_user_flow_cannot_connect(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.post(f"{BASE_URL}/backend", exc=aiohttp.ClientError)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: BASE_URL, CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {"base": "cannot_connect"}


async def test_user_flow_invalid_url(hass: HomeAssistant) -> None:
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: "ftp://x", CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_URL: "invalid_url"}


async def test_user_flow_already_configured(
    hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry
) -> None:
    config_entry.add_to_hass(hass)
    result = await _start(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_URL: BASE_URL, CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "already_configured"


async def test_reauth_flow(hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry) -> None:
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    assert result["type"] is FlowResultType.FORM
    assert result["step_id"] == "reauth_confirm"

    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "reauth_successful"
    assert config_entry.data[CONF_TOKEN] == TOKEN

    await hass.async_block_till_done()
    await hass.config_entries.async_unload(config_entry.entry_id)  # Timer des neu geladenen Eintrags beenden


async def test_reauth_wrong_account(hass: HomeAssistant, server: FakeServer, config_entry: MockConfigEntry) -> None:
    server.settings = {**server.settings, "username": "deborah"}
    config_entry.add_to_hass(hass)
    result = await config_entry.start_reauth_flow(hass)
    result = await hass.config_entries.flow.async_configure(result["flow_id"], {CONF_TOKEN: TOKEN})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "wrong_account"
