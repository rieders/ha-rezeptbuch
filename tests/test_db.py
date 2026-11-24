"""DB-Tests: Schema, CRUD, Original-Schutz, Versionen + Diff, Bewertungen, Kategorien, FTS."""

from __future__ import annotations

import sqlite3

import pytest

from custom_components.rezeptbuch.const import SYSTEM_USER_ID
from custom_components.rezeptbuch.db import (
    ConflictError,
    Database,
    NotFoundError,
    categories as cats,
    connect,
    ratings,
    recipes,
    shopping,
    transaction,
    versions,
)
from custom_components.rezeptbuch.db.schema import SCHEMA_VERSION, get_schema_version
from custom_components.rezeptbuch.models import ValidationError

SAMPLE = {
    "servings": 4,
    "prep_time": 20,
    "cook_time": 40,
    "ingredients": [
        {"amount": 250, "unit": "g", "name": "Mehl"},
        {"amount": 200, "unit": "g", "name": "Zucker"},
        {"amount": 3, "name": "Eier"},
        {"amount": 1, "unit": "Pck.", "name": "Backpulver"},
    ],
    "steps": [
        {"text": "Alles verrühren."},
        {"text": "Bei 180 Grad 40 Minuten backen.", "timer_seconds": 2400},
    ],
}


def _recipe(tx, title="Rührkuchen", **kwargs):
    return tx(recipes.create_recipe, title=title, data=kwargs.pop("data", SAMPLE), **kwargs)


# --- Schema ---------------------------------------------------------------------


def test_schema_migrated(conn):
    assert get_schema_version(conn) == SCHEMA_VERSION == 2
    tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type IN ('table')")}
    assert {"recipes", "recipe_versions", "offers", "watchlist", "watch_hits", "recipe_fts"} <= tables
    cols = {r[1] for r in conn.execute("PRAGMA table_info(shopping_items)")}
    assert "offer_id" in cols


def test_migration_is_idempotent(tmp_path):
    path = tmp_path / "x.db"
    connect(path).close()
    c = connect(path)
    assert c.execute("SELECT COUNT(*) FROM schema_version").fetchone()[0] == SCHEMA_VERSION
    c.close()


def test_fts_is_regular_table(conn):
    sql = conn.execute("SELECT sql FROM sqlite_master WHERE name = 'recipe_fts'").fetchone()[0]
    assert "content=" not in sql.replace(" ", "")


# --- Rezepte CRUD -------------------------------------------------------------------


def test_create_and_get_recipe(conn, tx):
    rid = _recipe(tx, tags=["Klassiker", "schnell", "klassiker"], source_url="https://www.chefkoch.de/r/1?utm_source=x")
    r = tx(recipes.get_recipe, rid)
    assert r["title"] == "Rührkuchen"
    assert r["servings"] == 4 and r["total_time"] == 60
    assert r["source_url"] == "https://www.chefkoch.de/r/1"
    assert r["tags"] == ["Klassiker", "schnell"]
    assert len(r["versions"]) == 1
    v = r["version"]
    assert v["is_original"] and v["label"] == "Original" and v["version_no"] == 1
    assert v["data"]["ingredients"][0] == {
        "amount": 250.0,
        "amount_max": None,
        "unit": "g",
        "name": "Mehl",
        "note": None,
        "group": None,
    }
    assert r["stats"]["rating_count"] == 0


def test_create_validation(tx):
    with pytest.raises(ValidationError):
        _recipe(tx, title="  ")
    with pytest.raises(ValidationError):
        _recipe(tx, data={"ingredients": [{"amount": 1}]})


def test_duplicate_detection(tx):
    rid = _recipe(tx, source_url="http://chefkoch.de/rezepte/42/Kuchen.html/#x")
    dups = tx(recipes.find_duplicates, "https://www.chefkoch.de/rezepte/42/Kuchen.html?utm_medium=share")
    assert [d["id"] for d in dups] == [rid]
    # Index ist nicht unique: zweites Rezept mit gleicher URL ist (bewusst) möglich
    rid2 = _recipe(tx, source_url="https://chefkoch.de/rezepte/42/Kuchen.html")
    assert len(tx(recipes.find_duplicates, "chefkoch.de/rezepte/42/Kuchen.html")) == 2
    assert rid2 != rid
    assert tx(recipes.find_duplicates, "kein url") == []


