"""Binärsensoren: ist heute / morgen Einkaufstag?"""

from __future__ import annotations

from datetime import timedelta

from homeassistant.components.binary_sensor import BinarySensorEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.util import dt as dt_util

from .coordinator import ShoppingHeldConfigEntry, ShoppingHeldCoordinator
from .entity import ShoppingHeldDayEntity, app_weekday

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ShoppingHeldConfigEntry,
    async_add_entities: AddConfigEntryEntitiesCallback,
) -> None:
    coordinator = entry.runtime_data
    async_add_entities(
        [
            ShoppingDayBinarySensor(coordinator, "shopping_day_today", 0),
            ShoppingDayBinarySensor(coordinator, "shopping_day_tomorrow", 1),
        ]
    )


class ShoppingDayBinarySensor(ShoppingHeldDayEntity, BinarySensorEntity):
    """An, wenn heute (bzw. morgen) laut Einstellungen der Liste Einkaufstag ist."""

    _attr_icon = "mdi:cart-check"

    def __init__(self, coordinator: ShoppingHeldCoordinator, key: str, offset_days: int) -> None:
        super().__init__(coordinator)
        self._attr_translation_key = key
        self._attr_unique_id = f"{coordinator.config_entry.entry_id}_{key}"
        self._offset_days = offset_days

    @property
    def is_on(self) -> bool:
        day = dt_util.now().date() + timedelta(days=self._offset_days)
        return app_weekday(day) in self.coordinator.data.shopping_days
