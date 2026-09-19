"""Gemeinsame Basisklasse der ShoppingHeld-Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import ShoppingHeldCoordinator


class ShoppingHeldEntity(CoordinatorEntity[ShoppingHeldCoordinator]):
    """Alle Entitäten einer Liste hängen an demselben Gerät."""

    _attr_has_entity_name = True

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator)
        entry = coordinator.config_entry
        list_name = coordinator.data.settings.get("list_name") or "Einkaufsliste"
        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, entry.entry_id)},
            name=f"ShoppingHeld {list_name}",
            manufacturer="ShoppingHeld",
            entry_type=DeviceEntryType.SERVICE,
        )
