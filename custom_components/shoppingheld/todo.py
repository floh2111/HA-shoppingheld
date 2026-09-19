"""Die ShoppingHeld-Einkaufsliste als To-do-Liste."""

from __future__ import annotations

from typing import Any

import voluptuous as vol

from homeassistant.components.todo import (
    TodoItem,
    TodoItemStatus,
    TodoListEntity,
    TodoListEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv, entity_platform
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ShoppingHeldError, format_summary, parse_item_text
from .const import CATEGORIES, CATEGORY_LABELS, DEFAULT_CATEGORY, DOMAIN
from .coordinator import ShoppingHeldConfigEntry, ShoppingHeldCoordinator
from .entity import ShoppingHeldEntity

PARALLEL_UPDATES = 1

ADD_ITEM_SCHEMA: dict[Any, Any] = {
    vol.Required("item"): cv.string,
    vol.Optional("amount"): vol.All(vol.Coerce(int), vol.Range(min=1, max=99)),
    vol.Optional("unit"): cv.string,
    vol.Optional("category"): vol.In(CATEGORIES),
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShoppingHeldConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    """To-do-Entität und Service shoppingheld.add_item einrichten."""
    async_add_entities([ShoppingHeldTodoList(entry.runtime_data)])
    platform = entity_platform.async_get_current_platform()
    platform.async_register_entity_service("add_item", ADD_ITEM_SCHEMA, "async_add_item_service")


class ShoppingHeldTodoList(ShoppingHeldEntity, TodoListEntity):
    """Einkaufsliste: offene Artikel = "zu erledigen", abgehakte = "erledigt"."""

    _attr_name = None  # Name des Geräts ("ShoppingHeld <Listenname>") wird verwendet
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
    )
    # Die Artikelliste steckt zusätzlich als Attribut für die Dashboard-Karte im State - nicht in
    # die Langzeit-Statistik/Datenbank schreiben (würde bei jeder Änderung ein neues Datenpaket sein).
    _unrecorded_attributes = frozenset({"items", "categories", "shopping_days"})

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_todo"

    # --- Lesen ---------------------------------------------------------------------------
    @property
    def todo_items(self) -> list[TodoItem]:
        return [
            TodoItem(
                uid=str(item["id"]),
                summary=format_summary(item),
                status=TodoItemStatus.COMPLETED if item.get("checked") else TodoItemStatus.NEEDS_ACTION,
            )
            for item in self.coordinator.data.items
        ]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rohdaten (mit Kategorie) für die ShoppingHeld-Dashboard-Karte."""
        data = self.coordinator.data
        days = [
            int(day) for day in str(data.settings.get("shopping_days") or "").split(",") if day.strip().isdigit()
        ]
        return {
            "source": DOMAIN,
            "list_name": data.settings.get("list_name") or "Einkaufsliste",
            "shopping_days": days,
            "categories": CATEGORY_LABELS,
            "items": [
                {
                    "id": item["id"],
                    "text": item.get("text", ""),
                    "amount": int(item.get("amount") or 1),
                    "unit": item.get("unit") or "",
                    "category": item.get("category") or DEFAULT_CATEGORY,
                    "checked": bool(item.get("checked")),
                    "summary": format_summary(item),
                }
                for item in data.items
            ],
        }

    # --- Schreiben -----------------------------------------------------------------------
    async def _add(self, text: str, amount: int, unit: str | None, category: str | None) -> None:
        text = text.strip()
        if not text:
            raise ServiceValidationError("Der Artikelname darf nicht leer sein.")
        client = self.coordinator.client
        try:
            category = category or await client.async_guess_category(text)
            await client.async_add_item(text, amount, category, unit)
        except ShoppingHeldError as err:
            raise HomeAssistantError(f"Artikel konnte nicht hinzugefügt werden: {err}") from err
        # Direkt neu laden statt async_request_refresh(): das ist bei HA 10 s entprellt, sodass bei
        # zwei schnellen Aktionen hintereinander die Liste bis zu 10 s veraltet angezeigt würde.
        await self.coordinator.async_refresh()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        amount, text = parse_item_text(item.summary or "")
        await self._add(text, amount, None, None)

    async def async_add_item_service(
        self,
        item: str,
        amount: int | None = None,
        unit: str | None = None,
        category: str | None = None,
    ) -> None:
        """Service shoppingheld.add_item (mit Menge, Einheit und Kategorie)."""
        if amount is None:
            amount, item = parse_item_text(item)
        await self._add(item, amount, unit, category)

    async def async_update_todo_item(self, item: TodoItem) -> None:
        current = next(
            (i for i in self.coordinator.data.items if str(i["id"]) == item.uid), None
        )
        if current is None:
            raise ServiceValidationError("Der Artikel existiert nicht mehr.")
        if item.summary is not None and item.summary != format_summary(current):
            raise ServiceValidationError(
                "Artikel umbenennen wird nicht unterstützt - bitte löschen und neu anlegen."
            )
        wanted_checked = item.status == TodoItemStatus.COMPLETED
        if wanted_checked != bool(current.get("checked")):
            try:
                await self.coordinator.client.async_toggle_item(current["id"])
            except ShoppingHeldError as err:
                raise HomeAssistantError(f"Artikel konnte nicht geändert werden: {err}") from err
            await self.coordinator.async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        try:
            for uid in uids:
                await self.coordinator.client.async_delete_item(int(uid))
        except ShoppingHeldError as err:
            raise HomeAssistantError(f"Artikel konnte nicht gelöscht werden: {err}") from err
        await self.coordinator.async_refresh()
