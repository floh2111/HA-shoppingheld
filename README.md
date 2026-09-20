# HA-shoppingheld

Home-Assistant-Integration für **ShoppingHeld**, die gemeinsame, smarte Einkaufsliste
(Web-App/PWA mit Alexa-Skill): Die Liste erscheint in Home Assistant als To-do-Liste, dazu gibt es
Sensoren, Buttons, Ereignisse für Automationen und eine **Dashboard-Karte**, die die Liste so zeigt
wie die App – nach Kategorien gruppiert, mit Fortschrittsbalken, Wischen zum Löschen und
Vorschlags-Chips.

> **Hinweis:** Diese Integration ist eine **private Anbindung** an einen einzelnen ShoppingHeld-Server und
> nicht für die allgemeine Nutzung gedacht. Zugangs-Token gibt es nur für das Konto des Betreibers.

*English: custom integration for the ShoppingHeld shopping-list service – to-do list, sensors,
`shoppingheld.add_item` service and a category-grouped dashboard card. Setup instructions below
are in German; the UI strings are available in German and English.*

## Was ist enthalten?

| Was | Beschreibung |
|---|---|
| **To-do-Liste** `todo.shoppingheld_<listenname>` | Artikel anzeigen, hinzufügen, abhaken/zurücknehmen, löschen. Menge wird als „3× Apfel“ dargestellt. Kategorie wird beim Hinzufügen automatisch erkannt (wie beim Alexa-Skill). |
| **Sensor** „Offene Artikel“ | Anzahl der noch nicht abgehakten Artikel (Attribute: `checked_items`, `total_items`). |
| **Sensor** „Nächster Einkaufstag“ | Datum des nächsten Einkaufstags laut ShoppingHeld-Einstellungen (Attribute: `weekday`, `days_until`, `is_today`). |
| **Binärsensoren** „Einkaufstag heute“ / „Einkaufstag morgen“ | An, wenn heute bzw. morgen laut ShoppingHeld-Einstellungen Einkaufstag ist (wechselt um Mitternacht von selbst). |
| **Buttons** „Basics hinzufügen“ / „Abgehakte löschen“ | Legt alle Basics auf die Liste bzw. löscht alle abgehakten Artikel. |
| **Ereignisse** `shoppingheld_item_added`, `shoppingheld_list_completed` | Für Automationen: Artikel neu auf der Liste, Liste komplett abgehakt (siehe unten). |
| **Service** `shoppingheld.add_item` | Artikel mit Menge, Einheit und optional Kategorie hinzufügen. |
| **Service** `shoppingheld.set_amount` | Menge eines Artikels ändern (per Name oder ID). |
| **Karte** `custom:shoppingheld-card` | Dashboard-Karte im Stil der App. Wird mit der Integration automatisch bereitgestellt – keine extra Ressource nötig. |

Die Liste wird standardmäßig jede Minute abgefragt (einstellbar, s. u.); eigene Änderungen (aus HA)
erscheinen sofort.

### Abfrageintervall einstellen

*Einstellungen → Geräte & Dienste → ShoppingHeld → ⚙️ Konfigurieren*: zwischen 30 und 300 Sekunden
(Standard 60). Ein größeres Intervall schont den ShoppingHeld-Server, Änderungen aus der App
erscheinen dann etwas später.

## Installation

### Über HACS (empfohlen)

