"""Rezepte: Anlegen, Lesen, Suchen, Löschen, Tags, Bilder, Volltextindex."""

from __future__ import annotations

from datetime import UTC, datetime, timedelta
import json
import random
import re
import sqlite3
from typing import Any

from ..const import (
    IMAGE_COVER,
    IMAGE_KINDS,
    ORIGINAL_LABEL,
    SOURCE_MANUAL,
    SOURCE_TYPES,
    SYSTEM_USER_ID,
)
from ..models import ValidationError, VersionData, utcnow_iso
from ..url_utils import normalize_url, url_key
from . import NotFoundError
from .categories import ancestors, descendant_ids, recipe_categories, set_recipe_categories

SORTS = {
    "name": "title COLLATE NOCASE ASC",
    "rating": "avg_stars DESC NULLS LAST, title COLLATE NOCASE",
    "last_cooked": "last_cooked DESC NULLS LAST, title COLLATE NOCASE",
    "least_recently_cooked": "last_cooked ASC NULLS FIRST, title COLLATE NOCASE",
    "new": "created DESC, id DESC",
    "updated": "updated DESC, id DESC",
}


def _require_recipe(conn: sqlite3.Connection, recipe_id: int) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM recipes WHERE id = ?", (recipe_id,)).fetchone()
    if row is None:
        raise NotFoundError(f"Rezept {recipe_id} nicht gefunden")
    return dict(row)


# ---------------------------------------------------------------------------
# Anlegen / Ändern / Löschen
# ---------------------------------------------------------------------------


def find_duplicates(conn: sqlite3.Connection, url: str) -> list[dict[str, Any]]:
    """Rezepte mit derselben (normalisierten) Quell-URL."""
    try:
        key = url_key(url)
    except ValueError:
        return []
    return [
        dict(r)
        for r in conn.execute(
            "SELECT id, title, source_url, created FROM recipes WHERE source_key = ? ORDER BY id",
            (key,),
        )
    ]