def test_update_and_delete_recipe(conn, tx):
    rid = _recipe(tx, image="covers/a.jpg")
    tx(recipes.update_recipe, rid, title="Marmorkuchen", description="lecker")
    r = tx(recipes.get_recipe, rid)
    assert r["title"] == "Marmorkuchen" and r["image"] == "covers/a.jpg"
    paths = tx(recipes.delete_recipe, rid)
    assert paths == ["covers/a.jpg"]
    with pytest.raises(NotFoundError):
        tx(recipes.get_recipe, rid)
    assert conn.execute("SELECT COUNT(*) FROM recipe_fts").fetchone()[0] == 0


# --- Original-Schutz -------------------------------------------------------------


def test_delete_recipe_with_original_and_versions_works(conn, tx):
    rid = _recipe(tx)
    tx(versions.create_version, rid, {**SAMPLE, "servings": 2}, label="Halbe Menge")
    log = tx(ratings.add_cook_log, rid, stars=4)
    tx(versions.add_annotation, rid, text="lecker")
    tx(recipes.delete_recipe, rid)
    for table in ("recipe_versions", "cook_log", "annotations"):
        assert conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0] == 0, table
    assert log


def test_original_cannot_be_deleted_directly(conn, tx):
    rid = _recipe(tx)
    vid = tx(versions.original_version_id, rid)
    with pytest.raises(sqlite3.IntegrityError, match="Originalversion"), transaction(conn):
        conn.execute("DELETE FROM recipe_versions WHERE id = ?", (vid,))
    with pytest.raises(ConflictError):
        tx(versions.delete_version, vid)
    assert conn.execute("SELECT COUNT(*) FROM recipe_versions").fetchone()[0] == 1


def test_original_cannot_be_updated(conn, tx):
    rid = _recipe(tx)
    vid = tx(versions.original_version_id, rid)
    for sql in (
        "UPDATE recipe_versions SET data = '{}' WHERE id = ?",
        "UPDATE recipe_versions SET label = 'Hack' WHERE id = ?",
        "UPDATE recipe_versions SET is_original = 0 WHERE id = ?",
    ):
        with pytest.raises(sqlite3.IntegrityError, match="Originalversion"), transaction(conn):
            conn.execute(sql, (vid,))
    with pytest.raises(ConflictError):
        tx(versions.update_version, vid, label="neu")


def test_original_cook_log_link_may_be_nulled(conn, tx):
    """ON DELETE SET NULL für cook_log_id darf nicht am Trigger scheitern."""

    def _setup(c):
        now = "2024-01-01T00:00:00+00:00"
        rid = c.execute(
            "INSERT INTO recipes (title, source_type, created, updated) VALUES ('X', 'manual', ?, ?)", (now, now)
        ).lastrowid
        log = c.execute("INSERT INTO cook_log (recipe_id, stars, created) VALUES (?, 4, ?)", (rid, now)).lastrowid
        vid = versions.create_version(c, rid, SAMPLE, is_original=True, cook_log_id=log)
        return vid, log

    vid, log = tx(_setup)
    tx(ratings.delete_cook_log, log)
    assert tx(versions.get_version, vid)["cook_log_id"] is None


def test_backup_import_can_create_original(conn, tx):
    """Backup-Import: Rezept ohne Original anlegen und Original nachträglich einfügen."""

    def _import(c):
        now = "2024-01-01T00:00:00+00:00"
        cur = c.execute(
            "INSERT INTO recipes (title, source_type, created, updated) VALUES ('Import', 'manual', ?, ?)",
            (now, now),
        )
        rid = cur.lastrowid
        vid = versions.create_version(c, rid, SAMPLE, label="Original", is_original=True, created=now)
        versions.create_version(c, rid, SAMPLE, label="Meine")
        return rid, vid

    rid, vid = tx(_import)
    r = tx(recipes.get_recipe, rid)
    assert r["versions"][0]["id"] == vid and r["versions"][0]["is_original"]
    with pytest.raises(ConflictError):
        tx(versions.create_version, rid, SAMPLE, is_original=True)
    tx(recipes.delete_recipe, rid)


# --- Versionen + Diff -------------------------------------------------------------


