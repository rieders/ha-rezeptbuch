# Plan: Rezeptbuch

Grundlage: der ursprüngliche Auftrag und die Ergänzungen (Angebote, Panel-Vorgaben).
Reihenfolge wie vereinbart. Nach jedem Schritt gilt: Tests, ruff, Typprüfung und Actions grün,
dann committen und pushen, kurze Zusammenfassung.

| Schritt | Inhalt | Stand |
|---|---|---|
| 1 | DB, Modelle, Zutaten-Parser | ✅ |
| 2 | URL-Import | ✅ |
| 3 | Foto-Import über ai_task | ✅ |
| 4 | Einrichtung, Optionen, Aktionen, Entitäten, Diagnose | ✅ |
| 6+7 | WebSocket-API, HTTP-Views, Panel (Grundumfang) | ✅ |
| – | Smoke-Test im echten HA (`docs/smoke-test.md`) | ⏳ läuft |
| 7b | Panel vervollständigen, mit Fehlerbehebungen aus dem Smoke-Test | offen |
| 5 | Angebote & Einkauf (Marktguru) | offen |
| 8 | Tests vervollständigen | offen |
| 9 | README, Export/Backup | offen |

## 7b – Panel vervollständigen

Zuerst die Fehler aus dem Smoke-Test beheben, dann alles in einem Rutsch.

### Rezept bearbeiten und Versionen
- Editor für bestehende Rezepte (Titel, Portionen, Zeiten, Zutaten, Schritte inkl. Timer,
  Kategorien, Tags). Speichern erzeugt immer eine **neue Version** mit Label (Standard
  „Meine Version“) und Änderungsnotiz; das Original bleibt unverändert.
- Versionsumschalter im Rezept: Original | Meine Version | ältere Versionen.
- Diff zum Original (farbig, z. B. „Zucker 200 g → 150 g“, gestrichen/neu).
- „Als Standard setzen“ und „Auf Original zurücksetzen“.
- Inline-Notizen direkt an einzelnen Zutaten und Schritten (ohne neue Version);
  das Backend kann das schon, im Panel gibt es bisher nur Notizen zum ganzen Rezept.

### Kategorieverwaltung
- Kategoriebaum in der Seitenleiste des Panels, auf- und zuklappbar, mit Rezeptanzahl
  inklusive Unterkategorien, Icon und Farbe.
- Anlegen, Umbenennen, Icon und Farbe ändern, Löschen (Rezepte wandern zur Elternkategorie
  bzw. „Ohne Kategorie“).
- Verschieben und Umsortieren per Drag & Drop mit Zyklusprüfung; Verschieben und Löschen
  nur für Admins, serverseitig geprüft.
- Breadcrumbs (Backen › Kuchen › Obstkuchen).
- Kategorien im Rezept zuweisen (nicht nur im Entwurf).

### Kochmodus
- Vollbild, ein Schritt pro Bildschirm, große Schrift.
- Weiter/zurück per Wischen und Pfeiltasten.
- Abhakbare Zutatenliste.
- Timer aus den Schritten (vorhandene Timer-Logik wiederverwenden).
- Wake Lock; falls nicht unterstützt, sichtbarer Hinweis bzw. Fallback.
- Nach dem letzten Schritt: Dialog „Wie war's?“ mit Sternen, Text und Option „Änderungen als
  neue Version speichern“ (Version mit dem cook_log-Eintrag verknüpft).
- Gut bedienbar auf dem Tablet im Querformat und in der Companion-App.

### Weitere Lücken aus dem Abgleich mit dem Auftrag
- **Listenfilter** für mindestens n Sterne, nie gekocht und lange nicht gekocht. Das Backend
  (`recipes/list`) kann das schon, das Panel bietet bisher nur Kategorie, Tag und Sortierung.
- **Schalter „Unterkategorien einbeziehen“** beim Kategorie-Filter. Das Backend kann das,
  im Panel ist es fest eingeschaltet.
- **Import-Tab „Manuell“**: Die Entwurfs-Tabelle kennt die Quelle `manual`, aber es fehlen
  ein WebSocket-Befehl zum Anlegen eines leeren Entwurfs und der Tab im Import-Dialog.
- **Foto vom eigenen Ergebnis zur Bewertung**: Die Spalte `cook_log.photo` gibt es, aber
  WebSocket-Befehl, Aktion und Panel bieten keinen Upload an.
