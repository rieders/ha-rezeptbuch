# Smoke-Test im echten Home Assistant

Voraussetzung: Home Assistant **2026.2.3 oder neuer**, Internetzugang (beim ersten Start
wird `recipe-scrapers` installiert). Das eigene Integrations-Icon erscheint erst ab HA 2026.3.

## 1. Installation

Repository-Adresse für Variante A und B: `https://github.com/rieders/ha-rezeptbuch`.
Es gibt noch keine Releases, installiert wird deshalb der aktuelle Stand von `main`
(wird als Commit-Hash angezeigt).

### Variante A: Marketplace (ab HA 2026.11)

Ab 2026.11 ist HACS als „Marketplace“ in Home Assistant eingebaut.

1. **Einstellungen → Marketplace** → **Über Link hinzufügen** (benutzerdefiniertes Repository).
2. Repository-Adresse eintragen, Typ **Integration** → **Hinzufügen**.
3. **Rezeptbuch** öffnen → **Herunterladen**.
4. Home Assistant **neu starten**.

Bei späteren Updates: Rezeptbuch im Marketplace → **Erneut herunterladen**, dann neu starten.

### Variante B: HACS (HA vor 2026.11)

1. HACS öffnen → oben rechts **⋮** → **Benutzerdefinierte Repositories**.
2. Repository-Adresse eintragen, Typ: **Integration** → **Hinzufügen**.
3. In HACS nach **Rezeptbuch** suchen → **Herunterladen**.
4. Home Assistant **neu starten**.

Bei späteren Updates: In HACS beim Rezeptbuch **⋮ → Erneut herunterladen**, dann neu starten.

### Variante C: Manuelle Kopie

1. Den Ordner `custom_components/rezeptbuch/` aus dem Repo (inkl. `frontend/` und `brand/`)
   nach `/config/custom_components/rezeptbuch/` kopieren, z. B. per Samba, SSH oder
   Studio Code Server. Nicht kopieren: den Repo-Ordner `frontend/` (Quellcode) und `tests/`.
2. Home Assistant **neu starten**.

### Logging vorab einschalten

In `configuration.yaml` ergänzen (vorhandenen `logger:`-Block erweitern) und neu starten:

```yaml
logger:
  default: warning
  logs:
    custom_components.rezeptbuch: debug
    recipe_scrapers: debug
    homeassistant.components.ai_task: debug
```

## 2. Checkliste

Bei jedem Punkt nebenbei prüfen: kein roter Fehler-Toast im Panel, keine Fehler in
**Einstellungen → System → Protokolle**.

### Einrichtung
- [ ] **Einstellungen → Geräte & Dienste → Integration hinzufügen → Rezeptbuch**,
      „Standard-Kategorien anlegen“ angehakt lassen → Absenden.
- [ ] Integration läuft ohne Fehler; Entitäten vorhanden: Sensoren (u. a. Rezept des Tages)
      und `todo.rezeptbuch_einkaufsliste`.
- [ ] Ordner `/config/rezeptbuch/` wurde angelegt (Datenbank und Bilder).
- [ ] Optionen → **Allgemein**: KI-Entität für den Foto-Import wählen (oder leer lassen,
      wenn unter Einstellungen → KI ein Standard gesetzt ist).

### Panel
- [ ] Seitenleiste zeigt **Rezeptbuch** (Kochmützen-Icon); das Panel öffnet sich ohne weiße Seite.
- [ ] Nach einem harten Neuladen (Strg+F5) öffnet es sich weiterhin.
- [ ] Navigation Rezepte / Entwürfe / Importieren funktioniert, der Zurück-Button des Browsers auch.

### URL-Import (chefkoch.de)
- [ ] **Importieren → URL**: Adresse eines Chefkoch-Rezepts einfügen → **Importieren**.
- [ ] Es öffnet sich ein Entwurf: Titel, Portionen, Zeiten, Zutaten, Schritte und Bild stimmen.
      Kategorievorschlag ist plausibel.
- [ ] **Als Rezept übernehmen** → Rezept erscheint in der Liste mit Bild.
- [ ] Dieselbe URL noch einmal importieren → Hinweis „Schon vorhanden“ und **Vorhandenes öffnen**.

### Foto-Import (ai_task)
- [ ] **Importieren → Foto** → Foto eines **handgeschriebenen Zettels** → **Mit KI auswerten**.
- [ ] Entwurf prüfen: Zutaten mit Mengen und Einheiten, Schritte, Portionen. Fehler im Editor
      korrigieren → **Entwurf speichern** → **Als Rezept übernehmen**.
- [ ] Dasselbe mit einer **Kochbuchseite**, gern als Doppelseite mit 2 Fotos; Reihenfolge
      mit „Nach oben/unten“ testen.
