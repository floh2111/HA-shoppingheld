"""Rezept-Zutaten aus eingefügtem Text in Einkaufsartikel umwandeln.

Aus dem kopierten Text einer Rezeptseite (auch wenn Menge und Name in getrennten Zeilen stehen, wie bei Chefkoch)
werden Artikel mit sinnvollen Mengen:

    "1200 ml" / "Milch"            -> 2 Milch          (Packungen zu 1 Liter)
    "3 große" / "Ei(er), Größe L"  -> 3 Eier
    "400 g" / "Mehl"               -> 1 Mehl           (Packung zu 1 kg)
    "1 Prise(n)" / "Salz"          -> 1 Salz
    "500 g Tomaten"                -> 500 g Tomaten    (Frischware ohne feste Packung bleibt in Gramm)

Reine Textverarbeitung ohne Netzwerk, damit sie sich gut testen lässt.
"""

from __future__ import annotations

from dataclasses import dataclass
import math
import re

# --- Zahlen ---------------------------------------------------------------------------------------
_FRACTIONS = {"½": 0.5, "¼": 0.25, "¾": 0.75, "⅓": 1 / 3, "⅔": 2 / 3, "⅛": 0.125}
_NUM = r"(?:\d+/\d+|\d+(?:[.,]\d+)?(?:\s*(?:[½¼¾]|\d+/\d+))?|[½¼¾⅓⅔⅛])"
_AMOUNT_RE = re.compile(rf"^\s*(?P<n1>{_NUM})(?:\s*[-–—]\s*(?P<n2>{_NUM}))?\s*")


def _to_float(text: str) -> float:
    """'1,5' -> 1.5, '1 1/2' -> 1.5, '½' -> 0.5, '1.000' -> 1000."""
    text = re.sub(r"(?<=\d)\.(?=\d{3}(?!\d))", "", text)  # Tausenderpunkt
    total = 0.0
    for part in re.findall(r"\d+/\d+|\d+(?:[.,]\d+)?|[½¼¾⅓⅔⅛]", text):
        if part in _FRACTIONS:
            total += _FRACTIONS[part]
        elif "/" in part:
            top, bottom = part.split("/")
            total += int(top) / int(bottom) if int(bottom) else 0
        else:
            total += float(part.replace(",", "."))
    return total


# --- Einheiten ------------------------------------------------------------------------------------
_WEIGHT = {"g": 1, "gr": 1, "gramm": 1, "kg": 1000, "kilo": 1000}
_VOLUME = {"ml": 1, "milliliter": 1, "cl": 10, "dl": 100, "l": 1000, "liter": 1000}
# kleine Mengen: für die Einkaufsliste heißt das einfach "einmal kaufen"
_SMALL = {
    "el", "esslöffel", "tl", "teelöffel", "prise", "prisen", "msp", "messerspitze", "messerspitzen", "spritzer",
    "schuss", "handvoll", "tropfen", "schluck",
}
# gezählt, die Einheit selbst ist beim Einkaufen egal ("3 Scheiben Käse" -> 3 Käse)
_PIECE = {
    "stück", "stücke", "stk", "zehe", "zehen", "scheibe", "scheiben", "blatt", "blätter", "stiel", "stiele",
    "zweig", "zweige", "stange", "stangen", "würfel", "streifen",
}
# Gebinde, die auf der Liste als Einheit stehen bleiben: "2 Dosen Tomaten"
_PACK = {
    "dose": ("Dose", "Dosen"), "dosen": ("Dose", "Dosen"),
    "packung": ("Packung", "Packungen"), "packungen": ("Packung", "Packungen"), "pck": ("Packung", "Packungen"),
    "pkg": ("Packung", "Packungen"), "pack": ("Packung", "Packungen"),
    "päckchen": ("Päckchen", "Päckchen"),
    "becher": ("Becher", "Becher"),
    "glas": ("Glas", "Gläser"), "gläser": ("Glas", "Gläser"),
    "flasche": ("Flasche", "Flaschen"), "flaschen": ("Flasche", "Flaschen"),
    "tüte": ("Tüte", "Tüten"), "tüten": ("Tüte", "Tüten"),
    "bund": ("Bund", "Bund"),
    "rolle": ("Rolle", "Rollen"), "rollen": ("Rolle", "Rollen"),
    "kopf": ("Kopf", "Köpfe"), "köpfe": ("Kopf", "Köpfe"),
    "knolle": ("Knolle", "Knollen"), "knollen": ("Knolle", "Knollen"),
}
_ALL_UNITS = sorted({*_WEIGHT, *_VOLUME, *_SMALL, *_PIECE, *_PACK}, key=len, reverse=True)
_LETTER = "A-Za-zÄÖÜäöüß"
_UNIT_RE = re.compile(
    rf"(?P<unit>{'|'.join(re.escape(u) for u in _ALL_UNITS)})(?![{_LETTER}])\.?(?:\([a-zäöü]{{1,3}}\))?\s*", re.IGNORECASE
)
_SIZE_RE = re.compile(
    rf"(?:klein|mittelgroß|mittel|groß|gehäuft|gestrichen|dick|dünn)(?:e|er|en|es|em)?(?![{_LETTER}])\s*", re.IGNORECASE
)

