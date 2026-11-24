# Rezeptbuch für Home Assistant

[![Validate](https://github.com/rieders/ha-rezeptbuch/actions/workflows/validate.yml/badge.svg)](https://github.com/rieders/ha-rezeptbuch/actions/workflows/validate.yml)
[![Tests](https://github.com/rieders/ha-rezeptbuch/actions/workflows/tests.yml/badge.svg)](https://github.com/rieders/ha-rezeptbuch/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

> [!WARNING]
> **In Entwicklung.** Einrichtung, Aktionen und Entitäten funktionieren bereits; das Panel
> „Rezepte“ in der Seitenleiste folgt noch. Datenformat und Funktionen können sich ändern.

**Rezeptbuch** ist eine eigenständige Rezeptdatenbank direkt in Home Assistant – ohne
externe Dienste wie Mealie und ohne separates Add-on. Rezepte lassen sich per URL von
Rezeptseiten (Chefkoch, Kochbar, Lecker, Food-Blogs …) importieren oder von Fotos aus
Kochbüchern und handgeschriebenen Karteikarten erfassen. Eigene Bewertungen, versionierte
Abänderungen und hierarchische Kategorien gehören dazu. Die Oberfläche ist deutsch.

<!-- Screenshot-Platzhalter: Rezeptliste, Rezeptdetail, Kochmodus -->

## Funktionen

### Bereits umgesetzt

- **Einrichtung über die Oberfläche** (optional mit Standard-Kategorien) und **Optionen**:
  KI-Entität für den Foto-Import, Standard-Portionen, Speicherpfad, „Private
  Netzwerkadressen erlauben“, Kategorie-Filter und Gewichtung für „Rezept des Tages“,
  eigene Ideen-Sensoren (z. B. „Backidee der Woche“)
- **URL-Import** über recipe-scrapers und schema.org/JSON-LD; Ergebnis zuerst als
  Entwurf zur Korrektur (oder direkt übernehmen), mit Duplikaterkennung, lokal
  gespeichertem Bild und lernender Kategorie-Zuordnung
- **Foto-Import** über `ai_task`: Kochbuchseiten oder handgeschriebene Karteikarten,
  auch mehrere Seiten; unleserliche Stellen werden markiert
- **Versionen:** Das Original bleibt immer unverändert; Änderungen werden als neue
  Version gespeichert, mit Diff („Zucker 200 g → 150 g“) und „Zurück zum Original“
- **Inline-Notizen**, **Bewertungen** (0,5–5 Sterne, getrennt nach HA-Benutzern)
- **Hierarchische Kategorien** beliebiger Tiefe mit Zyklusschutz; **Volltextsuche**
- **Deutscher Zutaten-Parser** („1½ TL Zimt“, „2–3 Zwiebeln“, „1 Prise(n) Salz“ …)
  und Timer-Erkennung in Schritten („ca. 45 Min.“)
- **Einkaufsliste** mit Zusammenfassen (500 g + 1 kg Mehl → 1,5 kg; TL/EL);
  „Prise“ und „etwas“ werden nicht addiert
- **Aufräumen** einmal täglich: alte Entwürfe (> 14 Tage) und verwaiste Bilder
- **Sicherheit beim Abruf:** Timeout, Größenlimit, Schutz vor Zugriffen auf
  lokale/private Adressen (SSRF)

### Entitäten

| Entität | Inhalt |
|---|---|
| `sensor.rezeptbuch_anzahl_rezepte` | Anzahl Rezepte; Attribute: Anzahl je Hauptkategorie |
| `sensor.rezeptbuch_rezept_des_tages` | Täglich neu, bevorzugt gut bewertete und lange nicht gekochte Rezepte |
| `sensor.rezeptbuch_idee_…` | Eigene Ideen-Sensoren je Kategorie (täglich oder wöchentlich) |
| `todo.rezeptbuch_einkaufsliste` | Einkaufsliste |

### Aktionen

`rezeptbuch.import_url`, `import_image`, `confirm_draft`, `discard_draft`, `search`,
`get_recipe`, `random_recipe`, `rate_recipe`, `add_to_shopping_list`, `create_category`,
`assign_category`, `delete_recipe` – mit Rückgabewerten (z. B. `recipe_id`, `draft_id`)
für Automationen.

```yaml
# Beispiel: Rezept-URL importieren und direkt speichern
action: rezeptbuch.import_url
data:
  url: "https://www.chefkoch.de/rezepte/…"
  confirm: true
response_variable: ergebnis
```

### Geplant

- Angebote (Aldi, Lidl & Co.) für die Einkaufsliste, Preisalarm
- Panel „Rezepte“ in der Seitenleiste: Kategoriebaum, Suche und Filter, Editor,
  Kochmodus fürs Küchen-Tablet
- Export und Import als ZIP (Backup)

## Installation

Voraussetzung: Home Assistant **2026.2.3** oder neuer. Getestet wird automatisch gegen
HA 2026.2.3 (Python 3.13) und HA 2026.10.4 (Python 3.14).

### Über HACS (benutzerdefiniertes Repository)

1. HACS öffnen → Menü (⋮) → **Benutzerdefinierte Repositories**
2. Repository `https://github.com/rieders/ha-rezeptbuch` eintragen, Typ **Integration**
3. **Rezeptbuch** in HACS suchen und herunterladen
4. Home Assistant neu starten

### Manuell

1. Den Ordner `custom_components/rezeptbuch` aus diesem Repository nach
   `<config>/custom_components/rezeptbuch` kopieren
2. Home Assistant neu starten

Danach unter *Einstellungen → Geräte & Dienste → Integration hinzufügen* „Rezeptbuch“ wählen.

## Datenschutz

Alle Rezepte, Bilder und Bewertungen bleiben lokal in deiner Home-Assistant-Instanz.
Externe Zugriffe gibt es nur beim Import einer URL (Abruf der Rezeptseite und des Bildes)
und später optional für die KI-Auswertung von Fotos über deine eigene `ai_task`-Entität.

## Entwicklung

```bash
python -m venv .venv
.venv/bin/pip install -r requirements_test.txt
.venv/bin/ruff check custom_components tests
.venv/bin/pytest
```

Die Tests laufen ohne Netzwerkzugriff; HTTP-Antworten kommen aus Fixtures
(`tests/fixtures/`). Hinweise zum Testen unter Windows: [`tests/win_shims/README.md`](tests/win_shims/README.md).

## Lizenz

[MIT](LICENSE) © 2026 André Rieder
