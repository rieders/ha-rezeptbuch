"""Einträge der eigenen Einkaufsliste (todo.rezeptbuch_einkaufsliste).

Das Zusammenfassen von Zutaten (Einheiten umrechnen) passiert in
shopping_list.py; hier liegt nur die Persistenz.
"""

from __future__ import annotations

import json
import sqlite3
from typing import Any
import uuid

from ..models import ValidationError, utcnow_iso
from . import NotFoundError

STATUS_OPEN = "needs_action"
STATUS_DONE = "completed"


def _row(row: sqlite3.Row) -> dict[str, Any]:
    item = dict(row)
    item["sources"] = json.loads(item.get("sources") or "[]")
    return item


def list_items(conn: sqlite3.Connection, status: str | None = None) -> list[dict[str, Any]]:
    """Alle Einträge in Listenreihenfolge."""
    sql = "SELECT * FROM shopping_items"
    params: list[Any] = []
    if status:
        sql += " WHERE status = ?"
        params.append(status)
    return [_row(r) for r in conn.execute(sql + " ORDER BY position, id", params)]


def get_item(conn: sqlite3.Connection, uid: str) -> dict[str, Any]:
    """Ein Eintrag."""
    row = conn.execute("SELECT * FROM shopping_items WHERE uid = ?", (uid,)).fetchone()
    if row is None:
        raise NotFoundError(f"Eintrag {uid} nicht gefunden")
    return _row(row)


def add_item(
    conn: sqlite3.Connection,
    *,
    summary: str,
    name: str | None = None,
    amount: float | None = None,
    amount_max: float | None = None,
    unit: str | None = None,
    note: str | None = None,
    description: str | None = None,
    recipe_id: int | None = None,
    sources: list[dict[str, Any]] | None = None,
    status: str = STATUS_OPEN,
) -> dict[str, Any]:
    """Eintrag anhängen."""
    summary = (summary or "").strip()
    if not summary:
        raise ValidationError("Eintrag darf nicht leer sein")
    now = utcnow_iso()
    position = conn.execute("SELECT COALESCE(MAX(position) + 1, 0) FROM shopping_items").fetchone()[0]
    uid = uuid.uuid4().hex
    conn.execute(
        """
        INSERT INTO shopping_items (uid, name, amount, amount_max, unit, note, summary, description,
                                    status, recipe_id, sources, position, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            uid,
            (name or summary).strip(),
            amount,
            amount_max,
            unit,
            note,
            summary,
            description,
            status,
            recipe_id,
            json.dumps(sources or [], ensure_ascii=False),
            position,
            now,
            now,
        ),
    )
    return get_item(conn, uid)


def update_item(conn: sqlite3.Connection, uid: str, **fields: Any) -> dict[str, Any]:
    """Felder eines Eintrags ändern."""
    allowed = {
        "summary",
        "name",
        "amount",
        "amount_max",
        "unit",
        "note",
        "description",
        "status",
        "sources",
        "recipe_id",
    }
    get_item(conn, uid)
    sets, params = [], []
    for key, value in fields.items():
        if key not in allowed:
            raise ValidationError(f"Unbekanntes Feld: {key}")
        if key == "sources":
            value = json.dumps(value or [], ensure_ascii=False)
        sets.append(f"{key} = ?")
        params.append(value)
    if sets:
        sets.append("updated = ?")
        params.append(utcnow_iso())
        conn.execute(f"UPDATE shopping_items SET {', '.join(sets)} WHERE uid = ?", (*params, uid))
    return get_item(conn, uid)


def delete_items(conn: sqlite3.Connection, uids: list[str]) -> int:
    """Einträge löschen."""
    if not uids:
        return 0
    cur = conn.execute(f"DELETE FROM shopping_items WHERE uid IN ({','.join('?' * len(uids))})", uids)
    return cur.rowcount


def clear_completed(conn: sqlite3.Connection) -> int:
    """Erledigte Einträge entfernen."""
    return conn.execute("DELETE FROM shopping_items WHERE status = ?", (STATUS_DONE,)).rowcount


def move_item(conn: sqlite3.Connection, uid: str, previous_uid: str | None) -> None:
    """Eintrag hinter `previous_uid` (None = an den Anfang) verschieben."""
    order = [r[0] for r in conn.execute("SELECT uid FROM shopping_items ORDER BY position, id")]
    if uid not in order:
        raise NotFoundError(f"Eintrag {uid} nicht gefunden")
    order.remove(uid)
    if previous_uid is None:
        order.insert(0, uid)
    else:
        if previous_uid not in order:
            raise NotFoundError(f"Eintrag {previous_uid} nicht gefunden")
        order.insert(order.index(previous_uid) + 1, uid)
    for pos, item_uid in enumerate(order):
        conn.execute("UPDATE shopping_items SET position = ? WHERE uid = ?", (pos, item_uid))