def test_versions_and_default(tx):
    rid = _recipe(tx)
    orig = tx(versions.original_version_id, rid)
    changed = {
        **SAMPLE,
        "servings": 6,
        "ingredients": [
            {"amount": 250, "unit": "g", "name": "Mehl"},
            {"amount": 150, "unit": "g", "name": "Zucker"},
            {"amount": 3, "name": "Eier"},
            {"amount": 100, "unit": "g", "name": "Schokolade"},
        ],
    }
    v2 = tx(versions.create_version, rid, changed, change_note="weniger süß")
    r = tx(recipes.get_recipe, rid)
    assert r["default_version_id"] == v2 and r["servings"] == 6
    assert r["version"]["label"] == "Meine Version"
    assert [v["id"] for v in r["versions"]] == [orig, v2]
    assert r["versions"][1]["is_default"]

    # Original bleibt unverändert
    assert tx(versions.get_version, orig)["data"]["servings"] == 4

    d = tx(versions.diff, orig, v2)
    assert d["has_changes"]
    by_status = {(e["status"], (e["new"] or e["old"])["name"]) for e in d["ingredients"]}
    assert ("changed", "Zucker") in by_status
    assert ("removed", "Backpulver") in by_status
    assert ("added", "Schokolade") in by_status
    assert ("unchanged", "Mehl") in by_status
    assert "Zucker 200 g → 150 g" in d["summary"]
    assert d["meta"] == [{"field": "servings", "label": "Portionen", "old": 4.0, "new": 6.0}]

    v3 = tx(versions.create_version, rid, SAMPLE, label="Test", make_default=False)
    assert tx(recipes.get_recipe, rid)["default_version_id"] == v2
    tx(versions.reset_to_original, rid)
    assert tx(recipes.get_recipe, rid)["default_version_id"] == orig
    tx(versions.set_default_version, rid, v3)
    tx(versions.delete_version, v3)
    r = tx(recipes.get_recipe, rid)
    assert r["default_version_id"] == orig and r["servings"] == 4


def test_version_with_cook_log_link(tx):
    rid = _recipe(tx)
    other = _recipe(tx, title="Anderes")
    log = tx(ratings.add_cook_log, rid, stars=4.5, comment="gut")
    vid = tx(versions.create_version, rid, SAMPLE, cook_log_id=log)
    assert tx(versions.get_version, vid)["cook_log_id"] == log
    foreign = tx(ratings.add_cook_log, other, stars=1)
    with pytest.raises(ValidationError):
        tx(versions.create_version, rid, SAMPLE, cook_log_id=foreign)


def test_step_diff_words(tx):
    rid = _recipe(tx)
    orig = tx(versions.original_version_id, rid)
    data = {**SAMPLE, "steps": [{"text": "Alles verrühren."}, {"text": "Bei 170 Grad 45 Minuten backen."}]}
    v2 = tx(versions.create_version, rid, data)
    d = tx(versions.diff, orig, v2)
    step = d["steps"][1]
    assert step["status"] == "changed"
    ops = {(w["op"], w["text"]) for w in step["words"]}
    assert ("delete", "180") in ops and ("insert", "170") in ops


def test_annotations(tx):
    rid = _recipe(tx)
    orig = tx(versions.original_version_id, rid)
    a1 = tx(
        versions.add_annotation,
        rid,
        text="nächstes Mal weniger Salz",
        target_type="ingredient",
        target_index=1,
        version_id=orig,
    )
    tx(versions.add_annotation, rid, text="Allgemein super")
    with pytest.raises(ValidationError):
        tx(versions.add_annotation, rid, text="x", target_type="step", target_index=9, version_id=orig)
    with pytest.raises(ValidationError):
        tx(versions.add_annotation, rid, text="x", target_type="step")
    notes = tx(versions.list_annotations, rid, orig)
    assert len(notes) == 2
    tx(versions.update_annotation, a1, "weniger Zucker")
    tx(versions.delete_annotation, a1)
    assert len(tx(versions.list_annotations, rid)) == 1


# --- Bewertungen ----------------------------------------------------------------


