"""Rezeptversionen (Original bleibt unverändert) und Inline-Notizen."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..const import ANNOTATION_TARGETS, DEFAULT_VERSION_LABEL, SYSTEM_USER_ID, TARGET_RECIPE
from ..diff import diff_versions
from ..models import ValidationError, VersionData, utcnow_iso
from . import ConflictError, NotFoundError
from .recipes import _require_recipe, sync_from_default_version, touch


def _row_to_version(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["is_original"] = bool(item["is_original"])
    item["data"] = VersionData.from_json(item["data"]).to_dict()
    return item


def get_version(conn: sqlite3.Connection, version_id: int) -> dict[str, Any]:
    """Eine Version inkl. Daten."""
    row = conn.execute("SELECT * FROM recipe_versions WHERE id = ?", (version_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Version {version_id} nicht gefunden")
    return _row_to_version(row)


def get_version_data(conn: sqlite3.Connection, version_id: int) -> VersionData:
    """Nur die Daten einer Version."""
    row = conn.execute("SELECT data FROM recipe_versions WHERE id = ?", (version_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Version {version_id} nicht gefunden")
    return VersionData.from_json(row[0])


def list_versions(conn: sqlite3.Connection, recipe_id: int) -> list[dict[str, Any]]:
    """Alle Versionen (ohne Daten), Original zuerst, dann neueste zuerst."""
    default_id = conn.execute("SELECT default_version_id FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    default_id = default_id[0] if default_id else None
    rows = conn.execute(
        """
        SELECT id, recipe_id, version_no, label, is_original, change_note, cook_log_id, user_id, created
        FROM recipe_versions WHERE recipe_id = ?
        ORDER BY is_original DESC, version_no DESC
        """,
        (recipe_id,),
    ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["is_original"] = bool(item["is_original"])
        item["is_default"] = item["id"] == default_id
        result.append(item)
    return result


def original_version_id(conn: sqlite3.Connection, recipe_id: int) -> int:
    """ID der Originalversion."""
    row = conn.execute(
        "SELECT id FROM recipe_versions WHERE recipe_id = ? AND is_original = 1", (recipe_id,)
    ).fetchone()
    if row is None:
        raise NotFoundError(f"Rezept {recipe_id} hat keine Originalversion")
    return row[0]


def create_version(
    conn: sqlite3.Connection,
    recipe_id: int,
    data: VersionData | dict[str, Any],
    *,
    label: str | None = None,
    change_note: str | None = None,
    cook_log_id: int | None = None,
    user_id: str | None = None,
    make_default: bool = True,
    is_original: bool = False,
    created: str | None = None,
) -> int:
    """Neue Version anlegen (Bearbeiten erzeugt immer eine neue Version).

    `is_original=True` ist nur für den Backup-Import gedacht und nur möglich,
    solange das Rezept noch kein Original hat.
    """
    _require_recipe(conn, recipe_id)
    vdata = data if isinstance(data, VersionData) else VersionData.from_dict(data)
    if (
        cook_log_id is not None
        and conn.execute("SELECT 1 FROM cook_log WHERE id = ? AND recipe_id = ?", (cook_log_id, recipe_id)).fetchone()
        is None
    ):
        raise ValidationError("Kochvorgang gehört nicht zu diesem Rezept")
    version_no = conn.execute(
        "SELECT COALESCE(MAX(version_no), 0) + 1 FROM recipe_versions WHERE recipe_id = ?", (recipe_id,)
    ).fetchone()[0]
    label = (label or "").strip() or (DEFAULT_VERSION_LABEL if version_no == 2 else f"Version {version_no}")
    try:
        cur = conn.execute(
            """
            INSERT INTO recipe_versions (recipe_id, version_no, label, data, is_original, change_note,
                                         cook_log_id, user_id, created)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                recipe_id,
                version_no,
                label,
                vdata.to_json(),
                1 if is_original else 0,
                (change_note or "").strip() or None,
                cook_log_id,
                user_id or SYSTEM_USER_ID,
                created or utcnow_iso(),
            ),
        )
    except sqlite3.IntegrityError as err:
        raise ConflictError("Rezept hat bereits eine Originalversion") from err
    version_id = int(cur.lastrowid)
    if make_default:
        set_default_version(conn, recipe_id, version_id)
    else:
        touch(conn, recipe_id)
    return version_id


def update_version(
    conn: sqlite3.Connection,
    version_id: int,
    *,
    data: VersionData | dict[str, Any] | None = None,
    label: str | None = None,
    change_note: str | None = None,
) -> None:
    """Eigene (nicht originale) Version nachträglich korrigieren."""
    version = get_version(conn, version_id)
    if version["is_original"]:
        raise ConflictError("Die Originalversion kann nicht verändert werden – bitte eine neue Version anlegen")
    if data is not None:
        vdata = data if isinstance(data, VersionData) else VersionData.from_dict(data)
        conn.execute("UPDATE recipe_versions SET data = ? WHERE id = ?", (vdata.to_json(), version_id))
    if label is not None:
        if not label.strip():
            raise ValidationError("Versionsname darf nicht leer sein")
        conn.execute("UPDATE recipe_versions SET label = ? WHERE id = ?", (label.strip(), version_id))
    if change_note is not None:
        conn.execute(
            "UPDATE recipe_versions SET change_note = ? WHERE id = ?", (change_note.strip() or None, version_id)
        )
    sync_from_default_version(conn, version["recipe_id"])