# --- Übliche Packungsgrößen in Deutschland (Reihenfolge = Vorrang, spezielle zuerst) -----------------
# (Muster im kleingeschriebenen Namen, Packungsgröße, "g" oder "ml")
PACK_SIZES: list[tuple[str, int, str]] = [
    (r"buttermilch", 500, "ml"),
    (r"kokosmilch|kokosnussmilch", 400, "ml"),
    (r"(hafer|soja|mandel|reis|kokos)(drink|milch)", 1000, "ml"),
    (r"milch", 1000, "ml"),
    (r"saure sahne|schmand", 200, "g"),
    (r"crème fraîche|creme fraiche", 150, "g"),
    (r"sahne|cremefine", 200, "ml"),
    (r"joghurt|jogurt", 500, "g"),
    (r"mascarpone", 250, "g"),
    (r"quark", 250, "g"),
    (r"frischkäse", 200, "g"),
    (r"butterschmalz", 250, "g"),
    (r"butter|margarine", 250, "g"),
    (r"puderzucker|staubzucker", 500, "g"),
    (r"vanille(n)?zucker|vanillinzucker", 8, "g"),
    (r"zucker", 1000, "g"),
    (r"backpulver", 15, "g"),
    (r"trockenhefe", 7, "g"),
    (r"speisestärke|maisstärke|stärke", 400, "g"),
    (r"mehl", 1000, "g"),
    (r"haferflocken", 500, "g"),
    (r"\breis\b|basmati|jasmin|langkorn", 500, "g"),
    (r"nudel|spaghetti|penne|fusilli|tagliatelle|pasta|makkaroni|spätzle", 500, "g"),
    (r"hackfleisch|gehacktes", 500, "g"),
    (r"salz", 500, "g"),
    (r"olivenöl|rapsöl|sonnenblumenöl|\böl\b|öl$", 500, "ml"),
    (r"essig", 500, "ml"),
    (r"mineralwasser|sprudel", 1000, "ml"),
    (r"käse|gouda|emmentaler|parmesan|cheddar|mozzarella", 200, "g"),
]
_PACK_SIZES = [(re.compile(pattern), size, unit) for pattern, size, unit in PACK_SIZES]

# Zutaten, die man nicht einkauft
_SKIP_NAMES = {
    "wasser", "leitungswasser", "kaltes wasser", "warmes wasser", "heißes wasser", "lauwarmes wasser",
    "eiswürfel", "eis", "zutaten", "nach belieben", "nach geschmack",
}
# Namensumschreibungen
_ALIASES = [
    (re.compile(r"knoblauch(zehe|zehen|knolle)?"), "Knoblauch"),
    (re.compile(r"^(ei|eier)$"), "Eier"),
]
_TOLERANCE = 0.05  # 1050 ml Milch sind noch 1 Liter-Packung, nicht 2


@dataclass
class Ingredient:
    """Eine Zutat, wie sie im Rezept steht."""

    name: str
    quantity: float | None = None
    unit: str | None = None  # kleingeschrieben wie im Text, z. B. "g", "el", "dose"


@dataclass
class ShoppingItem:
    """Was auf die Einkaufsliste kommt."""

    text: str
    amount: int = 1
    unit: str = ""


# --- Zeilen erkennen --------------------------------------------------------------------------------
_BULLETS = "-–—•*·▢☐◦▪✓✔ \t"