def test_ratings_multi_user(tx):
    rid = _recipe(tx)
    tx(ratings.add_cook_log, rid, stars=4, user_id="anna", cooked_at="2024-03-01T18:00:00+00:00")
    tx(ratings.add_cook_log, rid, stars=5, user_id="anna", cooked_at="2024-04-01T18:00:00+00:00")
    tx(ratings.add_cook_log, rid, stars=2.5, user_id="ben", cooked=False, comment="zu süß")
    tx(ratings.add_cook_log, rid, stars=3, user_id=None)  # Automation → System
    tx(ratings.add_cook_log, rid, user_id="ben", cooked_at="2024-05-01T18:00:00+00:00")  # nur gekocht
    stats = tx(ratings.recipe_stats, rid)
    assert stats["avg_stars"] == pytest.approx((4 + 5 + 2.5 + 3) / 4, abs=0.01)
    assert stats["rating_count"] == 4
    assert stats["cooked_count"] == 4
    users = {u["user_id"]: u for u in stats["per_user"]}
    assert set(users) == {"anna", "ben", SYSTEM_USER_ID}
    assert users["anna"]["avg_stars"] == 4.5
    assert users["ben"]["avg_stars"] == 2.5 and users["ben"]["cooked_count"] == 1
    assert users[SYSTEM_USER_ID]["rating_count"] == 1
    hist = tx(ratings.history, rid)
    assert len(hist) == 5


@pytest.mark.parametrize("stars", [0, 0.3, 5.5, 4.2, "x"])
def test_invalid_stars(tx, stars):
    rid = _recipe(tx)
    with pytest.raises(ValidationError):
        tx(ratings.add_cook_log, rid, stars=stars)


def test_rating_without_anything_rejected(tx):
    rid = _recipe(tx)
    with pytest.raises(ValidationError):
        tx(ratings.add_cook_log, rid, cooked=False)


def test_legacy_null_user_does_not_break_stats(conn, tx):
    rid = _recipe(tx)
    with transaction(conn):
        conn.execute(
            "INSERT INTO cook_log (recipe_id, stars, created, user_id) VALUES (?, 4, '2024-01-01', 'system')",
            (rid,),
        )
    stats = tx(ratings.recipe_stats, rid)
    assert stats["per_user"][0]["user_id"] == SYSTEM_USER_ID


# --- Kategorien ---------------------------------------------------------------


def test_default_tree(tx):
    assert tx(cats.create_default_tree) == 20
    assert tx(cats.create_default_tree) == 0  # idempotent
    tree = tx(cats.get_tree)
    assert [c["name"] for c in tree["categories"]] == ["Kochen", "Backen", "Getränke"]
    assert len(tree["categories"][1]["children"]) == 5


def _three_levels(tx):
    backen = tx(cats.create_category, "Backen")
    kuchen = tx(cats.create_category, "Kuchen", backen)
    obst = tx(cats.create_category, "Obstkuchen", kuchen)
    return backen, kuchen, obst


def test_three_levels_and_breadcrumbs(tx):
    backen, kuchen, obst = _three_levels(tx)
    assert tx(cats.category_path, obst) == "Backen › Kuchen › Obstkuchen"
    assert set(tx(cats.descendant_ids, backen)) == {backen, kuchen, obst}
    with pytest.raises(ConflictError):
        tx(cats.create_category, "kuchen", backen)  # Name pro Ebene eindeutig (NOCASE)
    tx(cats.create_category, "Kuchen")  # auf anderer Ebene erlaubt


def test_cycle_prevention(tx):
    backen, kuchen, obst = _three_levels(tx)
    with pytest.raises(ConflictError):
        tx(cats.move_category, backen, obst)
    with pytest.raises(ConflictError):
        tx(cats.move_category, kuchen, kuchen)
    tx(cats.move_category, obst, None)  # Zur Wurzel ist ok
    assert tx(cats.get_category, obst)["parent_id"] is None


def test_move_and_reorder(tx):
    a = tx(cats.create_category, "A")
    b = tx(cats.create_category, "B")
    c = tx(cats.create_category, "C")
    tx(cats.move_category, c, None, 0)
    tree = tx(cats.get_tree)
    assert [n["name"] for n in tree["categories"]] == ["C", "A", "B"]
    tx(cats.move_category, a, b)
    tree = tx(cats.get_tree)
    assert [n["name"] for n in tree["categories"]] == ["C", "B"]
    assert [n["position"] for n in tree["categories"]] == [0, 1]
    assert tree["categories"][1]["children"][0]["id"] == a


