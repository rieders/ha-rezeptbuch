"""Rezept-Import per Foto über ai_task.generate_data.

Ablauf (async_import_photos):
1. ai_task-Entität bestimmen (Option → HA-Standard → einzige vorhandene)
2. Fotos prüfen und lokal speichern (Originale, gedreht/max. 2400 px)
3. Verkleinerte Kopien (max. 1600 px, JPEG) für die KI erzeugen
4. ai_task.generate_data mit Anhängen (media-source://rezeptbuch/…) und einer
   Struktur, die nur ROHTEXT verlangt (Zutatenzeilen, Schritte, Zeiten als Text)
5. Zutatenzeilen → eigener ingredient_parser, Schritte → Timer-Erkennung
   (dieselbe Verarbeitung wie beim URL-Import)
6. Entwurf (source_type "photo", ohne source_url) mit Warnungen speichern

Die KI-Kopien werden danach immer gelöscht. Bei einem Fehler im KI-Aufruf
werden auch die gespeicherten Originale wieder entfernt.
"""

from __future__ import annotations

from io import BytesIO
import json
import logging
import re
from typing import Any

from homeassistant.core import HomeAssistant
from PIL import Image, ImageOps

from ..const import SOURCE_PHOTO
from ..db import Database
from ..db.drafts import create_draft, get_draft
from ..db.recipes import find_similar_titles
from ..errors import AiTaskEntityNotFound, AiTaskFailed, NoAiTaskEntity, NoPhotos
from ..images import async_delete_images, async_store_image
from ..ingredient_parser import UNREADABLE, parse_ingredient_lines
from ..media_source import media_source_uri
from ..models import Step, VersionData
from ..storage import Storage
from ..timers import detect_timer_seconds, parse_minutes_text
from .jsonld import parse_yield
from .mapping import map_keywords, split_keywords
from .url import WARN_NO_INGREDIENTS, WARN_NO_SERVINGS, WARN_NO_STEPS

_LOGGER = logging.getLogger(__name__)

AI_TASK_DOMAIN = "ai_task"
AI_MAX_DIMENSION = 1600
AI_JPEG_QUALITY = 82
MAX_PHOTOS = 10
TASK_NAME = "Rezeptbuch: Rezept von Foto erfassen"

WARN_NOTHING_RECOGNIZED = "Die KI hat auf den Fotos kein Rezept erkannt – bitte manuell erfassen oder verwerfen."
WARN_NO_TITLE = "Kein Titel erkannt."
WARN_BAD_RESPONSE = "Die Antwort der KI war unvollständig oder unbrauchbar."

INSTRUCTIONS = """\
Du bekommst {count} Foto(s) von EINEM Rezept, in der richtigen Reihenfolge \
(z. B. mehrere Seiten eines Kochbuchs, eine Doppelseite oder eine handgeschriebene Karteikarte).

Lies den gedruckten UND den handgeschriebenen Text und gib das Rezept als Rohtext zurück:
- Gib nur wieder, was tatsächlich auf den Fotos steht. Erfinde nichts: keine Mengen, \
Zutaten, Schritte, Zeiten oder Portionen ergänzen, nichts umrechnen, nichts übersetzen.
- Zutaten: jede Zutatenzeile wörtlich als eigenen Eintrag, Menge, Einheit und Zutat \
zusammen in EINER Zeile (z. B. "200 g Mehl", "1/2 TL Salz", "1 Pck. Backpulver"). \
Mengen und Einheiten NICHT zerlegen.
- Gruppenüberschriften der Zutaten (z. B. "Für den Teig:") als eigene Zeile mit Doppelpunkt am Ende.
- Schritte: jeder Zubereitungsschritt als eigener Eintrag, ohne Nummerierung.
- Zeiten und Portionen so, wie sie dastehen (z. B. "20 Min.", "1 Std. 30 Min.", "4 Portionen", \
"1 Springform (26 cm)").
- Unleserliche Stellen durch [unleserlich] ersetzen – nicht raten.
- Fehlt eine Angabe, das Feld leer lassen.
- category: Art des Gerichts in 1–3 Wörtern (z. B. "Kuchen", "Suppe", "Cocktail"), nur wenn erkennbar.
"""

STRUCTURE: dict[str, Any] = {
    "title": {"description": "Titel des Rezepts, wörtlich", "selector": {"text": None}},
    "servings": {
        "description": "Portionen/Ausbeute wörtlich, z. B. '4 Portionen' oder '12 Stück'",
        "selector": {"text": None},
    },
    "prep_time": {"description": "Vorbereitungszeit wörtlich, z. B. '20 Min.'", "selector": {"text": None}},
    "cook_time": {"description": "Koch-/Backzeit wörtlich", "selector": {"text": None}},
    "total_time": {"description": "Gesamtzeit wörtlich", "selector": {"text": None}},
    "ingredients": {
        "description": "Zutatenzeilen wörtlich, eine pro Eintrag; Gruppenüberschriften als eigene Zeile mit ':'",
        "selector": {"text": {"multiple": True}},
    },
    "steps": {
        "description": "Zubereitungsschritte wörtlich, einer pro Eintrag, ohne Nummerierung",
        "selector": {"text": {"multiple": True}},
    },
    "category": {"description": "Art des Gerichts in 1–3 Wörtern", "selector": {"text": None}},
}


