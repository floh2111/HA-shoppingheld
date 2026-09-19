"""Gemeinsame Test-Helfer: ein kleiner Fake-ShoppingHeld-Server auf Basis von aioclient_mock."""

from __future__ import annotations

from copy import deepcopy
from typing import Any
from unittest.mock import patch

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import (
    AiohttpClientMocker,
    AiohttpClientMockResponse,
)

from homeassistant.core import HomeAssistant
from homeassistant.setup import async_setup_component

from custom_components.shoppingheld.const import CONF_TOKEN, CONF_URL, DOMAIN

BASE_URL = "https://shoppingheld.example.org"
TOKEN = "shh_test_token"

DEFAULT_ITEMS = [
    {"id": 11, "text": "Apfel", "amount": 3, "unit": "", "category": "gemuese", "checked": False},
    {"id": 12, "text": "Bananen", "amount": 1, "unit": "", "category": "gemuese", "checked": True},
    {"id": 13, "text": "Butter", "amount": 500, "unit": "g", "category": "milchprodukte", "checked": False},
    {"id": 14, "text": "Brot", "amount": 1, "unit": "", "category": "brot", "checked": False},
]
DEFAULT_SETTINGS = {
    "username": "florian",
    "list_name": "Einkaufsliste",
    "shopping_days": "5,6",
    "household_members": ["florian"],
}


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations: None) -> None:
    """Lädt Integrationen aus custom_components/."""


@pytest.fixture(autouse=True)
def mock_frontend():
    """Frontend/HTTP werden nicht wirklich gestartet - wir prüfen nur die Registrierung der Karte."""
    with (
        patch("homeassistant.components.frontend.async_setup", return_value=True),
        patch("custom_components.shoppingheld.add_extra_js_url") as add_js,
        patch(
            "homeassistant.components.http.HomeAssistantHTTP.async_register_static_paths",
            create=True,
        ) as register,
    ):
        yield {"add_extra_js_url": add_js, "register_static_paths": register}


class FakeServer:
    """Minimaler Ersatz für /backend: hält Artikel und Einstellungen und protokolliert Aktionen."""

    def __init__(self, items: list[dict[str, Any]], settings: dict[str, Any]) -> None:
        self.items = deepcopy(items)
        self.settings = deepcopy(settings)
        self.actions: list[dict[str, Any]] = []
        self.next_id = 100
        self.status = 200  # z.B. 401 zum Testen widerrufener Token
        self.guess = {"milch": "milch", "eier": "milch"}

    async def handle_get(self, method: str, url: Any, data: Any):
        if self.status != 200:
            return AiohttpClientMockResponse(method, url, status=self.status, json={"error": "Nicht angemeldet"})
        return AiohttpClientMockResponse(method, url, json=deepcopy(self.items))

    async def handle_post(self, method: str, url: Any, data: Any):
        if self.status != 200:
            return AiohttpClientMockResponse(method, url, status=self.status, json={"error": "Nicht angemeldet"})
        self.actions.append(data)
        action = data["action"]
        if action == "get_settings":
            return AiohttpClientMockResponse(method, url, json=deepcopy(self.settings))
        if action == "guess_category":
            category = self.guess.get(data["text"].lower(), "sonstiges")
            return AiohttpClientMockResponse(method, url, json={"category": category})
        if action == "add":
            self.next_id += 1
            self.items.append(
                {
                    "id": self.next_id,
                    "text": data["text"],
                    "amount": data.get("amount", 1),
                    "unit": data.get("unit", ""),
                    "category": data.get("category", "sonstiges"),
                    "checked": False,
                }
            )
            return AiohttpClientMockResponse(method, url, json={"success": True, "id": self.next_id})
        if action == "toggle":
            for item in self.items:
                if item["id"] == data["id"]:
                    item["checked"] = not item["checked"]
            return AiohttpClientMockResponse(method, url, json={"success": True})
        if action == "delete":
            self.items = [i for i in self.items if i["id"] != data["id"]]
            return AiohttpClientMockResponse(method, url, json={"success": True})
        return AiohttpClientMockResponse(method, url, status=400, json={"error": f"Unbekannte Aktion: {action}"})


@pytest.fixture
def server(aioclient_mock: AiohttpClientMocker) -> FakeServer:
    fake = FakeServer(DEFAULT_ITEMS, DEFAULT_SETTINGS)
    aioclient_mock.get(f"{BASE_URL}/backend", side_effect=fake.handle_get)
    aioclient_mock.post(f"{BASE_URL}/backend", side_effect=fake.handle_post)
    return fake


@pytest.fixture
def config_entry() -> MockConfigEntry:
    return MockConfigEntry(
        domain=DOMAIN,
        title="ShoppingHeld (florian)",
        unique_id="shoppingheld.example.org/florian",
        data={CONF_URL: BASE_URL, CONF_TOKEN: TOKEN},
    )


@pytest.fixture
async def setup_integration(hass: HomeAssistant, config_entry: MockConfigEntry, server: FakeServer):
    """Richtet den Config-Entry gegen den Fake-Server ein."""
    assert await async_setup_component(hass, "http", {})
    config_entry.add_to_hass(hass)
    await hass.config_entries.async_setup(config_entry.entry_id)
    await hass.async_block_till_done()
    return config_entry
