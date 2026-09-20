"""Konstanten der ShoppingHeld-Integration."""

from __future__ import annotations

from datetime import timedelta

DOMAIN = "shoppingheld"
# Muss mit "version" in manifest.json übereinstimmen (wird für den Cache-Buster der Karte genutzt,
# ein Test prüft die Übereinstimmung).
VERSION = "0.2.0"

CONF_URL = "url"
# Vorbelegung der Server-Adresse im Einrichtungsformular (änderbar, z. B. für eine eigene Instanz)
DEFAULT_URL = "https://shoppingheld.flohcloud.de"
CONF_TOKEN = "token"

CONF_SCAN_INTERVAL = "scan_interval"
DEFAULT_SCAN_INTERVAL = 60  # Sekunden
MIN_SCAN_INTERVAL = 30
MAX_SCAN_INTERVAL = 300
# Einstellungen (Einkaufstage, Listenname) ändern sich selten - nicht bei jeder Abfrage neu holen
SETTINGS_REFRESH_INTERVAL = timedelta(minutes=30)

# Ereignisse auf dem HA-Ereignisbus (für Automationen)
EVENT_ITEM_ADDED = f"{DOMAIN}_item_added"
EVENT_LIST_COMPLETED = f"{DOMAIN}_list_completed"

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
