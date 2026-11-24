"""Import-Entwürfe: Vorschau/Korrektur vor dem Anlegen eines Rezepts.

data-JSON eines Entwurfs:
    {
      "title", "description", "source_url", "image" (rel. Pfad oder None),
      "version": VersionData-Dict, "category_ids", "tags", "warnings": [...],
      "source": {"categories": [...], "keywords": [...], "matched": {kw: id},
                 "suggested_category_ids": [...], "parser", "site_name", "author",
                 "image_url"}
    }
image_paths: Originalfotos (Foto-Import) → werden source_photo am Rezept.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any

from ..const import IMAGE_SOURCE_PHOTO, SOURCE_TYPES
from ..errors import DraftNotFound, DuplicateRecipe
from ..models import ValidationError, VersionData, utcnow_iso
from .recipes import add_image, create_recipe, find_duplicates


def _row(row: sqlite3.Row) -> dict[str, Any]:
    return {
        "id": row["id"],
        "source_type": row["source_type"],
        "data": json.loads(row["data"]),
        "image_paths": json.loads(row["image_paths"]),
        "user_id": row["user_id"],
        "created": row["created"],
        "updated": row["updated"],
    }


def create_draft(
    conn: sqlite3.Connection,
    source_type: str,
    data: dict[str, Any],
    image_paths: list[str] | None = None,
    user_id: str | None = None,
) -> int:
    """Entwurf speichern."""
    if source_type not in SOURCE_TYPES:
        raise ValidationError(f"Unbekannte Quelle: {source_type}")
    now = utcnow_iso()
    cur = conn.execute(
        "INSERT INTO import_drafts (source_type, data, image_paths, user_id, created, updated) VALUES (?, ?, ?, ?, ?, ?)",
        (
            source_type,
            json.dumps(data, ensure_ascii=False),
            json.dumps(image_paths or [], ensure_ascii=False),
            user_id,
            now,
            now,
        ),
    )
    return int(cur.lastrowid)


def get_draft(conn: sqlite3.Connection, draft_id: int) -> dict[str, Any]:
    """Entwurf lesen."""
    row = conn.execute("SELECT * FROM import_drafts WHERE id = ?", (draft_id,)).fetchone()
    if row is None:
        raise DraftNotFound(f"Entwurf {draft_id} nicht gefunden", draft_id=draft_id)
    return _row(row)


def list_drafts(conn: sqlite3.Connection, user_id: str | None = None) -> list[dict[str, Any]]:
    """Offene Entwürfe (optional nur eines Benutzers)."""
    sql = "SELECT * FROM import_drafts"
    params: list[Any] = []
    if user_id:
        sql += " WHERE user_id = ?"
        params.append(user_id)
    return [_row(r) for r in conn.execute(sql + " ORDER BY created DESC", params)]


def update_draft(
    conn: sqlite3.Connection, draft_id: int, changes: dict[str, Any], image_paths: list[str] | None = None
) -> dict[str, Any]:
    """Felder im Entwurf überschreiben (flaches Merge auf oberster Ebene)."""
    draft = get_draft(conn, draft_id)
    data = {**draft["data"], **changes}
    if "version" in changes:
        data["version"] = VersionData.from_dict(changes["version"]).to_dict()  # validieren
    conn.execute(
        "UPDATE import_drafts SET data = ?, image_paths = ?, updated = ? WHERE id = ?",
        (
            json.dumps(data, ensure_ascii=False),
            json.dumps(image_paths if image_paths is not None else draft["image_paths"], ensure_ascii=False),
            utcnow_iso(),
            draft_id,
        ),
    )
    return get_draft(conn, draft_id)


def delete_draft(conn: sqlite3.Connection, draft_id: int) -> list[str]:
    """Entwurf verwerfen; gibt die nicht mehr benötigten Bildpfade zurück."""
    draft = get_draft(conn, draft_id)
    conn.execute("DELETE FROM import_drafts WHERE id = ?", (draft_id,))
    paths = list(draft["image_paths"])
    if draft["data"].get("image"):
        paths.append(draft["data"]["image"])
    return sorted(set(paths))


def confirm_draft(
    conn: sqlite3.Connection,
    draft_id: int,
    overrides: dict[str, Any] | None = None,
    *,
    user_id: str | None = None,
    allow_duplicate: bool = False,
) -> dict[str, Any]:
    """Entwurf übernehmen: Rezept + Version 1 „Original“ anlegen, Entwurf löschen.

    Gibt {"recipe_id", "learned": bool} zurück. Lernt Kategorie-Korrekturen.
    """
    from ..importer.mapping import learn_from_correction

    draft = get_draft(conn, draft_id)
    data = {**draft["data"], **(overrides or {})}
    if data.get("source_url") and not allow_duplicate:
        dups = find_duplicates(conn, data["source_url"])
        if dups:
            raise DuplicateRecipe(dups[0]["id"], dups[0]["title"])
    allowed_images = set(draft["image_paths"]) | ({draft["data"]["image"]} if draft["data"].get("image") else set())
    if data.get("image") and data["image"] not in allowed_images:
        raise ValidationError("Das Rezeptbild muss eines der Bilder dieses Entwurfs sein")
    category_ids = [int(c) for c in data.get("category_ids") or []]
    recipe_id = create_recipe(
        conn,
        title=data.get("title") or "",
        description=data.get("description"),
        data=VersionData.from_dict(data.get("version")),
        source_url=data.get("source_url"),
        source_type=draft["source_type"],
        image=data.get("image"),
        category_ids=category_ids,
        tags=data.get("tags") or [],
        user_id=user_id or draft["user_id"],
    )
    for path in draft["image_paths"]:
        add_image(conn, recipe_id, path, IMAGE_SOURCE_PHOTO)
    source = data.get("source") or {}
    learn_from_correction(
        conn,
        primary_keywords=source.get("categories") or [],
        matched={k: int(v) for k, v in (source.get("matched") or {}).items()},
        suggested_ids=[int(c) for c in source.get("suggested_category_ids") or []],
        final_ids=category_ids,
    )
    conn.execute("DELETE FROM import_drafts WHERE id = ?", (draft_id,))
    return {"recipe_id": recipe_id}


def delete_drafts_older_than(conn: sqlite3.Connection, cutoff_iso: str) -> tuple[int, list[str]]:
    """Unbestätigte Entwürfe älter als `cutoff_iso` löschen.

    Gibt (Anzahl, nicht mehr benötigte Bildpfade) zurück.
    """
    ids = [r[0] for r in conn.execute("SELECT id FROM import_drafts WHERE updated < ?", (cutoff_iso,))]
    paths: list[str] = []
    for draft_id in ids:
        paths.extend(delete_draft(conn, draft_id))
    return len(ids), sorted(set(paths))


def referenced_image_paths(conn: sqlite3.Connection) -> set[str]:
    """Alle Bildpfade, auf die die Datenbank verweist (Rezepte, Kochprotokoll, Entwürfe)."""
    paths: set[str] = set()
    for sql in (
        "SELECT image FROM recipes WHERE image IS NOT NULL",
        "SELECT path FROM recipe_images",
        "SELECT photo FROM cook_log WHERE photo IS NOT NULL",
    ):
        paths.update(r[0] for r in conn.execute(sql))
    for data, image_paths in conn.execute("SELECT data, image_paths FROM import_drafts"):
        paths.update(json.loads(image_paths or "[]"))
        image = json.loads(data).get("image")
        if image:
            paths.add(image)
    return paths
