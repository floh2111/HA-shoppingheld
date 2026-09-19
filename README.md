# HA-shoppingheld

Home-Assistant-Integration für **ShoppingHeld**, die gemeinsame, smarte Einkaufsliste
(Web-App/PWA mit Alexa-Skill): Die Liste erscheint in Home Assistant als To-do-Liste, dazu gibt es
zwei Sensoren, einen Service zum Hinzufügen und eine **Dashboard-Karte**, die die Liste so zeigt
wie die App – nach Kategorien gruppiert, komplett abgehakte Kategorien ausgegraut.

*English: custom integration for the ShoppingHeld shopping-list service – to-do list, sensors,
`shoppingheld.add_item` service and a category-grouped dashboard card. Setup instructions below
are in German; the UI strings are available in German and English.*

## Was ist enthalten?

| Was | Beschreibung |
|---|---|
| **To-do-Liste** `todo.shoppingheld_<listenname>` | Artikel anzeigen, hinzufügen, abhaken/zurücknehmen, löschen. Menge wird als „3× Apfel“ dargestellt. Kategorie wird beim Hinzufügen automatisch erkannt (wie beim Alexa-Skill). |
| **Sensor** „Offene Artikel“ | Anzahl der noch nicht abgehakten Artikel (Attribute: `checked_items`, `total_items`). |
| **Sensor** „Nächster Einkaufstag“ | Datum des nächsten Einkaufstags laut ShoppingHeld-Einstellungen (Attribute: `weekday`, `days_until`, `is_today`). |
| **Service** `shoppingheld.add_item` | Artikel mit Menge, Einheit und optional Kategorie hinzufügen. |
| **Karte** `custom:shoppingheld-card` | Dashboard-Karte im Stil der App. Wird mit der Integration automatisch bereitgestellt – keine extra Ressource nötig. |

Die Liste wird jede Minute abgefragt; eigene Änderungen (aus HA) erscheinen sofort.

## Installation

### Über HACS (empfohlen)

1. In Home Assistant **HACS → ⋮ → Benutzerdefinierte Repositories** öffnen.
2. Repository `https://github.com/floh2111/HA-shoppingheld` mit Kategorie **Integration** hinzufügen.
3. „ShoppingHeld“ in HACS suchen, **Herunterladen** und Home Assistant neu starten.

### Manuell

Den Ordner `custom_components/shoppingheld` in das `custom_components`-Verzeichnis von Home
Assistant kopieren (z. B. über das Samba- oder SSH-Add-on) und neu starten.

## Einrichtung

1. **Zugangs-Token erzeugen:** in der ShoppingHeld-Web-App unter
   *Einstellungen → Benutzerdaten → 🏠 Home Assistant* auf „Neuen Token erzeugen“ tippen und den
   angezeigten Token kopieren (er wird nur einmal angezeigt).
2. In Home Assistant **Einstellungen → Geräte & Dienste → Integration hinzufügen → ShoppingHeld**.
3. Den Token eintragen. Die Server-Adresse ist bereits vorausgefüllt und muss nur geändert werden, wenn du eine eigene ShoppingHeld-Instanz nutzt.

Der Token erlaubt nur den Zugriff auf deine Einkaufsliste (Artikel lesen, hinzufügen, abhaken,
löschen) – nicht auf dein Konto – und lässt sich in der App jederzeit widerrufen. Ist er ungültig,
fordert Home Assistant dich über „Neu authentifizieren“ zu einem neuen Token auf.

## Dashboard-Karte

Die Karte steht nach der Einrichtung im Karten-Dialog als **ShoppingHeld** bereit. Per YAML:

```yaml
type: custom:shoppingheld-card
entity: todo.shoppingheld_einkaufsliste
title: Einkaufsliste       # optional, Standard: Listenname aus ShoppingHeld
hide_add: false           # true = Eingabefeld zum Hinzufügen ausblenden
hide_checked: false       # true = abgehakte Artikel ausblenden
```

- Antippen eines Artikels hakt ihn ab bzw. nimmt das Abhaken zurück, ✕ löscht ihn.
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
- Es wird abgefragt (alle 60 s), nicht gepusht; Änderungen aus der App oder per Alexa können bis zu
  einer Minute brauchen, bis sie in Home Assistant erscheinen.
- Ein Konto = eine Liste. Wer sich mit anderen eine Liste teilt (Haushalt), sieht in HA dieselbe Liste.

## Entwicklung

```bash
pip install -r requirements_test.txt
pytest
```

Die Tests laufen gegen einen Fake-Server (`tests/conftest.py`) und prüfen Einrichtung,
To-do-Liste, Service, Sensoren, Fehlerfälle und erneute Anmeldung.

## Lizenz

MIT – siehe [LICENSE](LICENSE).
