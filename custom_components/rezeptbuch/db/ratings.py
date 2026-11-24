"""Bewertungen und Kochprotokoll (cook_log), getrennt pro HA-Benutzer."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..const import SYSTEM_USER_ID
from ..models import ValidationError, utcnow_iso, validate_stars
from . import NotFoundError
from .recipes import _require_recipe, touch


def _user(user_id: str | None) -> str:
    return user_id or SYSTEM_USER_ID


def add_cook_log(
    conn: sqlite3.Connection,
    recipe_id: int,
    *,
    stars: float | None = None,
    comment: str | None = None,
    cooked: bool = True,
    cooked_at: str | None = None,
    servings: float | None = None,
    version_id: int | None = None,
    photo: str | None = None,
    user_id: str | None = None,
    created: str | None = None,
) -> int:
    """Kochvorgang und/oder Bewertung speichern.

    cooked=False → reine Bewertung ohne Kochen (cooked_at bleibt NULL).
    Ohne Sterne und ohne Kochen ergibt der Eintrag keinen Sinn.
    """
    _require_recipe(conn, recipe_id)
    stars = validate_stars(stars)
    comment = (comment or "").strip() or None
    if not cooked and stars is None and comment is None:
        raise ValidationError("Bitte Sterne oder einen Kommentar angeben")
    if version_id is None:
        version_id = conn.execute("SELECT default_version_id FROM recipes WHERE id = ?", (recipe_id,)).fetchone()[0]
    elif (
        conn.execute("SELECT 1 FROM recipe_versions WHERE id = ? AND recipe_id = ?", (version_id, recipe_id)).fetchone()
        is None
    ):
        raise ValidationError("Version gehört nicht zu diesem Rezept")
    now = utcnow_iso()
    cur = conn.execute(
        """
        INSERT INTO cook_log (recipe_id, version_id, cooked_at, stars, comment, servings, photo, user_id, created)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            recipe_id,
            version_id,
            (cooked_at or now) if cooked else None,
            stars,
            comment,
            servings,
            photo,
            _user(user_id),
            created or now,
        ),
    )
    touch(conn, recipe_id)
    return int(cur.lastrowid)


def update_cook_log(
    conn: sqlite3.Connection,
    entry_id: int,
    *,
    stars: float | None = None,
    comment: str | None = None,
    photo: str | None = None,
    clear_stars: bool = False,
) -> None:
    """Eintrag ändern (None = unverändert)."""
    if conn.execute("SELECT 1 FROM cook_log WHERE id = ?", (entry_id,)).fetchone() is None:
        raise NotFoundError(f"Eintrag {entry_id} nicht gefunden")
    if clear_stars:
        conn.execute("UPDATE cook_log SET stars = NULL WHERE id = ?", (entry_id,))
    elif stars is not None:
        conn.execute("UPDATE cook_log SET stars = ? WHERE id = ?", (validate_stars(stars), entry_id))
    if comment is not None:
        conn.execute("UPDATE cook_log SET comment = ? WHERE id = ?", (comment.strip() or None, entry_id))
    if photo is not None:
        conn.execute("UPDATE cook_log SET photo = ? WHERE id = ?", (photo or None, entry_id))


def get_cook_log(conn: sqlite3.Connection, entry_id: int) -> dict[str, Any]:
    """Ein Eintrag."""
    row = conn.execute("SELECT * FROM cook_log WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Eintrag {entry_id} nicht gefunden")
    return dict(row)


def delete_cook_log(conn: sqlite3.Connection, entry_id: int) -> str | None:
    """Eintrag löschen; gibt ggf. den Foto-Pfad zurück."""
    row = conn.execute("SELECT photo FROM cook_log WHERE id = ?", (entry_id,)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM cook_log WHERE id = ?", (entry_id,))
    return row[0]


def history(conn: sqlite3.Connection, recipe_id: int, limit: int | None = None) -> list[dict[str, Any]]:
    """Verlauf, neueste zuerst (gekocht oder bewertet)."""
    sql = """
        SELECT c.*, v.label AS version_label FROM cook_log c
        LEFT JOIN recipe_versions v ON v.id = c.version_id
        WHERE c.recipe_id = ? ORDER BY COALESCE(c.cooked_at, c.created) DESC, c.id DESC
    """
    params: list[Any] = [recipe_id]
    if limit:
        sql += " LIMIT ?"
        params.append(limit)
    return [dict(r) for r in conn.execute(sql, params)]


def recipe_stats(conn: sqlite3.Connection, recipe_id: int) -> dict[str, Any]:
    """Durchschnitt, Anzahl, zuletzt gekocht, letzte Bewertung, je Benutzer."""
    row = conn.execute(
        """
        SELECT AVG(stars) AS avg_stars, COUNT(stars) AS rating_count,
               SUM(cooked_at IS NOT NULL) AS cooked_count, MAX(cooked_at) AS last_cooked
        FROM cook_log WHERE recipe_id = ?
        """,
        (recipe_id,),
    ).fetchone()
    last = conn.execute(
        """
        SELECT stars, comment, user_id, COALESCE(cooked_at, created) AS at FROM cook_log
        WHERE recipe_id = ? AND stars IS NOT NULL
        ORDER BY COALESCE(cooked_at, created) DESC, id DESC LIMIT 1
        """,
        (recipe_id,),
    ).fetchone()
    per_user = [
        {
            "user_id": r["user_id"],
            "avg_stars": round(r["avg_stars"], 2) if r["avg_stars"] is not None else None,
            "rating_count": r["rating_count"],
            "cooked_count": r["cooked_count"] or 0,
            "last_cooked": r["last_cooked"],
        }
        for r in conn.execute(
            """
            SELECT COALESCE(user_id, ?) AS user_id, AVG(stars) AS avg_stars, COUNT(stars) AS rating_count,
                   SUM(cooked_at IS NOT NULL) AS cooked_count, MAX(cooked_at) AS last_cooked
            FROM cook_log WHERE recipe_id = ? GROUP BY COALESCE(user_id, ?) ORDER BY user_id
            """,
            (SYSTEM_USER_ID, recipe_id, SYSTEM_USER_ID),
        )
    ]
    return {
        "avg_stars": round(row["avg_stars"], 2) if row["avg_stars"] is not None else None,
        "rating_count": row["rating_count"] or 0,
        "cooked_count": row["cooked_count"] or 0,
        "last_cooked": row["last_cooked"],
        "last_rating": dict(last) if last else None,
        "per_user": per_user,
    }


def all_stats(conn: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    """Kurzstatistik für alle Rezepte (für Rezept des Tages)."""
    return {
        r["recipe_id"]: {
            "avg_stars": r["avg_stars"],
            "rating_count": r["rating_count"],
            "cooked_count": r["cooked_count"] or 0,
            "last_cooked": r["last_cooked"],
        }
        for r in conn.execute(
            """
            SELECT recipe_id, AVG(stars) AS avg_stars, COUNT(stars) AS rating_count,
                   SUM(cooked_at IS NOT NULL) AS cooked_count, MAX(cooked_at) AS last_cooked
            FROM cook_log GROUP BY recipe_id
            """
        )
    }