- [ ] Auf dem Tablet/Handy: **Kamera** direkt aus dem Panel nutzen.
- [ ] Bitte notieren: Welche KI (Anbieter/Modell)? Wie lange dauerte die Auswertung?

### Rezept bearbeiten → neue Version + Diff
- [ ] ⚠️ **Noch nicht im Panel (kommt mit Schritt 7b, siehe `PLAN.md`).** Das Backend kann Versionen anlegen, aber das Panel hat
      keinen „Bearbeiten“-Knopf für bestehende Rezepte. Testbar ist nur:
      Rezept öffnen → **Unterschiede zum Original** zeigt „Keine Unterschiede zum Original“.
- [ ] **Notiz hinzufügen** (z. B. „nächstes Mal weniger Salz“) → bleibt nach dem Neuladen erhalten.

### Bewertung
- [ ] Rezept öffnen → **Bewerten**: Sterne, Kommentar, **Heute gekocht** → speichern.
- [ ] Durchschnitt, **Verlauf** und „Zuletzt gekocht“ aktualisieren sich; in der Liste
      Sortierung **Bewertung** bzw. **Zuletzt gekocht** prüfen.
- [ ] Optional mit einem zweiten HA-Benutzer bewerten → Name erscheint in der Bewertungsliste.

### Kategorien
- [ ] Liste nach Kategorie filtern (auch Oberkategorie → Unterkategorien zählen mit).
- [ ] Kategorie einem Rezept zuweisen: im Entwurf vor dem Übernehmen, oder für bestehende
      Rezepte über **Entwicklerwerkzeuge → Aktionen → `rezeptbuch.assign_category`**.
- [ ] ⚠️ **Kategorie verschieben, anlegen, löschen: noch keine Oberfläche im Panel**
      (Backend und WebSocket-Befehl gibt es; kommt mit Schritt 7b). Anlegen geht über `rezeptbuch.create_category`.

### Einkaufsliste
- [ ] Rezept öffnen → Portionen ändern (Mengen werden umgerechnet) → **Auf die Einkaufsliste**.
- [ ] `todo.rezeptbuch_einkaufsliste` enthält die Zutaten; gleiche Zutaten aus zwei Rezepten
      werden zusammengefasst; vage Mengen („etwas Salz“) erscheinen nur einmal.

### Kochmodus auf dem Tablet
- [ ] ⚠️ **Einen eigenen Kochmodus gibt es noch nicht, kommt mit Schritt 7b** (kein Vollbild, keine große
      Schritt-für-Schritt-Ansicht, Bildschirm kann ausgehen). Testbar ist die Rezeptansicht
      auf dem Tablet (auch in der Companion-App):
- [ ] Layout im Hoch- und Querformat lesbar, nichts abgeschnitten.
- [ ] In einem Schritt mit Zeitangabe **Timer** starten → Timer-Leiste erscheint;
      Pause/Weiter/Beenden; nach Ablauf Ton bzw. Hinweis „Fertig: …“.
- [ ] Zwei Timer parallel; Timer laufen weiter, wenn man zur Liste und zurück navigiert.

### Rezept löschen
- [ ] Als **Administrator**: Rezept öffnen → **Rezept löschen** → bestätigen → verschwindet
      aus Liste und Suche.
- [ ] Optional als Nicht-Admin: Löschen wird mit „Administratorrechte nötig“ abgelehnt.

### Abschluss
- [ ] HA neu starten → alle Rezepte, Bewertungen und Bilder sind noch da.
- [ ] Integration **neu laden** (⋮ → Neu laden) → Panel funktioniert danach weiter.

## 3. Was ich bei Fehlern brauche

1. **HA-Log**: Einstellungen → System → Protokolle → **Vollständige Protokolle anzeigen** bzw.
   **Herunterladen**. Mit der Logger-Konfiguration oben steht alles Relevante unter
   `custom_components.rezeptbuch`. Alternativ auf der Integrationsseite
   **Debug-Protokollierung aktivieren**, Fehler auslösen, wieder deaktivieren; dann lädt
   HA die Logdatei automatisch herunter.
2. **Diagnose**: Einstellungen → Geräte & Dienste → Rezeptbuch → ⋮ → **Diagnose herunterladen**
   (enthält keine Rezeptinhalte, nur Zähler und Konfiguration).
3. **Browser-Konsole** bei Panel-Problemen (weiße Seite, Knopf reagiert nicht): F12 →
   Reiter **Konsole**, rote Meldungen kopieren oder Screenshot. Tritt der Fehler nur am
   Tablet auf: Screenshot plus Angabe, ob Companion-App oder Browser.
4. Dazu kurz: **HA-Version**, Installationsart (HA OS / Container / …), Gerät/Browser,
   bei URL-Import die **URL**, bei Foto-Import die **KI** und möglichst das Foto.
