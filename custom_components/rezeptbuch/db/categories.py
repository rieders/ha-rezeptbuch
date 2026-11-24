"""Hierarchische Kategorien: Baum, Verschieben, Zyklusschutz, Löschen, Zählung."""

from __future__ import annotations

import sqlite3
from typing import Any

from ..const import DEFAULT_CATEGORY_TREE
from ..models import ValidationError, utcnow_iso
from . import ConflictError, NotFoundError

UNCATEGORIZED_ID = 0  # virtueller Knoten "Ohne Kategorie"


def _require(conn: sqlite3.Connection, category_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Kategorie {category_id} nicht gefunden")
    return dict(row)


def get_category(conn: sqlite3.Connection, category_id: int) -> dict[str, Any]:
    """Eine Kategorie."""
    return _require(conn, category_id)


def _next_position(conn: sqlite3.Connection, parent_id: int | None) -> int:
    row = conn.execute(
        "SELECT COALESCE(MAX(position) + 1, 0) FROM categories WHERE parent_id IS ?",
        (parent_id,),
    ).fetchone()
    return int(row[0])


def _check_name(conn: sqlite3.Connection, name: str, parent_id: int | None, exclude: int | None) -> str:
    name = (name or "").strip()
    if not name:
        raise ValidationError("Kategoriename darf nicht leer sein")
    row = conn.execute(
        "SELECT id FROM categories WHERE parent_id IS ? AND name = ? COLLATE NOCASE AND id IS NOT ?",
        (parent_id, name, exclude),
    ).fetchone()
    if row is not None:
        raise ConflictError(f"Kategorie „{name}“ existiert hier bereits")
    return name


def create_category(
    conn: sqlite3.Connection,
    name: str,
    parent_id: int | None = None,
    icon: str | None = None,
    color: str | None = None,
    position: int | None = None,
) -> int:
    """Kategorie anlegen. Gibt die ID zurück."""
    if parent_id is not None:
        _require(conn, parent_id)
    name = _check_name(conn, name, parent_id, None)
    if position is None:
        position = _next_position(conn, parent_id)
    else:
        conn.execute(
            "UPDATE categories SET position = position + 1 WHERE parent_id IS ? AND position >= ?",
            (parent_id, position),
        )
    cur = conn.execute(
        "INSERT INTO categories (parent_id, name, icon, color, position, created) VALUES (?, ?, ?, ?, ?, ?)",
        (parent_id, name, icon or None, color or None, position, utcnow_iso()),
    )
    return int(cur.lastrowid)


def update_category(
    conn: sqlite3.Connection,
    category_id: int,
    *,
    name: str | None = None,
    icon: str | None = None,
    color: str | None = None,
) -> None:
    """Name/Icon/Farbe ändern (None = unverändert, "" = entfernen)."""
    cat = _require(conn, category_id)
    if name is not None:
        name = _check_name(conn, name, cat["parent_id"], category_id)
        conn.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    if icon is not None:
        conn.execute("UPDATE categories SET icon = ? WHERE id = ?", (icon or None, category_id))
    if color is not None:
        conn.execute("UPDATE categories SET color = ? WHERE id = ?", (color or None, category_id))
    if name is not None:
        _refresh_fts_for_subtree(conn, category_id)


def descendant_ids(conn: sqlite3.Connection, category_id: int, include_self: bool = True) -> list[int]:
    """IDs aller Unterkategorien (rekursiv)."""
    rows = conn.execute(
        """
        WITH RECURSIVE sub(id) AS (
            SELECT ?
            UNION ALL
            SELECT c.id FROM categories c JOIN sub ON c.parent_id = sub.id
        )
        SELECT id FROM sub
        """,
        (category_id,),
    ).fetchall()
    ids = [r[0] for r in rows]
    return ids if include_self else [i for i in ids if i != category_id]


def ancestors(conn: sqlite3.Connection, category_id: int) -> list[dict[str, Any]]:
    """Pfad von der Wurzel bis zur Kategorie (für Breadcrumbs)."""
    rows = conn.execute(
        """
        WITH RECURSIVE up(id, parent_id, name, icon, color, depth) AS (
            SELECT id, parent_id, name, icon, color, 0 FROM categories WHERE id = ?
            UNION ALL
            SELECT c.id, c.parent_id, c.name, c.icon, c.color, up.depth + 1
            FROM categories c JOIN up ON c.id = up.parent_id
            WHERE up.depth < 64
        )
        SELECT id, parent_id, name, icon, color FROM up ORDER BY depth DESC
        """,
        (category_id,),
    ).fetchall()
    if not rows:
        raise NotFoundError(f"Kategorie {category_id} nicht gefunden")
    return [dict(r) for r in rows]


def category_path(conn: sqlite3.Connection, category_id: int, sep: str = " › ") -> str:
    """ "Backen › Kuchen › Obstkuchen"."""
    return sep.join(a["name"] for a in ancestors(conn, category_id))


def move_category(
    conn: sqlite3.Connection,
    category_id: int,
    new_parent_id: int | None,
    position: int | None = None,
) -> None:
    """Kategorie umhängen und/oder umsortieren. Verhindert Zyklen."""
    cat = _require(conn, category_id)
    if new_parent_id is not None:
        _require(conn, new_parent_id)
        if new_parent_id in descendant_ids(conn, category_id):
            raise ConflictError(
                "Eine Kategorie kann nicht unter sich selbst oder eine Unterkategorie verschoben werden"
            )
    old_parent = cat["parent_id"]
    if new_parent_id != old_parent:
        _check_name(conn, cat["name"], new_parent_id, category_id)

    # Geschwister der Zielebene ohne die verschobene Kategorie neu durchnummerieren
    siblings = [
        r[0]
        for r in conn.execute(
            "SELECT id FROM categories WHERE parent_id IS ? AND id != ? ORDER BY position, id",
            (new_parent_id, category_id),
        )
    ]
    if position is None or position > len(siblings):
        position = len(siblings)
    position = max(position, 0)
    siblings.insert(position, category_id)
    conn.execute("UPDATE categories SET parent_id = ? WHERE id = ?", (new_parent_id, category_id))
    for idx, cid in enumerate(siblings):
        conn.execute("UPDATE categories SET position = ? WHERE id = ?", (idx, cid))
    if new_parent_id != old_parent:
        _renumber(conn, old_parent)
        _refresh_fts_for_subtree(conn, category_id)


def _renumber(conn: sqlite3.Connection, parent_id: int | None) -> None:
    ids = [
        r[0] for r in conn.execute("SELECT id FROM categories WHERE parent_id IS ? ORDER BY position, id", (parent_id,))
    ]
    for idx, cid in enumerate(ids):
        conn.execute("UPDATE categories SET position = ? WHERE id = ?", (idx, cid))


def delete_category(conn: sqlite3.Connection, category_id: int) -> dict[str, Any]:
    """Kategorie löschen.

    Kindkategorien werden an die Elternkategorie gehängt, Rezepte wandern zur
    Elternkategorie (bzw. nach "Ohne Kategorie", wenn es keine gibt).
    Muss innerhalb einer Transaktion aufgerufen werden (Database.run).
    """
    cat = _require(conn, category_id)
    parent_id = cat["parent_id"]
    children = [
        r[0]
        for r in conn.execute("SELECT id FROM categories WHERE parent_id = ? ORDER BY position, id", (category_id,))
    ]
    next_pos = _next_position(conn, parent_id)
    for child_id in children:
        child = _require(conn, child_id)
        # Namenskonflikt auf Elternebene: Namen eindeutig machen
        name = child["name"]
        suffix = 2
        while conn.execute(
            "SELECT 1 FROM categories WHERE parent_id IS ? AND name = ? COLLATE NOCASE AND id != ?",
            (parent_id, name, child_id),
        ).fetchone():
            name = f"{child['name']} ({suffix})"
            suffix += 1
        conn.execute(
            "UPDATE categories SET parent_id = ?, name = ?, position = ? WHERE id = ?",
            (parent_id, name, next_pos, child_id),
        )
        next_pos += 1

    recipe_ids = [
        r[0] for r in conn.execute("SELECT recipe_id FROM recipe_categories WHERE category_id = ?", (category_id,))
    ]
    if parent_id is not None:
        conn.executemany(
            "INSERT OR IGNORE INTO recipe_categories (recipe_id, category_id) VALUES (?, ?)",
            [(rid, parent_id) for rid in recipe_ids],
        )
    conn.execute("DELETE FROM recipe_categories WHERE category_id = ?", (category_id,))
    conn.execute("DELETE FROM category_mappings WHERE category_id = ?", (category_id,))
    conn.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    _renumber(conn, parent_id)

    from .recipes import refresh_fts

    for rid in recipe_ids:
        refresh_fts(conn, rid)
    for child_id in children:
        _refresh_fts_for_subtree(conn, child_id)
    return {"moved_recipes": len(recipe_ids), "moved_children": len(children), "target_id": parent_id}


def get_tree(conn: sqlite3.Connection) -> dict[str, Any]:
    """Kompletter Baum mit Rezeptanzahl (direkt und inkl. Unterkategorien)."""
    cats = [dict(r) for r in conn.execute("SELECT * FROM categories ORDER BY position, name")]
    direct = {
        r[0]: r[1] for r in conn.execute("SELECT category_id, COUNT(*) FROM recipe_categories GROUP BY category_id")
    }
    # Distinct-Zählung je Teilbaum (ein Rezept in zwei Unterkategorien zählt einmal)
    total = {
        r[0]: r[1]
        for r in conn.execute(
            """
            WITH RECURSIVE tree(root, id) AS (
                SELECT id, id FROM categories
                UNION ALL
                SELECT tree.root, c.id FROM categories c JOIN tree ON c.parent_id = tree.id
            )
            SELECT tree.root, COUNT(DISTINCT rc.recipe_id)
            FROM tree JOIN recipe_categories rc ON rc.category_id = tree.id
            GROUP BY tree.root
            """
        )
    }
    nodes: dict[int, dict[str, Any]] = {}
    for c in cats:
        nodes[c["id"]] = {
            **c,
            "count": direct.get(c["id"], 0),
            "count_total": total.get(c["id"], 0),
            "children": [],
        }
    roots: list[dict[str, Any]] = []
    for c in cats:
        node = nodes[c["id"]]
        parent = nodes.get(c["parent_id"]) if c["parent_id"] is not None else None
        (parent["children"] if parent else roots).append(node)
    uncategorized = conn.execute(
        "SELECT COUNT(*) FROM recipes r WHERE NOT EXISTS (SELECT 1 FROM recipe_categories rc WHERE rc.recipe_id = r.id)"
    ).fetchone()[0]
    all_count = conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
    return {"categories": roots, "uncategorized": uncategorized, "total": all_count}


def list_categories(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Flache Liste inkl. Pfad (für Auswahlfelder und die KI)."""
    cats = [dict(r) for r in conn.execute("SELECT * FROM categories ORDER BY position, name")]
    by_id = {c["id"]: c for c in cats}

    def _path(c: dict[str, Any]) -> str:
        names = []
        seen: set[int] = set()
        while c is not None and c["id"] not in seen:
            seen.add(c["id"])
            names.append(c["name"])
            c = by_id.get(c["parent_id"])  # type: ignore[assignment]
        return " › ".join(reversed(names))

    for c in cats:
        c["path"] = _path(c)
    cats.sort(key=lambda c: c["path"].casefold())
    return cats


def set_recipe_categories(
    conn: sqlite3.Connection, recipe_id: int, category_ids: list[int], replace: bool = True
) -> None:
    """Kategorien eines Rezepts setzen (replace) oder ergänzen."""
    if conn.execute("SELECT 1 FROM recipes WHERE id = ?", (recipe_id,)).fetchone() is None:
        raise NotFoundError(f"Rezept {recipe_id} nicht gefunden")
    ids = list(dict.fromkeys(int(c) for c in category_ids or [] if c not in (None, UNCATEGORIZED_ID)))
    for cid in ids:
        _require(conn, cid)
    if replace:
        conn.execute("DELETE FROM recipe_categories WHERE recipe_id = ?", (recipe_id,))
    conn.executemany(
        "INSERT OR IGNORE INTO recipe_categories (recipe_id, category_id) VALUES (?, ?)",
        [(recipe_id, cid) for cid in ids],
    )
    from .recipes import refresh_fts

    refresh_fts(conn, recipe_id)


def recipe_categories(conn: sqlite3.Connection, recipe_id: int) -> list[dict[str, Any]]:
    """Kategorien eines Rezepts inkl. Pfad."""
    rows = conn.execute(
        "SELECT c.* FROM categories c JOIN recipe_categories rc ON rc.category_id = c.id WHERE rc.recipe_id = ? ORDER BY c.name",
        (recipe_id,),
    ).fetchall()
    result = []
    for r in rows:
        item = dict(r)
        item["path"] = [a["name"] for a in ancestors(conn, r["id"])]
        result.append(item)
    return result


def _refresh_fts_for_subtree(conn: sqlite3.Connection, category_id: int) -> None:
    from .recipes import refresh_fts

    ids = descendant_ids(conn, category_id)
    placeholders = ",".join("?" * len(ids))
    for (rid,) in conn.execute(
        f"SELECT DISTINCT recipe_id FROM recipe_categories WHERE category_id IN ({placeholders})", ids
    ).fetchall():
        refresh_fts(conn, rid)


def create_default_tree(conn: sqlite3.Connection) -> int:
    """Standardbaum anlegen (idempotent). Gibt die Anzahl neuer Kategorien zurück."""
    created = 0
    for name, icon, color, children in DEFAULT_CATEGORY_TREE:
        row = conn.execute(
            "SELECT id FROM categories WHERE parent_id IS NULL AND name = ? COLLATE NOCASE", (name,)
        ).fetchone()
        if row:
            parent_id = row[0]
        else:
            parent_id = create_category(conn, name, None, icon, color)
            created += 1
        for child_name, child_icon in children:
            if conn.execute(
                "SELECT 1 FROM categories WHERE parent_id = ? AND name = ? COLLATE NOCASE",
                (parent_id, child_name),
            ).fetchone():
                continue
            create_category(conn, child_name, parent_id, child_icon, color)
            created += 1
    return created


# ---------------------------------------------------------------------------
# Kategorie-Mappings (Quelle-Schlagwort → Kategorie)
# ---------------------------------------------------------------------------


def _norm_keyword(keyword: str) -> str:
    return " ".join((keyword or "").strip().split())


def get_mapping(conn: sqlite3.Connection, keyword: str) -> int | None:
    """Gelernte Kategorie zu einem Schlagwort."""
    row = conn.execute(
        "SELECT category_id FROM category_mappings WHERE source_keyword = ?", (_norm_keyword(keyword),)
    ).fetchone()
    return row[0] if row else None


def learn_mapping(conn: sqlite3.Connection, keyword: str, category_id: int) -> None:
    """Zuordnung merken bzw. überschreiben (lernt aus Korrekturen)."""
    keyword = _norm_keyword(keyword)
    if not keyword:
        return
    _require(conn, category_id)
    conn.execute(
        """
        INSERT INTO category_mappings (source_keyword, category_id, hits, updated)
        VALUES (?, ?, 1, ?)
        ON CONFLICT(source_keyword) DO UPDATE SET
            hits = CASE WHEN category_id = excluded.category_id THEN hits + 1 ELSE 1 END,
            category_id = excluded.category_id,
            updated = excluded.updated
        """,
        (keyword, category_id, utcnow_iso()),
    )


def forget_mapping(conn: sqlite3.Connection, keyword: str) -> None:
    """Zuordnung entfernen."""
    conn.execute("DELETE FROM category_mappings WHERE source_keyword = ?", (_norm_keyword(keyword),))


def list_mappings(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Alle gelernten Zuordnungen."""
    return [
        dict(r)
        for r in conn.execute(
            "SELECT m.*, c.name AS category_name FROM category_mappings m JOIN categories c ON c.id = m.category_id ORDER BY m.source_keyword"
        )
    ]


__all__ = [
    "UNCATEGORIZED_ID",
    "ancestors",
    "category_path",
    "create_category",
    "create_default_tree",
    "delete_category",
    "descendant_ids",
    "forget_mapping",
    "get_category",
    "get_mapping",
    "get_tree",
    "learn_mapping",
    "list_categories",
    "list_mappings",
    "move_category",
    "recipe_categories",
    "set_recipe_categories",
    "update_category",
]
