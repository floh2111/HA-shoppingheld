"""Rezept-Parser (Text -> Einkaufsartikel) und der Dienst shoppingheld.add_recipe."""

from __future__ import annotations

import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError

from custom_components.shoppingheld.recipe import recipe_to_items

from .conftest import FakeServer

ENTITY = "todo.shoppingheld_einkaufsliste"

# So kommt der markierte Text der Chefkoch-Zutatentabelle an: Menge und Name stehen in getrennten Zeilen,
# dazu Notizen in kleiner Schrift ("wer mag ...", "fettarme", "zum Backen")
CHEFKOCH = """Zutaten
Für 4 Portionen
400 g
Mehl
wer mag, kann Vollkornmehl verwenden
3 große
Ei(er), Größe L
1 Prise(n)
Salz
750 ml
Milch
fettarme
30 ml
Mineralwasser mit Kohlensäure
Butter
zum Backen"""


def items(text: str) -> list[tuple[str, int, str]]:
    return [(i.text, i.amount, i.unit) for i in recipe_to_items(text)]


def test_chefkoch_table_from_two_line_format() -> None:
    assert items(CHEFKOCH) == [
        ("Mehl", 1, ""),  # 400 g -> 1 Packung zu 1 kg
        ("Eier", 3, ""),  # "3 große" + "Ei(er), Größe L"
        ("Salz", 1, ""),  # 1 Prise
        ("Milch", 1, ""),  # 750 ml -> 1 Liter-Packung
        ("Mineralwasser mit Kohlensäure", 1, ""),  # 30 ml -> 1 Flasche, nicht 0
        ("Butter", 1, ""),  # ohne Menge
    ]


@pytest.mark.parametrize(
    ("text", "expected"),
    [
        # Packungen zu üblichen Größen
        ("1200 ml Milch", [("Milch", 2, "")]),  # das Beispiel: 1,2 Liter = 2 Packungen
        ("1050 ml Milch", [("Milch", 1, "")]),  # 5 % Toleranz
        ("1,5 l Milch", [("Milch", 2, "")]),
        ("400 g Mehl", [("Mehl", 1, "")]),
        ("1,2 kg Mehl", [("Mehl", 2, "")]),
        ("200 g Butter", [("Butter", 1, "")]),
        ("300 g Butter", [("Butter", 2, "")]),
        ("200 ml Sahne", [("Sahne", 1, "")]),
        ("250 ml Sahne", [("Sahne", 2, "")]),
        ("500 g Quark", [("Quark", 2, "")]),
        ("400 g Spaghetti", [("Spaghetti", 1, "")]),
        # Frischware ohne feste Packung behält die Menge
        ("500 g Tomaten", [("Tomaten", 500, "g")]),
        ("1 kg Kartoffeln", [("Kartoffeln", 1, "kg")]),
        ("1,5 kg Kartoffeln", [("Kartoffeln", 1500, "g")]),
        ("1.000 g Kartoffeln", [("Kartoffeln", 1, "kg")]),
        ("2 l Apfelsaft", [("Apfelsaft", 2, "l")]),
        # Stückware
        ("3 Eier", [("Eier", 3, "")]),
        ("1 Ei", [("Eier", 1, "")]),
        ("3 große Eier", [("Eier", 3, "")]),
        ("2 mittelgroße Zwiebeln", [("Zwiebeln", 2, "")]),
        ("½ Zitrone", [("Zitrone", 1, "")]),
        ("1 1/2 Zwiebeln", [("Zwiebeln", 2, "")]),
        ("2-3 Knoblauchzehen", [("Knoblauch", 1, "")]),
        ("4 Scheiben Käse", [("Käse", 4, "")]),
        # Gebinde bleiben als Einheit stehen
        ("2 Dosen Tomaten (gehackt)", [("Tomaten", 2, "Dosen")]),
        ("1 Dose(n) Mais", [("Mais", 1, "Dose")]),
        ("1 Pck. Vanillezucker", [("Vanillezucker", 1, "Packung")]),
        ("½ Bund Petersilie", [("Petersilie", 1, "Bund")]),
        ("2 Becher Schmand", [("Schmand", 2, "Becher")]),
        # kleine Mengen = einmal kaufen
        ("1 EL Olivenöl", [("Olivenöl", 1, "")]),
        ("1 TL Zimt", [("Zimt", 1, "")]),
        ("1 Prise Salz", [("Salz", 1, "")]),
        ("2 Msp. Cayennepfeffer", [("Cayennepfeffer", 1, "")]),
        # Namen säubern
        ("2 Zwiebeln, fein gehackt", [("Zwiebeln", 2, "")]),
        ("500 g Mehl (Type 405)", [("Mehl", 1, "")]),
        ("1 Tomate(n)", [("Tomaten", 1, "")]),
        ("Salz nach Geschmack", [("Salz", 1, "")]),
        ("Salz und Pfeffer", [("Salz", 1, ""), ("Pfeffer", 1, "")]),
        # nicht einkaufen
        ("200 ml Wasser", []),
        ("Zutaten", []),
        ("Für den Teig:", []),
        ("Für 4 Portionen", []),
    ],
)
def test_single_lines(text: str, expected: list[tuple[str, int, str]]) -> None:
    assert items(text) == expected