# ---------------------------------------------------------------------------
# ai_task-Entität
# ---------------------------------------------------------------------------


def _preferred_entity(hass: HomeAssistant) -> str | None:
    """Von HA als Standard gesetzte ai_task-Entität (Einstellungen → KI)."""
    try:
        from homeassistant.components.ai_task.const import DATA_PREFERENCES
    except ImportError:
        return None
    prefs = hass.data.get(DATA_PREFERENCES)
    return getattr(prefs, "gen_data_entity_id", None)


def resolve_ai_task_entity(hass: HomeAssistant, configured: str | None) -> str:
    """Zu verwendende ai_task-Entität bestimmen oder verständlich scheitern."""
    if not hass.services.has_service(AI_TASK_DOMAIN, "generate_data"):
        raise NoAiTaskEntity("Für den Foto-Import wird eine KI-Aufgabe (ai_task) benötigt – es ist keine eingerichtet.")
    if configured:
        if hass.states.get(configured) is None:
            raise AiTaskEntityNotFound(
                f"Die ausgewählte KI-Entität {configured} gibt es nicht (mehr).", entity_id=configured
            )
        return configured
    preferred = _preferred_entity(hass)
    if preferred and hass.states.get(preferred) is not None:
        return preferred
    entities = sorted(hass.states.async_entity_ids(AI_TASK_DOMAIN))
    if len(entities) == 1:
        return entities[0]
    if not entities:
        raise NoAiTaskEntity("Für den Foto-Import wird eine KI-Aufgabe (ai_task) benötigt – es ist keine eingerichtet.")
    raise NoAiTaskEntity(
        "Es gibt mehrere KI-Entitäten, aber keine Standard-Entität. "
        "Bitte in den Rezeptbuch-Optionen oder unter Einstellungen → KI eine auswählen.",
        count=len(entities),
    )


# ---------------------------------------------------------------------------
# Bilder für die KI
# ---------------------------------------------------------------------------


def make_ai_copy(data: bytes) -> bytes:
    """Verkleinerte JPEG-Kopie (max. 1600 px) für die KI. Blockierend (Executor)."""
    with Image.open(BytesIO(data)) as img:
        img = ImageOps.exif_transpose(img)
        img.thumbnail((AI_MAX_DIMENSION, AI_MAX_DIMENSION), Image.Resampling.LANCZOS)
        out = BytesIO()
        img.convert("RGB").save(out, format="JPEG", quality=AI_JPEG_QUALITY, optimize=True)
        return out.getvalue()


async def _async_make_ai_copies(hass: HomeAssistant, storage: Storage, originals: list[str]) -> list[str]:
    def _run() -> list[str]:
        copies: list[str] = []
        for rel in originals:
            copy = make_ai_copy(storage.image_path(rel).read_bytes())
            copies.append(storage.write_image(copy, "jpg"))
        return copies

    return await hass.async_add_executor_job(_run)


# ---------------------------------------------------------------------------
# Antwort auswerten
# ---------------------------------------------------------------------------


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, dict):  # KI hat doch zerlegt → wieder zusammensetzen
        return " ".join(str(v) for v in value.values() if v not in (None, ""))
    return " ".join(str(value).split())


