# Rezeptbuch für Home Assistant

[![Validate](https://github.com/rieders/ha-rezeptbuch/actions/workflows/validate.yml/badge.svg)](https://github.com/rieders/ha-rezeptbuch/actions/workflows/validate.yml)
[![Tests](https://github.com/rieders/ha-rezeptbuch/actions/workflows/tests.yml/badge.svg)](https://github.com/rieders/ha-rezeptbuch/actions/workflows/tests.yml)
[![HACS Custom](https://img.shields.io/badge/HACS-Custom-41BDF5.svg)](https://hacs.xyz/docs/faq/custom_repositories)

> [!WARNING]
> **In Entwicklung.** Die Integration ist noch nicht einsatzbereit: Einrichtung über die
> Oberfläche, Aktionen, Entitäten und das Panel folgen in den nächsten Schritten.
> Datenformat und Funktionen können sich noch ändern.

**Rezeptbuch** ist eine eigenständige Rezeptdatenbank direkt in Home Assistant – ohne
externe Dienste wie Mealie und ohne separates Add-on. Rezepte lassen sich per URL von
Rezeptseiten (Chefkoch, Kochbar, Lecker, Food-Blogs …) importieren oder von Fotos aus
Kochbüchern und handgeschriebenen Karteikarten erfassen. Eigene Bewertungen, versionierte
Abänderungen und hierarchische Kategorien gehören dazu. Die Oberfläche ist deutsch.

<!-- Screenshot-Platzhalter: Rezeptliste, Rezeptdetail, Kochmodus -->

## Funktionen

### Bereits umgesetzt (Kern, noch ohne Oberfläche)

- **Datenbank** (SQLite unter `/config/rezeptbuch/`) mit Migrationen
- **Versionen:** Das Original bleibt immer unverändert; Änderungen werden als neue
  Version gespeichert, mit Diff-Ansicht („Zucker 200 g → 150 g“), Standardversion
  und „Zurück zum Original“
- **Inline-Notizen** an Zutaten und Schritten, ohne neue Version
- **Bewertungen** 0,5–5 Sterne pro Kochvorgang, getrennt nach HA-Benutzern
- **Hierarchische Kategorien** beliebiger Tiefe, mit Zyklusschutz, Zählung inklusive
  Unterkategorien und Standardbaum (Kochen, Backen, Getränke)
- **Volltextsuche** über Titel, Zutaten, Tags und Kategorien
- **Deutscher Zutaten-Parser** („1½ TL Zimt“, „2–3 Zwiebeln“, „1 Pck. Backpulver“,
  „etwas Pfeffer“, „1 Prise(n) Salz“ …) und Timer-Erkennung in Schritten („ca. 45 Min.“)
- **Einheiten-Umrechnung** für die Einkaufsliste (g/kg, ml/l, TL/EL); „Prise“ und
  „etwas“ werden nicht addiert
- **URL-Import** über recipe-scrapers und schema.org/JSON-LD; Ergebnis zuerst als
  Entwurf zur Korrektur, mit Duplikaterkennung, lokal gespeichertem Bild und
  lernender Kategorie-Zuordnung
- **Sicherheit beim Abruf:** Timeout, Größenlimit, Schutz vor Zugriffen auf private
  bzw. lokale Adressen (SSRF)

### Geplant

- Foto-Import über `ai_task` (gedruckt und handschriftlich, mehrere Seiten)
- Einrichtung und Optionen über die Oberfläche, Aktionen (`rezeptbuch.import_url` …)
- Sensoren „Anzahl Rezepte“, „Rezept des Tages“, Ideen-Sensoren, Einkaufsliste als `todo`-Entität
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

> Die Einrichtung unter *Einstellungen → Geräte & Dienste* ist erst ab der nächsten
> Entwicklungsstufe möglich.

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