def test_bullets_checkboxes_and_tabs() -> None:
    text = "Für den Teig:\n- 250 g Mehl\n• 100 g Zucker\t\n▢ 1 Ei\n☐ Butter\nFür die Füllung:\n500 g\tQuark"
    assert items(text) == [
        ("Mehl", 1, ""),
        ("Zucker", 1, ""),
        ("Eier", 1, ""),
        ("Butter", 1, ""),
        ("Quark", 2, ""),
    ]


def test_same_ingredient_is_summed_before_converting() -> None:
    # 200 g + 300 g Mehl = 500 g = eine Packung, nicht zwei
    assert items("200 g Mehl\n300 g Mehl") == [("Mehl", 1, "")]
    # 2 Eier + 1 Ei = 3 Eier; die Prise Salz zählt neben dem TL Salz nicht doppelt
    assert items("2 Eier\n1 Ei\n1 Prise Salz\n1 TL Salz") == [("Eier", 3, ""), ("Salz", 1, "")]
    # Milch aus zwei Stellen: 1200 + 1500 + 1050 = 3750 ml = 4 Packungen
    assert items("1200 ml Milch\n1,5 l Milch\n1050 ml Milch") == [("Milch", 4, "")]
    # eine echte Menge schlägt die bloße Nennung
    assert items("Butter\n125 g Butter") == [("Butter", 1, "")]


def test_lowercase_ingredient_is_not_mistaken_for_a_note() -> None:
    # "frisch gemahlener Pfeffer" endet auf ein Hauptwort = Zutat, "frisch gemahlen" wäre eine Notiz
    assert items("500 g Quark\nfrisch gemahlener Pfeffer") == [("Quark", 2, ""), ("Frisch gemahlener Pfeffer", 1, "")]
    assert items("Pfeffer\nfrisch gemahlen") == [("Pfeffer", 1, "")]
    assert items("Salz\nzum Bestreuen\nwer mag, kann auch Chili nehmen") == [("Salz", 1, "")]


def test_amounts_survive_odd_input() -> None:
    assert items("") == []
    assert items("   \n\n  ") == []
    assert items("1200") == []  # nur eine Zahl, kein Name
    assert items("0 g Mehl") == [("Mehl", 1, "")]  # nie 0
    assert items("3 Eier\nEier") == [("Eier", 3, "")]


# --- Dienst ---------------------------------------------------------------------------------------
async def test_add_recipe_service_adds_items_with_amounts(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    before = len(server.items)
    response = await hass.services.async_call(
        "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": CHEFKOCH}, blocking=True, return_response=True
    )
    added = server.items[before:]
    assert [(i["text"], i["amount"], i["unit"]) for i in added] == [
        ("Mehl", 1, ""), ("Eier", 3, ""), ("Salz", 1, ""), ("Milch", 1, ""),
        ("Mineralwasser mit Kohlensäure", 1, ""), ("Butter", 1, ""),
    ]
    assert next(i for i in added if i["text"] == "Milch")["category"] == "milch"  # Kategorie wie beim normalen Hinzufügen
    result = response[ENTITY]
    assert result["added"] == 6 and result["dry_run"] is False
    assert result["summary"].startswith("Mehl, 3× Eier, Salz, Milch")
    assert hass.states.get(ENTITY).state == str(3 + 6)  # 3 offene vorher + 6 neue


async def test_add_recipe_units_and_larger_amounts(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    before = len(server.items)
    await hass.services.async_call(
        "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": "500 g Tomaten\n2 Dosen Mais\n1,5 kg Kartoffeln"},
        blocking=True, return_response=True,
    )
    added = [(i["text"], i["amount"], i["unit"]) for i in server.items[before:]]
    assert added == [("Tomaten", 500, "g"), ("Mais", 2, "Dosen"), ("Kartoffeln", 1500, "g")]  # 500 > 99 geht hier


async def test_add_recipe_dry_run_adds_nothing(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    server.actions.clear()
    response = await hass.services.async_call(
        "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": CHEFKOCH, "dry_run": True},
        blocking=True, return_response=True,
    )
    assert not any(a["action"] == "add" for a in server.actions)
    assert response[ENTITY]["added"] == 0 and len(response[ENTITY]["items"]) == 6


async def test_add_recipe_without_ingredients_is_rejected(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": "Zutaten\nFür 4 Portionen"}, blocking=True
        )


async def test_add_recipe_too_long_is_rejected(hass: HomeAssistant, setup_integration: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError):
        await hass.services.async_call(
            "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": "Mehl\n" * 3000}, blocking=True
        )


async def test_add_recipe_limits_number_of_items(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    before = len(server.items)
    text = "\n".join(f"Artikel{chr(65 + i % 26)}{i}" for i in range(100))
    await hass.services.async_call("shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": text}, blocking=True)
    assert len(server.items) - before == 60


async def test_add_recipe_reports_server_errors(
    hass: HomeAssistant, setup_integration: MockConfigEntry, server: FakeServer
) -> None:
    server.status = 500
    with pytest.raises(HomeAssistantError):
        await hass.services.async_call(
            "shoppingheld", "add_recipe", {"entity_id": ENTITY, "text": "400 g Mehl"}, blocking=True
        )