def test_counts_include_subcategories(tx):
    _, kuchen, obst = _three_levels(tx)
    r1 = _recipe(tx, title="Apfelkuchen", category_ids=[obst])
    _recipe(tx, title="Marmorkuchen", category_ids=[kuchen])
    tx(cats.set_recipe_categories, r1, [obst, kuchen])  # doppelt im Teilbaum
    _recipe(tx, title="Ohne")
    tree = tx(cats.get_tree)
    b = tree["categories"][0]
    k = b["children"][0]
    o = k["children"][0]
    assert (b["count"], b["count_total"]) == (0, 2)
    assert (k["count"], k["count_total"]) == (2, 2)
    assert (o["count"], o["count_total"]) == (1, 1)
    assert tree["uncategorized"] == 1 and tree["total"] == 3


def test_category_filter_with_and_without_subcategories(tx):
    backen, kuchen, obst = _three_levels(tx)
    _recipe(tx, title="Apfelkuchen", category_ids=[obst])
    _recipe(tx, title="Marmorkuchen", category_ids=[kuchen])
    _recipe(tx, title="Nix")
    res = tx(recipes.search_recipes, category_id=backen)
    assert res["total"] == 2
    res = tx(recipes.search_recipes, category_id=kuchen, include_subcategories=False)
    assert [i["title"] for i in res["items"]] == ["Marmorkuchen"]
    res = tx(recipes.search_recipes, uncategorized=True)
    assert [i["title"] for i in res["items"]] == ["Nix"]


def test_delete_category_moves_children_and_recipes(conn, tx):
    backen, kuchen, obst = _three_levels(tx)
    r1 = _recipe(tx, title="Marmorkuchen", category_ids=[kuchen])
    r2 = _recipe(tx, title="Apfelkuchen", category_ids=[obst])
    result = tx(cats.delete_category, kuchen)
    assert result == {"moved_recipes": 1, "moved_children": 1, "target_id": backen}
    assert tx(cats.get_category, obst)["parent_id"] == backen
    assert [c["id"] for c in tx(cats.recipe_categories, r1)] == [backen]
    assert [c["id"] for c in tx(cats.recipe_categories, r2)] == [obst]
    # Root löschen → Rezepte ohne Kategorie, Kinder werden Wurzeln
    tx(cats.delete_category, backen)
    assert tx(cats.recipe_categories, r1) == []
    assert tx(cats.get_category, obst)["parent_id"] is None
    assert tx(cats.get_tree)["uncategorized"] == 1


def test_delete_category_name_conflict(tx):
    a = tx(cats.create_category, "A")
    tx(cats.create_category, "X", a)
    tx(cats.create_category, "X")
    tx(cats.delete_category, a)
    names = sorted(c["name"] for c in tx(cats.get_tree)["categories"])
    assert names == ["X", "X (2)"]


def test_parent_fk_restrict(conn, tx):
    backen, _, _ = _three_levels(tx)
    with pytest.raises(sqlite3.IntegrityError), transaction(conn):
        conn.execute("DELETE FROM categories WHERE id = ?", (backen,))


def test_mappings_learn(tx):
    backen, kuchen, _ = _three_levels(tx)
    tx(cats.learn_mapping, "Backen", backen)
    tx(cats.learn_mapping, "  backen ", kuchen)  # Korrektur überschreibt
    assert tx(cats.get_mapping, "BACKEN") == kuchen
    assert tx(cats.list_mappings)[0]["hits"] == 1
    tx(cats.learn_mapping, "Backen", kuchen)
    assert tx(cats.list_mappings)[0]["hits"] == 2
    tx(cats.delete_category, kuchen)
    assert tx(cats.get_mapping, "backen") is None


# --- Suche / FTS ---------------------------------------------------------------