def create_recipe(
    conn: sqlite3.Connection,
    *,
    title: str,
    data: VersionData | dict[str, Any],
    description: str | None = None,
    source_url: str | None = None,
    source_type: str = SOURCE_MANUAL,
    image: str | None = None,
    category_ids: list[int] | None = None,
    tags: list[str] | None = None,
    user_id: str | None = None,
    created: str | None = None,
) -> int:
    """Rezept mit Version 1 „Original“ anlegen. Gibt die Rezept-ID zurück."""
    title = (title or "").strip()
    if not title:
        raise ValidationError("Titel darf nicht leer sein")
    if source_type not in SOURCE_TYPES:
        raise ValidationError(f"Unbekannte Quelle: {source_type}")
    vdata = data if isinstance(data, VersionData) else VersionData.from_dict(data)
    norm_url = key = None
    if source_url:
        norm_url = normalize_url(source_url)
        key = url_key(norm_url)
    now = utcnow_iso()
    cur = conn.execute(
        """
        INSERT INTO recipes (title, description, servings, prep_time, cook_time, total_time,
                             source_url, source_key, source_type, image, created, updated)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            title,
            (description or "").strip() or None,
            vdata.servings,
            vdata.prep_time,
            vdata.cook_time,
            vdata.total_time,
            norm_url,
            key,
            source_type,
            image,
            created or now,
            now,
        ),
    )
    recipe_id = int(cur.lastrowid)
    vcur = conn.execute(
        """
        INSERT INTO recipe_versions (recipe_id, version_no, label, data, is_original, user_id, created)
        VALUES (?, 1, ?, ?, 1, ?, ?)
        """,
        (recipe_id, ORIGINAL_LABEL, vdata.to_json(), user_id or SYSTEM_USER_ID, created or now),
    )
    conn.execute("UPDATE recipes SET default_version_id = ? WHERE id = ?", (int(vcur.lastrowid), recipe_id))
    if image:
        add_image(conn, recipe_id, image, IMAGE_COVER)
    if category_ids:
        set_recipe_categories(conn, recipe_id, category_ids)
    if tags:
        set_tags(conn, recipe_id, tags)
    refresh_fts(conn, recipe_id)
    return recipe_id


def update_recipe(
    conn: sqlite3.Connection,
    recipe_id: int,
    *,
    title: str | None = None,
    description: str | None = None,
    image: str | None = None,
    source_url: str | None = None,
) -> None:
    """Nicht versionierte Stammdaten ändern (Titel, Beschreibung, Titelbild, Quelle)."""
    _require_recipe(conn, recipe_id)
    sets: list[str] = []
    params: list[Any] = []
    if title is not None:
        if not title.strip():
            raise ValidationError("Titel darf nicht leer sein")
        sets.append("title = ?")
        params.append(title.strip())
    if description is not None:
        sets.append("description = ?")
        params.append(description.strip() or None)
    if image is not None:
        sets.append("image = ?")
        params.append(image or None)
    if source_url is not None:
        norm = normalize_url(source_url) if source_url else None
        sets += ["source_url = ?", "source_key = ?"]
        params += [norm, url_key(norm) if norm else None]
    if not sets:
        return
    sets.append("updated = ?")
    params.append(utcnow_iso())
    conn.execute(f"UPDATE recipes SET {', '.join(sets)} WHERE id = ?", (*params, recipe_id))
    refresh_fts(conn, recipe_id)


def touch(conn: sqlite3.Connection, recipe_id: int) -> None:
    """updated-Zeitstempel setzen."""
    conn.execute("UPDATE recipes SET updated = ? WHERE id = ?", (utcnow_iso(), recipe_id))


def delete_recipe(conn: sqlite3.Connection, recipe_id: int) -> list[str]:
    """Rezept inkl. aller Versionen, Notizen, Bewertungen löschen.

    Gibt die Pfade der zugehörigen Bilder zurück (Dateien löscht der Aufrufer).
    """
    recipe = _require_recipe(conn, recipe_id)
    paths = {r[0] for r in conn.execute("SELECT path FROM recipe_images WHERE recipe_id = ?", (recipe_id,))}
    paths |= {
        r[0] for r in conn.execute("SELECT photo FROM cook_log WHERE recipe_id = ? AND photo IS NOT NULL", (recipe_id,))
    }
    if recipe["image"]:
        paths.add(recipe["image"])
    conn.execute("DELETE FROM recipes WHERE id = ?", (recipe_id,))
    return sorted(paths)


def sync_from_default_version(conn: sqlite3.Connection, recipe_id: int) -> None:
    """Portionen/Zeiten im Rezept aus der Standardversion übernehmen (Cache für Listen)."""
    row = conn.execute(
        "SELECT v.data FROM recipes r JOIN recipe_versions v ON v.id = r.default_version_id WHERE r.id = ?",
        (recipe_id,),
    ).fetchone()
    if row is None:
        return
    data = VersionData.from_json(row[0])
    conn.execute(
        "UPDATE recipes SET servings = ?, prep_time = ?, cook_time = ?, total_time = ?, updated = ? WHERE id = ?",
        (data.servings, data.prep_time, data.cook_time, data.total_time, utcnow_iso(), recipe_id),
    )
    refresh_fts(conn, recipe_id)


# ---------------------------------------------------------------------------
# Tags
# ---------------------------------------------------------------------------


def _clean_tags(tags: list[str] | None) -> list[str]:
    seen: dict[str, str] = {}
    for t in tags or []:
        name = " ".join(str(t).strip().lstrip("#").split())
        if name and name.casefold() not in seen:
            seen[name.casefold()] = name[:60]
    return list(seen.values())


def set_tags(conn: sqlite3.Connection, recipe_id: int, tags: list[str], replace: bool = True) -> list[str]:
    """Tags eines Rezepts setzen oder ergänzen."""
    _require_recipe(conn, recipe_id)
    names = _clean_tags(tags)
    if replace:
        conn.execute("DELETE FROM recipe_tags WHERE recipe_id = ?", (recipe_id,))
    for name in names:
        conn.execute("INSERT OR IGNORE INTO tags (name) VALUES (?)", (name,))
        tag_id = conn.execute("SELECT id FROM tags WHERE name = ?", (name,)).fetchone()[0]
        conn.execute("INSERT OR IGNORE INTO recipe_tags (recipe_id, tag_id) VALUES (?, ?)", (recipe_id, tag_id))
    conn.execute("DELETE FROM tags WHERE id NOT IN (SELECT tag_id FROM recipe_tags)")
    refresh_fts(conn, recipe_id)
    return recipe_tags(conn, recipe_id)


def recipe_tags(conn: sqlite3.Connection, recipe_id: int) -> list[str]:
    """Tags eines Rezepts."""
    return [
        r[0]
        for r in conn.execute(
            "SELECT t.name FROM tags t JOIN recipe_tags rt ON rt.tag_id = t.id WHERE rt.recipe_id = ? ORDER BY t.name COLLATE NOCASE",
            (recipe_id,),
        )
    ]


def list_tags(conn: sqlite3.Connection) -> list[dict[str, Any]]:
    """Alle Tags mit Anzahl."""
    return [
        dict(r)
        for r in conn.execute(
            "SELECT t.name, COUNT(rt.recipe_id) AS count FROM tags t LEFT JOIN recipe_tags rt ON rt.tag_id = t.id GROUP BY t.id ORDER BY t.name COLLATE NOCASE"
        )
    ]


# ---------------------------------------------------------------------------
# Bilder
# ---------------------------------------------------------------------------


def add_image(
    conn: sqlite3.Connection,
    recipe_id: int,
    path: str,
    kind: str,
    position: int | None = None,
    cook_log_id: int | None = None,
) -> int:
    """Bild registrieren. Ein neues Cover ersetzt das Titelbild."""
    if kind not in IMAGE_KINDS:
        raise ValidationError(f"Unbekannte Bildart: {kind}")
    if position is None:
        position = conn.execute(
            "SELECT COALESCE(MAX(position) + 1, 0) FROM recipe_images WHERE recipe_id = ? AND kind = ?",
            (recipe_id, kind),
        ).fetchone()[0]
    cur = conn.execute(
        "INSERT INTO recipe_images (recipe_id, path, kind, position, cook_log_id, created) VALUES (?, ?, ?, ?, ?, ?)",
        (recipe_id, path, kind, position, cook_log_id, utcnow_iso()),
    )
    if kind == IMAGE_COVER:
        conn.execute("UPDATE recipes SET image = ? WHERE id = ?", (path, recipe_id))
    return int(cur.lastrowid)


def list_images(conn: sqlite3.Connection, recipe_id: int, kind: str | None = None) -> list[dict[str, Any]]:
    """Bilder eines Rezepts."""
    sql = "SELECT * FROM recipe_images WHERE recipe_id = ?"
    params: list[Any] = [recipe_id]
    if kind:
        sql += " AND kind = ?"
        params.append(kind)
    return [dict(r) for r in conn.execute(sql + " ORDER BY kind, position, id", params)]


def reorder_images(conn: sqlite3.Connection, recipe_id: int, image_ids: list[int]) -> None:
    """Reihenfolge von Bildern setzen (z. B. Doppelseite)."""
    for pos, image_id in enumerate(image_ids):
        conn.execute("UPDATE recipe_images SET position = ? WHERE id = ? AND recipe_id = ?", (pos, image_id, recipe_id))


def delete_image(conn: sqlite3.Connection, image_id: int) -> str | None:
    """Bild-Eintrag löschen, gibt den Pfad zurück."""
    row = conn.execute("SELECT * FROM recipe_images WHERE id = ?", (image_id,)).fetchone()
    if row is None:
        return None
    conn.execute("DELETE FROM recipe_images WHERE id = ?", (image_id,))
    if row["kind"] == IMAGE_COVER:
        nxt = conn.execute(
            "SELECT path FROM recipe_images WHERE recipe_id = ? AND kind = ? ORDER BY position DESC, id DESC LIMIT 1",
            (row["recipe_id"], IMAGE_COVER),
        ).fetchone()
        conn.execute(
            "UPDATE recipes SET image = ? WHERE id = ? AND image = ?",
            (nxt[0] if nxt else None, row["recipe_id"], row["path"]),
        )
    return row["path"]


# ---------------------------------------------------------------------------
# Volltextindex
# ---------------------------------------------------------------------------


def refresh_fts(conn: sqlite3.Connection, recipe_id: int) -> None:
    """FTS-Eintrag (rowid = recipe_id) neu schreiben."""
    conn.execute("DELETE FROM recipe_fts WHERE rowid = ?", (recipe_id,))
    row = conn.execute(
        "SELECT r.title, r.description, v.data FROM recipes r LEFT JOIN recipe_versions v ON v.id = r.default_version_id WHERE r.id = ?",
        (recipe_id,),
    ).fetchone()
    if row is None:
        return
    ingredients = ""
    if row["data"]:
        data = json.loads(row["data"])
        ingredients = " ".join(i.get("name", "") for i in data.get("ingredients", []))
    tags = " ".join(recipe_tags(conn, recipe_id))
    cat_names: set[str] = set()
    for (cid,) in conn.execute("SELECT category_id FROM recipe_categories WHERE recipe_id = ?", (recipe_id,)):
        cat_names.update(a["name"] for a in ancestors(conn, cid))
    conn.execute(
        "INSERT INTO recipe_fts (rowid, title, ingredients, tags, categories) VALUES (?, ?, ?, ?, ?)",
        (recipe_id, row["title"], ingredients, tags, " ".join(sorted(cat_names))),
    )


def rebuild_fts(conn: sqlite3.Connection) -> int:
    """Gesamten Index neu aufbauen."""
    conn.execute("DELETE FROM recipe_fts")
    ids = [r[0] for r in conn.execute("SELECT id FROM recipes")]
    for rid in ids:
        refresh_fts(conn, rid)
    return len(ids)


def _fts_query(query: str) -> str | None:
    tokens = re.findall(r"[\wäöüÄÖÜß]+", query or "")
    if not tokens:
        return None
    return " AND ".join(f'"{t}"*' for t in tokens)


# ---------------------------------------------------------------------------
# Lesen / Suchen
# ---------------------------------------------------------------------------

_STATS_SQL = """
    (SELECT AVG(stars) FROM cook_log c WHERE c.recipe_id = r.id AND c.stars IS NOT NULL) AS avg_stars,
    (SELECT COUNT(stars) FROM cook_log c WHERE c.recipe_id = r.id) AS rating_count,
    (SELECT COUNT(*) FROM cook_log c WHERE c.recipe_id = r.id AND c.cooked_at IS NOT NULL) AS cooked_count,
    (SELECT MAX(cooked_at) FROM cook_log c WHERE c.recipe_id = r.id) AS last_cooked
"""


def search_recipes(
    conn: sqlite3.Connection,
    *,
    query: str | None = None,
    category_id: int | None = None,
    include_subcategories: bool = True,
    uncategorized: bool = False,
    tags: list[str] | None = None,
    min_stars: float | None = None,
    never_cooked: bool = False,
    not_cooked_since_days: int | None = None,
    recipe_ids: list[int] | None = None,
    sort: str = "name",
    limit: int | None = 50,
    offset: int = 0,
) -> dict[str, Any]:
    """Rezepte filtern und sortieren. Gibt {"total": n, "items": [...]} zurück."""
    where: list[str] = []
    params: list[Any] = []
    rank_sql = "0"
    fts = _fts_query(query) if query else None
    if query and fts is None:
        return {"total": 0, "items": []}
    if fts:
        where.append("r.id IN (SELECT rowid FROM recipe_fts WHERE recipe_fts MATCH ?)")
        params.append(fts)
        rank_sql = (
            "(SELECT bm25(recipe_fts, 10.0, 3.0, 2.0, 1.0) FROM recipe_fts WHERE recipe_fts MATCH ? AND rowid = r.id)"
        )
    if uncategorized:
        where.append("NOT EXISTS (SELECT 1 FROM recipe_categories rc WHERE rc.recipe_id = r.id)")
    elif category_id is not None:
        ids = descendant_ids(conn, category_id) if include_subcategories else [category_id]
        where.append(
            f"r.id IN (SELECT recipe_id FROM recipe_categories WHERE category_id IN ({','.join('?' * len(ids))}))"
        )
        params.extend(ids)
    for tag in _clean_tags(tags):
        where.append(
            "EXISTS (SELECT 1 FROM recipe_tags rt JOIN tags t ON t.id = rt.tag_id WHERE rt.recipe_id = r.id AND t.name = ?)"
        )
        params.append(tag)
    if recipe_ids is not None:
        where.append(f"r.id IN ({','.join('?' * len(recipe_ids)) or 'NULL'})")
        params.extend(recipe_ids)

    inner = f"SELECT r.*, {_STATS_SQL}, {rank_sql} AS rank FROM recipes r"
    if where:
        inner += " WHERE " + " AND ".join(where)
    outer_where: list[str] = []
    outer_params: list[Any] = []
    if min_stars:
        outer_where.append("avg_stars >= ?")
        outer_params.append(float(min_stars))
    if never_cooked:
        outer_where.append("cooked_count = 0")
    if not_cooked_since_days:
        cutoff = datetime.now(UTC) - timedelta(days=int(not_cooked_since_days))
        outer_where.append("(last_cooked IS NULL OR last_cooked < ?)")
        outer_params.append(cutoff.isoformat(timespec="seconds"))
    order = "rank ASC, title COLLATE NOCASE" if fts and sort in (None, "relevance") else SORTS.get(sort, SORTS["name"])
    sql = f"SELECT * FROM ({inner})"
    if outer_where:
        sql += " WHERE " + " AND ".join(outer_where)
    all_params = ([fts] if fts else []) + params + outer_params
    total = conn.execute(f"SELECT COUNT(*) FROM ({sql})", all_params).fetchone()[0]
    sql += f" ORDER BY {order}"
    if limit:
        sql += " LIMIT ? OFFSET ?"
        all_params += [int(limit), int(offset)]
    items = []
    for row in conn.execute(sql, all_params):
        item = dict(row)
        item.pop("rank", None)
        item.pop("source_key", None)
        if item["avg_stars"] is not None:
            item["avg_stars"] = round(item["avg_stars"], 2)
        item["tags"] = recipe_tags(conn, item["id"])
        item["category_ids"] = [
            r[0] for r in conn.execute("SELECT category_id FROM recipe_categories WHERE recipe_id = ?", (item["id"],))
        ]
        items.append(item)
    return {"total": total, "items": items}


def random_recipe(
    conn: sqlite3.Connection,
    *,
    category_id: int | None = None,
    tags: list[str] | None = None,
    min_stars: float | None = None,
    rng: random.Random | None = None,
) -> dict[str, Any] | None:
    """Zufälliges Rezept (gleichverteilt) aus den Treffern."""
    result = search_recipes(conn, category_id=category_id, tags=tags, min_stars=min_stars, limit=None)
    if not result["items"]:
        return None
    return (rng or random).choice(result["items"])


def get_recipe(conn: sqlite3.Connection, recipe_id: int, version_id: int | None = None) -> dict[str, Any]:
    """Rezept mit Versionen, gewählter Version, Kategorien, Tags, Bildern, Notizen, Statistik."""
    from .ratings import recipe_stats
    from .versions import get_version, list_annotations, list_versions

    recipe = _require_recipe(conn, recipe_id)
    recipe.pop("source_key", None)
    vid = version_id or recipe["default_version_id"]
    version = get_version(conn, vid) if vid else None
    if version is None or version["recipe_id"] != recipe_id:
        raise NotFoundError(f"Version {vid} gehört nicht zu Rezept {recipe_id}")
    recipe["versions"] = list_versions(conn, recipe_id)
    recipe["version"] = version
    recipe["categories"] = recipe_categories(conn, recipe_id)
    recipe["tags"] = recipe_tags(conn, recipe_id)
    recipe["images"] = list_images(conn, recipe_id)
    recipe["annotations"] = list_annotations(conn, recipe_id, version["id"])
    recipe["stats"] = recipe_stats(conn, recipe_id)
    return recipe


def count_recipes(conn: sqlite3.Connection) -> int:
    """Anzahl Rezepte."""
    return conn.execute("SELECT COUNT(*) FROM recipes").fetchone()[0]