1. In Home Assistant **HACS → ⋮ → Benutzerdefinierte Repositories** öffnen.
2. Repository `https://github.com/floh2111/HA-shoppingheld` mit Kategorie **Integration** hinzufügen.
3. „ShoppingHeld“ in HACS suchen, **Herunterladen** und Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/shoppingheld` in das `custom_components`-Verzeichnis von Home
Assistant kopieren (z. B. über das Samba- oder SSH-Add-on) und neu starten.

## Einrichtung

1. **Zugangs-Token besorgen:** Der Token wird vom Betreiber des ShoppingHeld-Servers ausgestellt – die
   App selbst bietet dafür keine Oberfläche. Er wird nur einmal angezeigt.
2. In Home Assistant **Einstellungen → Geräte & Dienste → Integration hinzufügen → ShoppingHeld**.
3. Den Token eintragen. Die Server-Adresse ist bereits vorausgefüllt und muss nur geändert werden, wenn du eine eigene ShoppingHeld-Instanz nutzt.

Der Token erlaubt nur den Zugriff auf deine Einkaufsliste (Artikel lesen, hinzufügen, abhaken,
löschen, Menge ändern, Basics) – nicht auf dein Konto – und lässt sich jederzeit widerrufen. Ist er ungültig,
fordert Home Assistant dich über „Neu authentifizieren“ zu einem neuen Token auf.

## Dashboard-Karte

Die Karte steht nach der Einrichtung im Karten-Dialog als **ShoppingHeld** bereit. Per YAML:

```yaml
type: custom:shoppingheld-card
entity: todo.shoppingheld_einkaufsliste
title: Einkaufsliste       # optional, Standard: Listenname aus ShoppingHeld
hide_add: false           # true = Eingabefeld (und Vorschlags-Chips) ausblenden
hide_checked: false       # true = abgehakte Artikel ausblenden
hide_chips: false         # true = Vorschlags-Chips ausblenden
```

- Oben zeigt ein **Fortschrittsbalken** „12 von 18 im Wagen“; ist alles abgehakt, wird er grün
  („Alles im Wagen! 🎉“, mit kleiner Animation).
- Antippen eines Artikels hakt ihn ab bzw. nimmt das Abhaken zurück. **Nach links wischen** (oder ✕)
  löscht ihn, mit **− / +** änderst du die Menge.
- Über dem Eingabefeld stehen **Vorschlags-Chips**: deine Basics (`+ Milch`) und oft gekaufte
  Artikel (`💡 Kaffee`) – ein Tipp legt sie auf die Liste. Was schon offen auf der Liste steht,
  wird nicht vorgeschlagen. Es werden die ersten sechs gezeigt, „+N mehr“ klappt den Rest auf.
- Kategorien lassen sich auf- und zuklappen; ist in einer Kategorie alles abgehakt, wird sie
  ausgegraut.
- Ins Eingabefeld kann auch z. B. `2 Milch` geschrieben werden – die Menge wird erkannt.
- An Einkaufstagen zeigt die Karte oben „🛒 Heute Einkaufstag“.

## Service `shoppingheld.add_item`

```yaml
action: shoppingheld.add_item
target:
  entity_id: todo.shoppingheld_einkaufsliste
data:
  item: Milch
  amount: 2            # optional, Standard 1 ("2 Milch" als Text geht auch)
  unit: Packung        # optional
  category: milch      # optional, sonst automatisch erkannt
```

Mögliche Kategorien: `gemuese`, `cerealien`, `brot`, `kaffee`, `knabber`, `fleisch`, `konserven`,
`milch`, `milchprodukte`, `tk`, `getraenke`, `haushalt`, `koerperpflege`, `katzenfutter`,
`sonstiges`.

## Ereignisse für Automationen

| Ereignis | Wann | Daten |
|---|---|---|
| `shoppingheld_item_added` | Ein Artikel ist neu auf der Liste – egal ob aus HA, der App oder per Alexa | `text`, `amount`, `unit`, `category`, `item_id`, `list_name`, `entry_id` |
| `shoppingheld_list_completed` | Der letzte offene Artikel wurde abgehakt | `total_items`, `list_name`, `entry_id` |

Erkannt werden sie beim Abfragen (also mit dem eingestellten Intervall verzögert); direkt nach dem
Einrichten oder Neuladen der Integration gibt es keine Ereignisse für bereits vorhandene Artikel.

```yaml
automation:
  - alias: "Einkauf erledigt"
    triggers:
      - trigger: event
        event_type: shoppingheld_list_completed
    actions:
      - action: notify.notify
        data:
          message: "Alles im Wagen! 🎉"
  - alias: "Neuer Artikel auf der Liste"
    triggers:
      - trigger: event
        event_type: shoppingheld_item_added
    actions:
      - action: notify.notify
        data:
          message: "Neu auf der Einkaufsliste: {{ trigger.event.data.amount }}× {{ trigger.event.data.text }}"
