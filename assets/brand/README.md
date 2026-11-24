# Rezeptbuch-Icon

`icon.svg` ist die Quelle (eigene Grafik: aufgeschlagenes Buch mit Kochmütze, MIT-Lizenz).

Home Assistant zeigt ab **2026.3** die Bilder aus
`custom_components/rezeptbuch/brand/` an (Vorrang vor dem Brands-CDN, keine weitere
Konfiguration). Ältere Versionen zeigen dort nur einen Platzhalter; das
`home-assistant/brands`-Repository nimmt keine neuen Custom Integrations mehr an.

| Datei | Größe |
|---|---|
| `brand/icon.png` | 256 × 256 |
| `brand/icon@2x.png` | 512 × 512 |

Ein eigenes `logo.png` ist nicht nötig – Home Assistant nutzt das Icon als Ersatz.
Das Icon hat einen eigenen Hintergrund und funktioniert hell wie dunkel, daher keine
`dark_*`-Varianten.

## Neu rendern

```bash
npm install --prefix /tmp/resvg @resvg/resvg-js@2.6.2
RESVG_FROM=/tmp/resvg node assets/brand/render.mjs
```
