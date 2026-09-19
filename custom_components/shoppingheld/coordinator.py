"""Holt Einkaufsliste und Einstellungen regelmäßig vom ShoppingHeld-Server."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timedelta
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
from .const import (
    CONF_SCAN_INTERVAL,
    DEFAULT_SCAN_INTERVAL,
    DOMAIN,
    EVENT_ITEM_ADDED,
    EVENT_LIST_COMPLETED,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
    SETTINGS_REFRESH_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)

type ShoppingHeldConfigEntry = ConfigEntry[ShoppingHeldCoordinator]


@dataclass
class ShoppingHeldData:
    """Aktueller Stand: Artikel (schon in der Reihenfolge des Servers) und Listen-Einstellungen."""

    items: list[dict[str, Any]]
    settings: dict[str, Any]
    basics: list[dict[str, str]] = field(default_factory=list)
    suggestions: list[dict[str, str]] = field(default_factory=list)

    @property
    def shopping_days(self) -> set[int]:
        """Einkaufstage im Schema der App (0 = Sonntag ... 6 = Samstag)."""
        raw = str(self.settings.get("shopping_days") or "")
        return {int(day) for day in raw.split(",") if day.strip().isdigit()}


def scan_interval(entry: ConfigEntry) -> timedelta:
    """Abfrageintervall aus den Optionen (auf den erlaubten Bereich begrenzt)."""
    seconds = entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
    try:
        seconds = int(seconds)
    except (TypeError, ValueError):
        seconds = DEFAULT_SCAN_INTERVAL
    return timedelta(seconds=min(MAX_SCAN_INTERVAL, max(MIN_SCAN_INTERVAL, seconds)))


class ShoppingHeldCoordinator(DataUpdateCoordinator[ShoppingHeldData]):
    """Fragt die Liste regelmäßig ab (Standard: jede Minute), Einstellungen/Basics nur gelegentlich."""

    config_entry: ShoppingHeldConfigEntry

    def __init__(
        self, hass: HomeAssistant, entry: ShoppingHeldConfigEntry, client: ShoppingHeldClient
    ) -> None:
        super().__init__(
            hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=scan_interval(entry)
        )
        self.client = client
        self._settings: dict[str, Any] | None = None
        self._settings_fetched: datetime | None = None
        self._basics: list[dict[str, str]] = []
        self._suggestions: list[dict[str, str]] = []
        # Für die Ereignisse: was war beim letzten Abruf auf der Liste? (None = noch nie abgerufen)
        self._known_ids: set[int] | None = None
        self._had_open_items = False

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
                await self._async_refresh_basics()
        except ShoppingHeldAuthError as err:
            raise ConfigEntryAuthFailed(str(err)) from err
        except ShoppingHeldConnectionError as err:
            raise UpdateFailed(f"Server nicht erreichbar: {err}") from err
        except ShoppingHeldError as err:
            raise UpdateFailed(str(err)) from err
        self._fire_events(items)
        return ShoppingHeldData(
            items=items,
            settings=self._settings or {},
            basics=self._basics,
            suggestions=self._suggestions,
        )

    async def _async_refresh_basics(self) -> None:
        """Basics und Vorschläge (für die Karte) - optional: ein Fehler stört die Liste nicht."""
        for name, fetch in (
            ("_basics", self.client.async_get_basics),
            ("_suggestions", self.client.async_get_suggestions),
        ):
            try:
                setattr(self, name, await fetch())
            except ShoppingHeldAuthError:
                raise
            except ShoppingHeldError as err:
                _LOGGER.debug("%s konnten nicht geladen werden: %s", name.strip("_"), err)

    def _fire_events(self, items: list[dict[str, Any]]) -> None:
        """Ereignisse für Automationen: neuer Artikel auf der Liste, Liste komplett abgehakt."""
        ids = {item["id"] for item in items}
        has_open = any(not item.get("checked") for item in items)
        if self._known_ids is not None:  # beim allerersten Abruf gibt es nichts zu vergleichen
            settings = self._settings or {}
            base = {
                "entry_id": self.config_entry.entry_id,
                "list_name": settings.get("list_name") or "Einkaufsliste",
            }
            for item in items:
                if item["id"] not in self._known_ids:
                    self.hass.bus.async_fire(
                        EVENT_ITEM_ADDED,
                        {
                            **base,
                            "item_id": item["id"],
                            "text": item.get("text", ""),
                            "amount": int(item.get("amount") or 1),
                            "unit": item.get("unit") or "",
                            "category": item.get("category") or "",
                        },
                    )
            if self._had_open_items and not has_open and items:
                self.hass.bus.async_fire(EVENT_LIST_COMPLETED, {**base, "total_items": len(items)})
        self._known_ids = ids
        self._had_open_items = has_open