```

## Rezepte auf die Liste: `shoppingheld.add_recipe`

Kopierten Rezepttext (z. B. die Zutatentabelle einer Rezeptseite) in Einkaufsartikel mit **sinnvollen Mengen**
umwandeln. Es funktioniert auch, wenn Menge und Name – wie bei Chefkoch – in **getrennten Zeilen** stehen.
Notizen („wer mag, kann …“, „zum Backen“), Überschriften („Für den Teig:“) und Wasser werden weggelassen.

| Im Rezept | Auf der Liste | Warum |
|---|---|---|
| `1200 ml` / `Milch` | **2 Milch** | Packungen zu 1 Liter |
| `750 ml Milch` | 1 Milch | 1 Packung reicht |
| `3 große` / `Ei(er), Größe L` | **3 Eier** | Stückware bleibt Stückware |
| `400 g` / `Mehl` | 1 Mehl | Packung zu 1 kg |
| `200 g Butter` / `300 g Butter` | 1 / 2 Butter | Packung zu 250 g |
| `1 Prise(n)` / `Salz` | 1 Salz | kleine Mengen = einmal kaufen |
| `500 g Tomaten` | 500 g Tomaten | Frischware ohne feste Packung behält die Menge |
| `2 Dosen Tomaten (gehackt)` | 2 Dosen Tomaten | Gebinde bleiben als Einheit |
| `Knoblauchzehen`, `½ Bund Petersilie` | Knoblauch, 1 Bund Petersilie | |

Gleiche Zutaten werden **vor** dem Umrechnen zusammengezählt (200 g + 300 g Mehl = 1 Packung, nicht 2).
Die hinterlegten Packungsgrößen (Milch 1 l, Sahne 200 ml, Butter 250 g, Mehl/Zucker 1 kg, Nudeln/Reis 500 g,
Hackfleisch 500 g, Quark 250 g, Joghurt 500 g, Käse 200 g u. a.) stehen in `recipe.py` (`PACK_SIZES`).

```yaml
action: shoppingheld.add_recipe
target:
  entity_id: todo.shoppingheld_einkaufsliste
data:
  text: |
    400 g Mehl
    3 große Eier
    1200 ml Milch
  dry_run: false      # true = nichts hinzufügen, nur die erkannten Artikel zurückgeben
response_variable: ergebnis   # ergebnis.summary, ergebnis.items, ergebnis.added
```

### Aus dem iPhone-Teilen-Menü

Ein Kurzbefehl schickt den markierten Text an einen Webhook, eine Automation ruft den Dienst auf:

```yaml
alias: "Rezept auf die Einkaufsliste"
triggers:
  - trigger: webhook
    webhook_id: <langes-zufälliges-geheimnis>
    allowed_methods: [POST]
    local_only: false
actions:
  - action: shoppingheld.add_recipe
    target:
      entity_id: todo.shoppingheld_einkaufsliste
    data:
      text: "{{ trigger.json.text | default('') }}"
    response_variable: rezept
  - action: notify.mobile_app_<dein_handy>
    data:
      message: "Auf der Liste: {{ rezept['todo.shoppingheld_einkaufsliste'].summary }}"
```

Im Kurzbefehl (Aktion *Inhalt von URL abrufen*, Methode POST, Anfragetext JSON) das Feld `text` mit dem geteilten
Text füllen. Der Text wird **nicht** vorher zeilenweise zerlegt – das übernimmt die Integration.

Grenzen: höchstens 8000 Zeichen und 60 Artikel je Aufruf. Mengen werden nicht auf Portionen umgerechnet.

## Beispiel-Automation

Erinnerung am Einkaufstag, solange noch etwas offen ist:

```yaml
automation:
  - alias: "Einkaufstag: Liste noch offen"
    triggers:
      - trigger: time
        at: "16:00:00"
    conditions:
      - condition: template
        value_template: "{{ state_attr('sensor.shoppingheld_einkaufsliste_nachster_einkaufstag', 'is_today') }}"
      - condition: numeric_state
        entity_id: sensor.shoppingheld_einkaufsliste_offene_artikel
        above: 0
    actions:
      - action: notify.notify
        data:
          message: "Heute ist Einkaufstag – {{ states('sensor.shoppingheld_einkaufsliste_offene_artikel') }} Artikel offen."
```

(Die genauen Entity-IDs stehen unter *Einstellungen → Geräte & Dienste → ShoppingHeld*.)

## Grenzen

- Artikel **umbenennen** wird von ShoppingHeld nicht unterstützt (in HA: löschen und neu anlegen).
- Es wird abgefragt (Standard alle 60 s, einstellbar), nicht gepusht; Änderungen aus der App oder per
  Alexa können bis zum nächsten Abruf brauchen, bis sie in Home Assistant erscheinen.
- Ein Konto = eine Liste. Wer sich mit anderen eine Liste teilt (Haushalt), sieht in HA dieselbe Liste.

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Tests laufen gegen einen Fake-Server (`tests/conftest.py`) und prüfen Einrichtung,
To-do-Liste, Services, Sensoren, Buttons, Ereignisse, Optionen, Fehlerfälle und erneute Anmeldung.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
