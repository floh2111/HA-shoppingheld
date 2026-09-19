"""Schaltflächen: Basics auf die Liste legen, abgehakte Artikel löschen."""

from __future__ import annotations

from homeassistant.components.button import ButtonEntity
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .api import ShoppingHeldError
from .coordinator import ShoppingHeldConfigEntry, ShoppingHeldCoordinator
from .entity import ShoppingHeldEntity

PARALLEL_UPDATES = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShoppingHeldConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([AddBasicsButton(coordinator), ClearCheckedButton(coordinator)])


class _ShoppingHeldButton(ShoppingHeldEntity, ButtonEntity):
    def __init__(self, coordinator: ShoppingHeldCoordinator, key: str) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"


class AddBasicsButton(_ShoppingHeldButton):
    """Legt alle Basics (regelmäßig gekaufte Artikel) auf die Liste."""

    _attr_icon = "mdi:playlist-plus"

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator, "add_basics")

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.async_add_basics()
        except ShoppingHeldError as err:
            raise HomeAssistantError(f"Basics konnten nicht hinzugefügt werden: {err}") from err
        await self.coordinator.async_refresh()


class ClearCheckedButton(_ShoppingHeldButton):
    """Löscht alle abgehakten Artikel von der Liste."""

    _attr_icon = "mdi:cart-remove"

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator, "clear_checked")

    async def async_press(self) -> None:
        try:
            await self.coordinator.client.async_clear_checked()
        except ShoppingHeldError as err:
            raise HomeAssistantError(f"Abgehakte konnten nicht gelöscht werden: {err}") from err
        await self.coordinator.async_refresh()