def _is_heading(line: str) -> bool:
    lowered = line.lower()
    if line.endswith(":") or lowered in ("zutaten", "einkaufsliste", "zutatenliste"):
        return True
    return lowered.startswith("für ") and ("portion" in lowered or "person" in lowered or len(line.split()) <= 4)


def _parse_line(line: str) -> tuple[float | None, str | None, str]:
    """Zerlegt eine Zeile in (Menge, Einheit, Rest). Ohne führende Zahl ist die Menge None."""
    match = _AMOUNT_RE.match(line)
    if not match:
        return None, None, line.strip()
    quantity = _to_float(match.group("n2") or match.group("n1"))  # bei "2-3" die größere Zahl
    rest = line[match.end():]
    unit = None
    for _ in range(3):  # Einheit und Größenwörter in beliebiger Reihenfolge ("1 kleine Dose", "2 EL gehäufte")
        size = _SIZE_RE.match(rest)
        if size:
            rest = rest[size.end():]
            continue
        found = _UNIT_RE.match(rest) if unit is None else None
        if found:
            unit = found.group("unit").lower()
            rest = rest[found.end():]
            continue
        break
    return quantity, unit, rest.strip()


# Wörter, mit denen Notizen zu einer Zutat typischerweise anfangen ("zum Backen", "wer mag, kann ...")
_NOTE_STARTERS = {
    "zum", "zur", "zu", "nach", "für", "in", "auf", "mit", "ohne", "oder", "wer", "wenn", "auch", "evtl", "ggf", "z.",
    "je", "am", "im", "bei", "aus", "von", "als", "ca", "etwa", "optional", "alternativ", "kann", "können", "gerne",
}


def _looks_like_note(line: str) -> bool:
    """Kleingeschriebene Zeile direkt nach einer Zutat: Notiz ("fettarme", "zum Backen") oder eigene Zutat?

    Zutaten enden meist auf ein großgeschriebenes Hauptwort ("frisch gemahlener Pfeffer"), Notizen nicht
    ("frisch gemahlen") oder sie beginnen mit einer Präposition ("zum Backen").
    """
    words = line.split()
    if words[0].lower().rstrip(".,") in _NOTE_STARTERS:
        return True
    return not words[-1][:1].isupper()


def _clean_name(name: str) -> str:
    name = re.sub(r"(?<=\w)\(([a-zäöüß]{1,3})\)", r"\1", name)  # Ei(er) -> Eier, Zwiebel(n) -> Zwiebeln
    name = re.sub(r"\s*\([^)]*\)", "", name)  # weitere Klammern: (gehackt), (Typ 405)
    name = name.split(",")[0]  # ", fein gehackt", ", Größe L"
    name = re.sub(r"\s+(nach (geschmack|belieben|bedarf)|zum [a-zäöüß]+|optional|etwas|evtl\.?)$", "", name, flags=re.I)
    name = re.sub(r"\s+", " ", name).strip(" .;:-–—")
    return name[:1].upper() + name[1:] if name else name


def parse_recipe(text: str) -> list[Ingredient]:
    """Liest Zutaten aus Rezepttext. Menge und Name dürfen in derselben oder in getrennten Zeilen stehen."""
    result: list[Ingredient] = []
    pending: tuple[float, str | None] | None = None  # Zeile mit nur einer Menge, der Name kommt in der nächsten
    last_was_name = False

    def add(name: str, quantity: float | None, unit: str | None) -> None:
        cleaned = _clean_name(name)
        if not cleaned or cleaned.lower() in _SKIP_NAMES:
            return
        # "Salz und Pfeffer" ohne Menge sind zwei Zutaten
        parts = [p for p in re.split(r"\s+und\s+", cleaned) if p] if quantity is None else [cleaned]
        for part in parts:
            result.append(Ingredient(part[:1].upper() + part[1:], quantity, unit))

    for raw in text.replace("\t", " ").splitlines():
        line = raw.strip().lstrip(_BULLETS).strip()
        if not line:
            continue
        if _is_heading(line):
            pending, last_was_name = None, False
            continue
        quantity, unit, rest = _parse_line(line)
        if quantity is not None and not rest:  # nur Menge: der Name folgt
            pending, last_was_name = (quantity, unit), False
            continue
        if quantity is not None:
            add(rest, quantity, unit)
            pending, last_was_name = None, True
            continue
        # Zeile ohne Menge: Name (zum vorherigen Betrag) oder Notiz zur vorherigen Zutat
        if pending is None and last_was_name and line[0].islower() and _looks_like_note(line):
            continue  # "wer mag, kann Vollkornmehl verwenden", "fettarme", "zum Backen" ...
        if pending is not None:
            add(line, pending[0], pending[1])
        else:
            add(line, None, None)
        pending, last_was_name = None, True
    return result


