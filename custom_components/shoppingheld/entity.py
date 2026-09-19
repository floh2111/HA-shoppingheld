"""Gemeinsame Basisklasse der ShoppingHeld-Entitäten."""

from __future__ import annotations

from datetime import date

from homeassistant.core import callback
from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo
from homeassistant.helpers.event import async_track_time_change
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


def app_weekday(day: date) -> int:
    """Wochentag im Schema der App (0 = Sonntag ... 6 = Samstag)."""
    return (day.weekday() + 1) % 7


class ShoppingHeldDayEntity(ShoppingHeldEntity):
    """Entität, die vom heutigen Datum abhängt: wird auch nach Mitternacht neu bewertet.

    Ohne das würde sich der Zustand erst mit der nächsten Abfrage beim Server ändern.
    """

    async def async_added_to_hass(self) -> None:
        await super().async_added_to_hass()
        self.async_on_remove(
            async_track_time_change(self.hass, self._async_new_day, hour=0, minute=0, second=5)
        )

    @callback
    def _async_new_day(self, _now: object) -> None:
        self.async_write_ha_state()