def test_fulltext_search(tx):
    kuchen = tx(cats.create_category, "Kuchen")
    _recipe(
        tx,
        title="Käsekuchen",
        data={**SAMPLE, "ingredients": [{"name": "Quark", "amount": 500, "unit": "g"}]},
        tags=["Sonntag"],
    )
    _recipe(tx, title="Gulasch", data={**SAMPLE, "ingredients": [{"name": "Rindfleisch"}]}, category_ids=[kuchen])

    def titles(**kw):
        return [i["title"] for i in tx(recipes.search_recipes, **kw)["items"]]

    assert titles(query="käse") == ["Käsekuchen"]
    assert titles(query="kase") == ["Käsekuchen"]  # Diakritika egal
    assert titles(query="quark") == ["Käsekuchen"]  # Zutaten
    assert titles(query="sonntag") == ["Käsekuchen"]  # Tags
    assert titles(query="kuchen") == ["Gulasch"]  # Kategorie (Präfix „kuchen*“ matcht Titel nicht mittendrin)
    assert titles(query="rind") == ["Gulasch"]  # Präfix
    assert titles(query="!!!") == []
    assert titles(tags=["sonntag"]) == ["Käsekuchen"]


def test_fts_updates_on_category_rename_and_tags(tx):
    k = tx(cats.create_category, "Kuchen")
    rid = _recipe(tx, title="X", category_ids=[k])
    tx(cats.update_category, k, name="Gebäck")
    assert tx(recipes.search_recipes, query="gebäck")["total"] == 1
    assert tx(recipes.search_recipes, query="kuchen")["total"] == 0
    tx(recipes.set_tags, rid, ["Party"])
    assert tx(recipes.search_recipes, query="party")["total"] == 1


def test_search_filters_and_sort(tx):
    a = _recipe(tx, title="A")
    b = _recipe(tx, title="B")
    c = _recipe(tx, title="C")
    tx(ratings.add_cook_log, a, stars=5, cooked_at="2020-01-01T00:00:00+00:00")
    tx(ratings.add_cook_log, b, stars=3)
    res = tx(recipes.search_recipes, min_stars=4)
    assert [i["title"] for i in res["items"]] == ["A"]
    res = tx(recipes.search_recipes, never_cooked=True)
    assert [i["title"] for i in res["items"]] == ["C"]
    res = tx(recipes.search_recipes, not_cooked_since_days=30)
    assert [i["title"] for i in res["items"]] == ["A", "C"]
    res = tx(recipes.search_recipes, sort="rating")
    assert [i["title"] for i in res["items"]] == ["A", "B", "C"]
    res = tx(recipes.search_recipes, sort="name", limit=2, offset=1)
    assert res["total"] == 3 and [i["title"] for i in res["items"]] == ["B", "C"]
    assert c


# --- Bilder / Einkaufsliste ---------------------------------------------------------


def test_images(tx):
    rid = _recipe(tx)
    i1 = tx(recipes.add_image, rid, "src/1.jpg", "source_photo")
    i2 = tx(recipes.add_image, rid, "src/2.jpg", "source_photo")
    tx(recipes.reorder_images, rid, [i2, i1])
    imgs = tx(recipes.list_images, rid, "source_photo")
    assert [i["path"] for i in imgs] == ["src/2.jpg", "src/1.jpg"]
    tx(recipes.add_image, rid, "cover.jpg", "cover")
    assert tx(recipes.get_recipe, rid)["image"] == "cover.jpg"
    with pytest.raises(ValidationError):
        tx(recipes.add_image, rid, "x.jpg", "unbekannt")


def test_shopping_items(tx):
    a = tx(shopping.add_item, summary="200 g Mehl", name="Mehl", amount=200, unit="g")
    b = tx(shopping.add_item, summary="Milch")
    tx(shopping.move_item, b["uid"], None)
    assert [i["summary"] for i in tx(shopping.list_items)] == ["Milch", "200 g Mehl"]
    tx(shopping.update_item, a["uid"], status="completed")
    assert tx(shopping.clear_completed) == 1
    assert len(tx(shopping.list_items)) == 1


# --- Async-Wrapper ----------------------------------------------------------------


async def test_database_async(tmp_path):
    db = Database(tmp_path / "async.db")
    await db.async_open()
    rid = await db.run(recipes.create_recipe, title="Async", data=SAMPLE)
    r = await db.run(recipes.get_recipe, rid)
    assert r["title"] == "Async"
    with pytest.raises(ValidationError):
        await db.run(recipes.create_recipe, title="", data=SAMPLE)
    # fehlgeschlagene Transaktion hat nichts hinterlassen
    assert await db.run(recipes.count_recipes) == 1
    await db.async_close()