def _as_lines(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        items: list[Any] = value.splitlines()
    elif isinstance(value, list):
        items = value
    else:
        items = [value]
    return [line for line in (_as_text(v) for v in items) if line]


def _strip_numbering(text: str) -> str:
    return re.sub(r"^\s*(?:\d{1,2}[.)]|[-•*])\s+", "", text).strip()


def _count_unreadable(*texts: str) -> int:
    return sum(t.lower().count(UNREADABLE) for t in texts)


def parse_ai_result(data: Any) -> tuple[dict[str, Any], list[str]]:
    """KI-Rohdaten → (Entwurfsfelder, Warnungen). Wirft nie."""
    warnings: list[str] = []
    if isinstance(data, str):
        try:
            data = json.loads(data)
        except ValueError:
            data = None
    if not isinstance(data, dict):
        warnings.append(WARN_BAD_RESPONSE)
        data = {}

    title = _as_text(data.get("title"))
    servings_text = _as_text(data.get("servings"))
    times = {k: _as_text(data.get(k)) for k in ("prep_time", "cook_time", "total_time")}
    ingredient_lines = _as_lines(data.get("ingredients"))
    step_lines = [_strip_numbering(s) for s in _as_lines(data.get("steps"))]
    step_lines = [s for s in step_lines if s]
    category = _as_text(data.get("category"))

    ingredients = parse_ingredient_lines(ingredient_lines)
    steps = [Step(text=s, timer_seconds=detect_timer_seconds(s)) for s in step_lines]
    servings, servings_unit = parse_yield(servings_text) if servings_text else (None, None)
    version = VersionData(
        servings=servings,
        servings_unit=servings_unit,
        prep_time=parse_minutes_text(times["prep_time"]),
        cook_time=parse_minutes_text(times["cook_time"]),
        total_time=parse_minutes_text(times["total_time"]),
        ingredients=ingredients,
        steps=steps,
    )
    if version.total_time is None and (version.prep_time or version.cook_time):
        version.total_time = (version.prep_time or 0) + (version.cook_time or 0)

    if not title and not ingredients and not steps:
        warnings.append(WARN_NOTHING_RECOGNIZED)
    else:
        if not title:
            warnings.append(WARN_NO_TITLE)
        if not ingredients:
            warnings.append(WARN_NO_INGREDIENTS)
        if not steps:
            warnings.append(WARN_NO_STEPS)
        if not servings:
            warnings.append(WARN_NO_SERVINGS)
    unreadable = _count_unreadable(title, servings_text, *times.values(), *ingredient_lines, *step_lines)
    if unreadable:
        warnings.append(
            f"{unreadable} unleserliche Stelle{'n' if unreadable != 1 else ''} markiert ({UNREADABLE}) – bitte prüfen."
        )
    fields = {
        "title": title,
        "version": version,
        "category": category,
        "unreadable": unreadable,
    }
    return fields, warnings


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


async def async_import_photos(
    hass: HomeAssistant,
    db: Database,
    storage: Storage,
    photos: list[bytes],
    *,
    user_id: str | None = None,
    ai_task_entity: str | None = None,
    category_ids: list[int] | None = None,
    tags: list[str] | None = None,
) -> dict[str, Any]:
    """Fotos (Seitenreihenfolge = Listenreihenfolge) → Entwurf.

    Rückgabe: {"status": "draft", "draft_id", "draft", "warnings"}
    Fehler: NoPhotos, NoAiTaskEntity, AiTaskEntityNotFound, InvalidImage, AiTaskFailed.
    """
    if not photos:
        raise NoPhotos("Bitte mindestens ein Foto auswählen.")
    if len(photos) > MAX_PHOTOS:
        raise NoPhotos(f"Höchstens {MAX_PHOTOS} Fotos pro Rezept.", limit=MAX_PHOTOS)
    entity_id = resolve_ai_task_entity(hass, ai_task_entity)  # vor dem Speichern prüfen

    originals: list[str] = []
    try:
        for data in photos:
            originals.append(await async_store_image(hass, storage, data))
    except Exception:
        await async_delete_images(hass, storage, originals)
        raise

    ai_copies: list[str] = []
    try:
        ai_copies = await _async_make_ai_copies(hass, storage, originals)
        response = await hass.services.async_call(
            AI_TASK_DOMAIN,
            "generate_data",
            {
                "task_name": TASK_NAME,
                "entity_id": entity_id,
                "instructions": INSTRUCTIONS.format(count=len(originals)),
                "structure": STRUCTURE,
                "attachments": [
                    {"media_content_id": media_source_uri(rel), "media_content_type": "image/jpeg"} for rel in ai_copies
                ],
            },
            blocking=True,
            return_response=True,
        )
    except Exception as err:
        _LOGGER.warning("Rezeptbuch: KI-Auswertung der Fotos fehlgeschlagen: %s", err)
        await async_delete_images(hass, storage, originals)
        raise AiTaskFailed(f"Die KI-Auswertung ist fehlgeschlagen: {err}", reason=str(err)) from err
    finally:
        await async_delete_images(hass, storage, ai_copies)

    result_data = response.get("data") if isinstance(response, dict) else None
    fields, warnings = parse_ai_result(result_data)

    def _save(conn) -> int:
        mapping = map_keywords(conn, split_keywords([fields["category"]]) if fields["category"] else [], [])
        final_ids = list(dict.fromkeys([*mapping.category_ids, *(category_ids or [])]))
        final_tags = list(dict.fromkeys([*mapping.tags, *(tags or [])]))
        similar = find_similar_titles(conn, fields["title"]) if fields["title"] else []
        draft_warnings = list(warnings)
        for item in similar:
            draft_warnings.append(f"Ähnliches Rezept bereits vorhanden: „{item['title']}“ (ID {item['id']}).")
        draft = {
            "title": fields["title"],
            "description": None,
            "source_url": None,
            "image": None,  # Rezeptbild kann aus image_choices gewählt werden
            "image_choices": originals,
            "version": fields["version"].to_dict(),
            "category_ids": final_ids,
            "tags": final_tags,
            "warnings": draft_warnings,
            "similar_recipes": similar,
            "source": {
                "categories": mapping.primary_keywords,
                "keywords": [],
                "matched": mapping.matched,
                "suggested_category_ids": final_ids,
                "parser": "ai_task",
                "ai_task_entity": entity_id,
                "unreadable": fields["unreadable"],
            },
        }
        return create_draft(conn, SOURCE_PHOTO, draft, image_paths=originals, user_id=user_id)

    try:
        draft_id = await db.run(_save)
    except Exception:
        await async_delete_images(hass, storage, originals)
        raise
    draft = await db.run(get_draft, draft_id)
    return {"status": "draft", "draft_id": draft_id, "draft": draft, "warnings": draft["data"]["warnings"]}