def delete_version(conn: sqlite3.Connection, version_id: int) -> None:
    """Eigene Version löschen; war sie Standard, wird das Original Standard."""
    version = get_version(conn, version_id)
    if version["is_original"]:
        raise ConflictError("Die Originalversion kann nicht gelöscht werden")
    recipe_id = version["recipe_id"]
    default_id = conn.execute("SELECT default_version_id FROM recipes WHERE id = ?", (recipe_id,)).fetchone()[0]
    if default_id == version_id:
        conn.execute(
            "UPDATE recipes SET default_version_id = ? WHERE id = ?",
            (original_version_id(conn, recipe_id), recipe_id),
        )
    conn.execute("DELETE FROM recipe_versions WHERE id = ?", (version_id,))
    sync_from_default_version(conn, recipe_id)


def set_default_version(conn: sqlite3.Connection, recipe_id: int, version_id: int) -> None:
    """Version als Standard (Liste, Kochmodus, Einkaufsliste) markieren."""
    row = conn.execute("SELECT recipe_id FROM recipe_versions WHERE id = ?", (version_id,)).fetchone()
    if row is None or row[0] != recipe_id:
        raise NotFoundError(f"Version {version_id} gehört nicht zu Rezept {recipe_id}")
    conn.execute("UPDATE recipes SET default_version_id = ? WHERE id = ?", (version_id, recipe_id))
    sync_from_default_version(conn, recipe_id)


def reset_to_original(conn: sqlite3.Connection, recipe_id: int) -> int:
    """Original wieder als Standard setzen (eigene Versionen bleiben erhalten)."""
    vid = original_version_id(conn, recipe_id)
    set_default_version(conn, recipe_id, vid)
    return vid


def diff(conn: sqlite3.Connection, old_version_id: int, new_version_id: int) -> dict[str, Any]:
    """Diff zwischen zwei Versionen desselben Rezepts."""
    old = get_version(conn, old_version_id)
    new = get_version(conn, new_version_id)
    if old["recipe_id"] != new["recipe_id"]:
        raise ValidationError("Versionen gehören zu unterschiedlichen Rezepten")
    result = diff_versions(VersionData.from_dict(old["data"]), VersionData.from_dict(new["data"]))
    result["old_version_id"] = old_version_id
    result["new_version_id"] = new_version_id
    return result


# ---------------------------------------------------------------------------
# Inline-Notizen (ohne neue Version)
# ---------------------------------------------------------------------------


def add_annotation(
    conn: sqlite3.Connection,
    recipe_id: int,
    *,
    text: str,
    target_type: str = TARGET_RECIPE,
    target_index: int | None = None,
    version_id: int | None = None,
    user_id: str | None = None,
    created: str | None = None,
) -> int:
    """Notiz an Rezept, Zutat oder Schritt einer Version hängen."""
    _require_recipe(conn, recipe_id)
    text = (text or "").strip()
    if not text:
        raise ValidationError("Notiz darf nicht leer sein")
    if target_type not in ANNOTATION_TARGETS:
        raise ValidationError(f"Ungültiges Ziel: {target_type}")
    if target_type != TARGET_RECIPE:
        if version_id is None or target_index is None:
            raise ValidationError("Für Zutat/Schritt sind Version und Index nötig")
        version = get_version(conn, version_id)
        if version["recipe_id"] != recipe_id:
            raise ValidationError("Version gehört nicht zu diesem Rezept")
        items = version["data"]["ingredients" if target_type == "ingredient" else "steps"]
        if not 0 <= target_index < len(items):
            raise ValidationError("Index außerhalb der Liste")
    elif version_id is not None:
        get_version(conn, version_id)
    cur = conn.execute(
        """
        INSERT INTO annotations (recipe_id, version_id, target_type, target_index, text, user_id, created)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            recipe_id,
            version_id,
            target_type,
            target_index if target_type != TARGET_RECIPE else None,
            text,
            user_id or SYSTEM_USER_ID,
            created or utcnow_iso(),
        ),
    )
    return int(cur.lastrowid)


def update_annotation(conn: sqlite3.Connection, annotation_id: int, text: str) -> None:
    """Notiztext ändern."""
    if not (text or "").strip():
        raise ValidationError("Notiz darf nicht leer sein")
    cur = conn.execute("UPDATE annotations SET text = ? WHERE id = ?", (text.strip(), annotation_id))
    if cur.rowcount == 0:
        raise NotFoundError(f"Notiz {annotation_id} nicht gefunden")


def delete_annotation(conn: sqlite3.Connection, annotation_id: int) -> None:
    """Notiz löschen."""
    conn.execute("DELETE FROM annotations WHERE id = ?", (annotation_id,))


def list_annotations(conn: sqlite3.Connection, recipe_id: int, version_id: int | None = None) -> list[dict[str, Any]]:
    """Notizen eines Rezepts; mit version_id: die dieser Version + versionsunabhängige."""
    if version_id is None:
        rows = conn.execute("SELECT * FROM annotations WHERE recipe_id = ? ORDER BY created", (recipe_id,))
    else:
        rows = conn.execute(
            "SELECT * FROM annotations WHERE recipe_id = ? AND (version_id = ? OR version_id IS NULL) ORDER BY created",
            (recipe_id, version_id),
        )
    return [dict(r) for r in rows]
