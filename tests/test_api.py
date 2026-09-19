"""Reine Funktionen des API-Moduls (ohne Home Assistant)."""

import pytest

from custom_components.shoppingheld.api import format_summary, normalize_url, parse_item_text


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("Milch", (1, "Milch")),
        ("2 Milch", (2, "Milch")),
        ("2x Milch", (2, "Milch")),
        ("3× Eier", (3, "Eier")),
        ("  12 Äpfel  ", (12, "Äpfel")),
        ("500 g Butter", (1, "500 g Butter")),  # Einheit bleibt im Namen
        ("1 Liter Milch", (1, "1 Liter Milch")),
        ("100 Milch", (1, "100 Milch")),  # dreistellig: keine Menge
        ("7up", (1, "7up")),
        ("", (1, "")),
    ],
)
def test_parse_item_text(raw: str, expected: tuple[int, str]) -> None:
    assert parse_item_text(raw) == expected


@pytest.mark.parametrize(
    ("item", "expected"),
    [
        ({"text": "Milch", "amount": 1, "unit": ""}, "Milch"),
        ({"text": "Eier", "amount": 6, "unit": ""}, "6× Eier"),
        ({"text": "Butter", "amount": 500, "unit": "g"}, "500 g Butter"),
        ({"text": "Brot"}, "Brot"),
    ],
)
def test_format_summary(item: dict, expected: str) -> None:
    assert format_summary(item) == expected


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("https://a.example.org", "https://a.example.org"),
        ("https://a.example.org/", "https://a.example.org"),
        ("a.example.org", "https://a.example.org"),
        (" http://192.168.1.5:8787/backend ", "http://192.168.1.5:8787"),
    ],
)
def test_normalize_url(raw: str, expected: str) -> None:
    assert normalize_url(raw) == expected


@pytest.mark.parametrize("raw", ["", "   ", "ftp://x.org", "https://"])
def test_normalize_url_invalid(raw: str) -> None:
    with pytest.raises(ValueError):
        normalize_url(raw)