- **Titel in der Seitenleiste**: Laut Auftrag „Rezepte“, umgesetzt ist „Rezeptbuch“.
  Bitte entscheiden.

## 5 – Angebote & Einkauf (Aldi, Lidl & Co.)

Vorgaben aus der Ergänzung zum Auftrag; die Tabellen `offers`, `offer_mappings` und
`watchlist` existieren bereits, alles andere fehlt.

- **Provider**: Modul `offers/` mit austauschbarem Provider (`provider_base.py`:
  `search(query, zip_code)`, `weekly_offers(zip_code, retailers)`). Erster Provider Marktguru
  (`https://api.marktguru.de/api/v1/offers/search`, Parameter `as=web`, `q`, `zipCode`,
  `limit`, `offset`). API-Key nur über die Optionen, nie loggen. Timeouts, HTTP-Fehler und
  geänderte Antwortstruktur → Warnung und Repair-Issue statt Absturz. Drosseln und cachen,
  HA-eigene aiohttp-Session. TODO: Rewe-Provider (Daten aus ha-rewe).
- **Optionen** (Menüpunkt „Angebote“): an/aus, PLZ, Märkte (Mehrfachauswahl), Intervall
  (Standard: täglich früh und Montag nach Prospektwechsel).
- **Daten**: abgelaufene Angebote automatisch entfernen; `offer_mappings` lernen aus
  Bestätigen/Ablehnen.
- **Einkaufsliste mit Angeboten**: Fuzzy-Matching Zutat ↔ Produkt, Synonyme über Mappings,
  Grundvorrat optional ausblenden; Treffer mit Markt, Preis, Grundpreis, gültig bis.
  Ansicht nach Markt gruppiert mit Summen und geschätzter Ersparnis; „günstigster Markt gesamt“
  vs. „max. 2 Märkte“. Sync zu beliebiger todo-Entität (z. B. Bring!), Markt und Preis in der
  Beschreibung.
- **Rezepte aus Angeboten**: „Was kann ich diese Woche günstig kochen?“, kombinierbar mit
  Kategorie- und Bewertungsfilter; `sensor.rezeptbuch_angebots_tipp`.
- **Preisalarm**: Watchlist-Treffer → Event `rezeptbuch_offer_found` und Sensor; jeder Treffer
  nur einmal pro Angebotszeitraum.
- **Aktionen**: `refresh_offers`, `search_offers`, `add_recipe_to_shopping_list`
  (mit `with_offers`), `shopping_list_by_store`, `add_watch`, `remove_watch`.
- **Panel**: Bereich „Einkauf“ mit Tabs Liste | Nach Markt | Angebote | Merkliste; beim Rezept
  „Auf Einkaufsliste“ mit Portionswahl und Angebots-Vorschau.
- **Tests**: nur aufgezeichnete Antworten (Fixtures), Fehlerfälle, Matching und
  Mapping-Lernen, Gruppierung/Summen, Ablauf, Watchlist-Event nur einmal.

## 8 – Tests vervollständigen

Abgleich mit der Liste aus dem Auftrag: Zutaten-Parser, JSON-LD-Fallback, DB-CRUD,
Versionierung und Diff, Bewertungsdurchschnitt und Multi-User, Kategoriebaum (Verschieben,
Zyklen, Löschen, Zählung), Mapping beim Import, Config Flow. Dazu Tests für die neuen Teile
aus 7b und 5 sowie Frontend-Tests für Editor, Kochmodus und Kategoriebaum.

## 9 – README, Export/Backup

- **Export** als ZIP (JSON und Bilder) inkl. Versionen, Bewertungen, Notizen, Kategoriebaum
  und Tags; **Import** dieses Formats mit Zusammenführen statt Duplikaten (Originale müssen
  dabei angelegt werden können). Fehlt bisher komplett.
- TODO markieren: Import von Mealie- und Paprika-Exporten.
- README auf Deutsch mit Screenshot-Platzhaltern; Beispiel-Automationen: Rezept-URL vom Handy
  teilen → importieren, Sprachbefehl „Was koche ich heute?“, Einkaufsliste für den Wochenplan.
- Installationsweg über Marketplace (ab HA 2026.11) und HACS beschreiben.
- GitHub: Repo-Beschreibung und Topics setzen, sonst bleibt der HACS-Check rot.
