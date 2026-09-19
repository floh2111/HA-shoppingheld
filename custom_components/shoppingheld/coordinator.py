"""Holt Einkaufsliste und Einstellungen regelmäßig vom ShoppingHeld-Server."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from typing import Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed
from homeassistant.util import dt as dt_util

from .api import (
    ShoppingHeldAuthError,
    ShoppingHeldClient,
    ShoppingHeldConnectionError,
    ShoppingHeldError,
)
from .const import DOMAIN, SCAN_INTERVAL, SETTINGS_REFRESH_INTERVAL

_LOGGER = logging.getLogger(__name__)

type ShoppingHeldConfigEntry = ConfigEntry[ShoppingHeldCoordinator]


@dataclass
class ShoppingHeldData:
    """Aktueller Stand: Artikel (schon in der Reihenfolge des Servers) und Listen-Einstellungen."""

    items: list[dict[str, Any]]
    settings: dict[str, Any]


class ShoppingHeldCoordinator(DataUpdateCoordinator[ShoppingHeldData]):
    """Fragt die Liste jede Minute ab, die Einstellungen nur gelegentlich."""

    config_entry: ShoppingHeldConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ShoppingHeldConfigEntry, client: ShoppingHeldClient
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=SCAN_INTERVAL
        )
        self.client = client
        self._settings: dict[str, Any] | None = None
        self._settings_fetched: datetime | None = None

    async def _async_update_data(self) -> ShoppingHeldData:
        try:
            items = await self.client.async_get_items()
            now = dt_util.utcnow()
            if (
                self._settings is None
                or self._settings_fetched is None
                or now - self._settings_fetched > SETTINGS_REFRESH_INTERVAL
            ):
                try:
                    self._settings = await self.client.async_get_settings()
                    self._settings_fetched = now
                except ShoppingHeldAuthError:
                    raise
                except ShoppingHeldError:
                    if self._settings is None:
                        raise
                    _LOGGER.debug("Einstellungen konnten nicht aktualisiert werden, nutze alte")
        except ShoppingHeldAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ShoppingHeldConnectionError as err:
            raise UpdateFailed(f"Server nicht erreichbar: {err}") from err
        except ShoppingHeldError as err:
            raise UpdateFailed(str(err)) from err
        return ShoppingHeldData(items=items, settings=self._settings or {})
