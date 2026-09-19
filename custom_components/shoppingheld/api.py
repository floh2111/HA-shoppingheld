"""Kleiner asynchroner Client für die ShoppingHeld-Web-API (/backend)."""

from __future__ import annotations

import asyncio
import re
from typing import Any
from urllib.parse import urlparse

import aiohttp

from .const import CATEGORIES, DEFAULT_CATEGORY

REQUEST_TIMEOUT = 15

# Amount-Erkennung beim Anlegen per Text (z.B. Assist: "2 Milch"): führende Zahl 1-99, aber NICHT
# wenn danach eine Mengen-Einheit kommt ("500 g Butter", "1 Liter Milch") - die bleibt im Namen.
_LEADING_AMOUNT = re.compile(r"^\s*(\d{1,2})\s*(?:[x×]\s*|\s+)(\S.*?)\s*$", re.IGNORECASE)
_UNIT_WORD = re.compile(r"^(kg|g|gr|mg|l|ml|cl|dl|liter|stk|stück|pkg|pck)\b", re.IGNORECASE)


class ShoppingHeldError(Exception):
    """Allgemeiner Fehler der ShoppingHeld-API."""


class ShoppingHeldAuthError(ShoppingHeldError):
    """Token ungültig oder widerrufen."""


class ShoppingHeldConnectionError(ShoppingHeldError):
    """Server nicht erreichbar."""


def normalize_url(raw: str) -> str:
    """Bringt eine eingegebene Adresse in die Form https://host[:port] (ohne Slash am Ende)."""
    value = (raw or "").strip()
    if not value:
        raise ValueError("empty url")
    if "://" not in value:
        value = "https://" + value
    parsed = urlparse(value)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise ValueError("invalid url")
    return f"{parsed.scheme}://{parsed.netloc}"


def parse_item_text(text: str) -> tuple[int, str]:
    """Zerlegt "2 Milch" / "2x Milch" in (2, "Milch"); alles andere bleibt (1, text)."""
    stripped = (text or "").strip()
    match = _LEADING_AMOUNT.match(stripped)
    if match and int(match.group(1)) >= 1 and not _UNIT_WORD.match(match.group(2)):
        return int(match.group(1)), match.group(2)
    return 1, stripped


def format_summary(item: dict[str, Any]) -> str:
    """Anzeigetext eines Artikels inkl. Menge, wie er in der To-do-Liste erscheint."""
    text = item.get("text", "")
    amount = int(item.get("amount") or 1)
    unit = (item.get("unit") or "").strip()
    if unit:
        return f"{amount} {unit} {text}"
    if amount > 1:
        return f"{amount}× {text}"
    return text


class ShoppingHeldClient:
    """Spricht mit /backend, authentifiziert per persönlichem Zugangs-Token."""

    def __init__(self, session: aiohttp.ClientSession, base_url: str, token: str) -> None:
        self._session = session
        self._url = f"{base_url}/backend"
        self._headers = {"Authorization": f"Bearer {token}"}

    async def _request(self, method: str, payload: dict[str, Any] | None = None) -> Any:
        try:
            async with asyncio.timeout(REQUEST_TIMEOUT):
                async with self._session.request(
                    method, self._url, json=payload, headers=self._headers
                ) as response:
                    if response.status == 401:
                        raise ShoppingHeldAuthError("Zugangs-Token ungültig oder widerrufen")
                    try:
                        data = await response.json(content_type=None)
                    except (aiohttp.ContentTypeError, ValueError) as err:
                        raise ShoppingHeldError(f"Unerwartete Antwort (HTTP {response.status})") from err
                    if response.status >= 400:
                        message = data.get("error") if isinstance(data, dict) else None
                        raise ShoppingHeldError(message or f"HTTP {response.status}")
                    return data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise ShoppingHeldConnectionError(str(err) or "Verbindung fehlgeschlagen") from err

    async def _action(self, action: str, **params: Any) -> Any:
        return await self._request("POST", {"action": action, **params})

    async def async_get_items(self) -> list[dict[str, Any]]:
        data = await self._request("GET")
        if not isinstance(data, list):
            raise ShoppingHeldError("Unerwartete Antwort beim Laden der Liste")
        return data

    async def async_get_settings(self) -> dict[str, Any]:
        data = await self._action("get_settings")
        if not isinstance(data, dict):
            raise ShoppingHeldError("Unerwartete Antwort beim Laden der Einstellungen")
        return data

    async def async_guess_category(self, text: str) -> str:
        """Fragt die serverseitige Kategorie-Erkennung (wie beim Alexa-Skill), Fallback "sonstiges"."""
        try:
            data = await self._action("guess_category", text=text)
        except ShoppingHeldConnectionError:
            raise
        except ShoppingHeldError:
            return DEFAULT_CATEGORY
        category = data.get("category") if isinstance(data, dict) else None
        return category if category in CATEGORIES else DEFAULT_CATEGORY

    async def async_add_item(
        self, text: str, amount: int, category: str, unit: str | None = None
    ) -> None:
        params: dict[str, Any] = {"text": text, "amount": amount, "category": category}
        if unit:
            params["unit"] = unit
        await self._action("add", **params)

    async def async_toggle_item(self, item_id: int) -> None:
        await self._action("toggle", id=item_id)

    async def async_delete_item(self, item_id: int) -> None:
        await self._action("delete", id=item_id)
