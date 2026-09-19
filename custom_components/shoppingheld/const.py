"""Konstanten der ShoppingHeld-Integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "shoppingheld"
# Muss mit "version" in manifest.json übereinstimmen (wird für den Cache-Buster der Karte genutzt,
# ein Test prüft die Übereinstimmung).
VERSION = "0.1.1"

CONF_URL = "url"
CONF_TOKEN = "token"

SCAN_INTERVAL = timedelta(seconds=60)
# Einstellungen (Einkaufstage, Listenname) ändern sich selten - nicht bei jeder Abfrage neu holen
SETTINGS_REFRESH_INTERVAL = timedelta(minutes=30)

CARD_URL_PATH = "/shoppingheld_static/shoppingheld-card.js"

# Identisch zu CATEGORY_LABELS in der Web-App (public/app.js) - Reihenfolge = Standardreihenfolge
CATEGORY_LABELS: dict[str, str] = {
    "gemuese": "Obst & Gemüse",
    "cerealien": "Cerealien & Brotaufstrich",
    "brot": "Brot & Backwaren",
    "kaffee": "Kaffee/Tee",
    "knabber": "Knabberzeug & Süßes",
    "fleisch": "Fleisch & Wurst",
    "konserven": "Konserven & Saucen",
    "milch": "Kühltheke",
    "milchprodukte": "Milchprodukte",
    "tk": "TK-Produkte",
    "getraenke": "Getränke",
    "haushalt": "Haushalt",
    "koerperpflege": "Körperpflege",
    "katzenfutter": "Katzenfutter",
    "sonstiges": "Sonstiges",
}
CATEGORIES = list(CATEGORY_LABELS)
DEFAULT_CATEGORY = "sonstiges"

WEEKDAY_NAMES_DE = ["Sonntag", "Montag", "Dienstag", "Mittwoch", "Donnerstag", "Freitag", "Samstag"]
