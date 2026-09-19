"""Einrichtung der Integration: Server-Adresse + persönlicher Zugangs-Token."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any
from urllib.parse import urlparse

import voluptuous as vol

from homeassistant.config_entries import (
    ConfigEntry,
    ConfigFlow,
    ConfigFlowResult,
    OptionsFlowWithReload,
)
from homeassistant.core import callback
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.selector import NumberSelector, NumberSelectorConfig, NumberSelectorMode

from .api import (
    ShoppingHeldAuthError,
    ShoppingHeldClient,
    ShoppingHeldConnectionError,
    ShoppingHeldError,
    normalize_url,
)
from .const import (
    CONF_SCAN_INTERVAL,
    CONF_TOKEN,
    CONF_URL,
    DEFAULT_SCAN_INTERVAL,
    DEFAULT_URL,
    DOMAIN,
    MAX_SCAN_INTERVAL,
    MIN_SCAN_INTERVAL,
)

_LOGGER = logging.getLogger(__name__)


class ShoppingHeldConfigFlow(ConfigFlow, domain=DOMAIN):
    """Fragt Adresse und Token ab und prüft sie gegen den Server."""

    VERSION = 1

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> ShoppingHeldOptionsFlow:
        return ShoppingHeldOptionsFlow()

    async def _validate(self, url: str, token: str) -> tuple[dict[str, Any] | None, str | None]:
        """Gibt (Einstellungen, Fehlerschlüssel) zurück."""
        client = ShoppingHeldClient(async_get_clientsession(self.hass), url, token)
        try:
            return await client.async_get_settings(), None
        except ShoppingHeldAuthError:
            return None, "invalid_auth"
        except ShoppingHeldConnectionError:
            return None, "cannot_connect"
        except ShoppingHeldError:
            return None, "unknown"
        except Exception:  # noqa: BLE001
            _LOGGER.exception("Unerwarteter Fehler bei der Prüfung der Zugangsdaten")
            return None, "unknown"

    @staticmethod
    def _unique_id(url: str, settings: Mapping[str, Any]) -> str:
        return f"{urlparse(url).netloc}/{settings.get('username', '')}".lower()

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                url = normalize_url(user_input[CONF_URL])
            except ValueError:
                errors[CONF_URL] = "invalid_url"
            else:
                token = user_input[CONF_TOKEN].strip()
                settings, error = await self._validate(url, token)
                if error or settings is None:
                    errors["base"] = error or "unknown"
                else:
                    await self.async_set_unique_id(self._unique_id(url, settings))
                    self._abort_if_unique_id_configured()
                    return self.async_create_entry(
                        title=f"ShoppingHeld ({settings.get('username', '?')})",
                        data={CONF_URL: url, CONF_TOKEN: token},
                    )

        # Adresse ist vorbelegt: normalerweise muss nur noch der Token eingetragen werden
        schema = vol.Schema(
            {vol.Required(CONF_URL, default=DEFAULT_URL): str, vol.Required(CONF_TOKEN): str}
        )
        return self.async_show_form(
            step_id="user",
            data_schema=self.add_suggested_values_to_schema(schema, user_input or {}),
            errors=errors,
        )

    async def async_step_reauth(self, entry_data: Mapping[str, Any]) -> ConfigFlowResult:
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Token wurde widerrufen/ist ungültig: neuen Token abfragen."""
        errors: dict[str, str] = {}
        entry = self._get_reauth_entry()
        if user_input is not None:
            token = user_input[CONF_TOKEN].strip()
            settings, error = await self._validate(entry.data[CONF_URL], token)
            if error or settings is None:
                errors["base"] = error or "unknown"
            elif self._unique_id(entry.data[CONF_URL], settings) != entry.unique_id:
                return self.async_abort(reason="wrong_account")
            else:
                return self.async_update_reload_and_abort(entry, data_updates={CONF_TOKEN: token})

        return self.async_show_form(
            step_id="reauth_confirm",
            data_schema=vol.Schema({vol.Required(CONF_TOKEN): str}),
            description_placeholders={"title": entry.title},
            errors=errors,
        )


class ShoppingHeldOptionsFlow(OptionsFlowWithReload):
    """Abfrageintervall einstellen (mehr Sekunden = weniger Last auf dem Server)."""

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        if user_input is not None:
            return self.async_create_entry(data={CONF_SCAN_INTERVAL: int(user_input[CONF_SCAN_INTERVAL])})
        current = self.config_entry.options.get(CONF_SCAN_INTERVAL, DEFAULT_SCAN_INTERVAL)
        schema = vol.Schema(
            {
                vol.Required(CONF_SCAN_INTERVAL, default=current): NumberSelector(
                    NumberSelectorConfig(
                        min=MIN_SCAN_INTERVAL,
                        max=MAX_SCAN_INTERVAL,
                        step=10,
                        unit_of_measurement="s",
                        mode=NumberSelectorMode.SLIDER,
                    )
                )
            }
        )
        return self.async_show_form(step_id="init", data_schema=schema)
