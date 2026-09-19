"""Sensoren: Anzahl offener Artikel und nächster Einkaufstag."""

from __future__ import annotations

from datetime import date, timedelta
from typing import Any

from homeassistant.components.sensor import SensorDeviceClass, SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .const import WEEKDAY_NAMES_DE
from .coordinator import ShoppingHeldConfigEntry, ShoppingHeldCoordinator
from .entity import ShoppingHeldEntity

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShoppingHeldConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities([OpenItemsSensor(coordinator), NextShoppingDaySensor(coordinator)])


class OpenItemsSensor(ShoppingHeldEntity, SensorEntity):
    """Wie viele Artikel stehen noch offen auf der Liste?"""

    _attr_translation_key = "open_items"
    _attr_icon = "mdi:cart-outline"
    _attr_state_class = SensorStateClass.MEASUREMENT

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_open_items"

    @property
    def native_value(self) -> int:
        return sum(1 for item in self.coordinator.data.items if not item.get("checked"))

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        items = self.coordinator.data.items
        return {
            "checked_items": sum(1 for item in items if item.get("checked")),
            "total_items": len(items),
        }


def _app_weekday(day: date) -> int:
    """Wochentag im Schema der App (0 = Sonntag ... 6 = Samstag)."""
    return (day.weekday() + 1) % 7


class NextShoppingDaySensor(ShoppingHeldEntity, SensorEntity):
    """Nächster Einkaufstag laut Einstellungen der Liste (heute zählt mit)."""

    _attr_translation_key = "next_shopping_day"
    _attr_icon = "mdi:calendar-check"
    _attr_device_class = SensorDeviceClass.DATE

    def __init__(self, coordinator: ShoppingHeldCoordinator) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_next_shopping_day"

    def _shopping_days(self) -> set[int]:
        raw = str(self.coordinator.data.settings.get("shopping_days") or "")
        return {int(day) for day in raw.split(",") if day.strip().isdigit()}

    def _next_date(self) -> date | None:
        days = self._shopping_days()
        if not days:
            return None
        today = dt_util.now().date()
        for offset in range(8):
            candidate = today + timedelta(days=offset)
            if _app_weekday(candidate) in days:
                return candidate
        return None

    @property
    def native_value(self) -> date | None:
        return self._next_date()

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        next_date = self._next_date()
        if next_date is None:
            return {}
        today = dt_util.now().date()
        return {
            "weekday": WEEKDAY_NAMES_DE[_app_weekday(next_date)],
            "days_until": (next_date - today).days,
            "is_today": next_date == today,
        }