# --- In Einkaufsartikel umrechnen ---------------------------------------------------------------------
def _ceil(value: float) -> int:
    return max(1, math.ceil(value - 1e-9))


def _pack_for(name: str) -> tuple[int, str] | None:
    lowered = name.lower()
    for pattern, size, unit in _PACK_SIZES:
        if pattern.search(lowered):
            return size, unit
    return None


def _kind(ingredient: Ingredient) -> tuple[str, float]:
    """(Art, Menge in Grundeinheit): 'small', 'count', 'pack:<Einheit>', 'g' (Gramm) oder 'ml' (Milliliter)."""
    quantity, unit = ingredient.quantity, ingredient.unit
    if quantity is None or unit in _SMALL:
        return "small", 1.0
    if unit in _PACK:
        return f"pack:{_PACK[unit][0]}", quantity
    if unit in _WEIGHT:
        return "g", quantity * _WEIGHT[unit]
    if unit in _VOLUME:
        return "ml", quantity * _VOLUME[unit]
    return "count", quantity  # Stück, Zehen, Scheiben ... oder gar keine Einheit


def _finalize(name: str, kind: str, quantity: float) -> ShoppingItem:
    for pattern, replacement in _ALIASES:
        if pattern.search(name.lower()):
            return ShoppingItem(replacement, 1 if replacement == "Knoblauch" else _ceil(quantity if kind == "count" else 1))
    if kind == "small":
        return ShoppingItem(name, 1)
    if kind.startswith("pack:"):
        amount = _ceil(quantity)
        singular = kind.split(":", 1)[1]
        plural = next(p for s, p in _PACK.values() if s == singular)
        return ShoppingItem(name, amount, singular if amount == 1 else plural)
    if kind in ("g", "ml"):
        pack = _pack_for(name)
        if pack and pack[1] == kind:
            return ShoppingItem(name, _ceil(quantity / pack[0] - _TOLERANCE))
        # Frischware ohne feste Packung: Menge behalten, ganze Kilo/Liter hübsch schreiben
        big, big_unit = 1000, ("kg" if kind == "g" else "l")
        if quantity >= big and quantity % big == 0:
            return ShoppingItem(name, int(quantity // big), big_unit)
        return ShoppingItem(name, max(1, round(quantity)), kind)
    return ShoppingItem(name, _ceil(quantity))


def to_shopping_items(ingredients: list[Ingredient]) -> list[ShoppingItem]:
    """Rechnet Zutaten in Einkaufsartikel um. Gleiche Zutaten werden VOR dem Umrechnen zusammengezählt
    (200 g + 300 g Mehl = 500 g = 1 Packung, nicht 2). Steht eine Zutat auch mit echter Menge im Rezept, zählt
    eine bloße Prise/Erwähnung nicht extra."""
    groups: dict[str, dict[str, float]] = {}
    names: dict[str, str] = {}
    for ingredient in ingredients:
        key = ingredient.name.lower()
        kind, quantity = _kind(ingredient)
        names.setdefault(key, ingredient.name)
        kinds = groups.setdefault(key, {})
        kinds[kind] = 1.0 if kind == "small" else kinds.get(kind, 0.0) + quantity
    items: list[ShoppingItem] = []
    for key, kinds in groups.items():
        if len(kinds) > 1:
            kinds.pop("small", None)
        for kind, quantity in kinds.items():
            items.append(_finalize(names[key], kind, quantity))
    # Namensumschreibungen können verschiedene Zutaten auf denselben Artikel abbilden (Ei/Eier)
    merged: dict[tuple[str, str], ShoppingItem] = {}
    for item in items:
        key = (item.text.lower(), item.unit)
        if key in merged:
            merged[key].amount += item.amount
        else:
            merged[key] = item
    return list(merged.values())


def recipe_to_items(text: str) -> list[ShoppingItem]:
    """Rezepttext -> Einkaufsartikel."""
    return to_shopping_items(parse_recipe(text))
