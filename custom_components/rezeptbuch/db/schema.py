"""DB-Schema und Migrationen (schema_version-Tabelle).

Jede Migration ist eine Liste von SQL-Anweisungen; neue Migrationen werden
hinten an MIGRATIONS angehängt, bestehende nie verändert.
"""

from __future__ import annotations

import logging
import sqlite3

_LOGGER = logging.getLogger(__name__)

MIGRATION_1 = [
    """
    CREATE TABLE recipes (
        id                 INTEGER PRIMARY KEY,
        title              TEXT NOT NULL,
        description        TEXT,
        servings           REAL,
        prep_time          INTEGER,
        cook_time          INTEGER,
        total_time         INTEGER,
        source_url         TEXT,
        source_key         TEXT,
        source_type        TEXT NOT NULL DEFAULT 'manual'
                           CHECK (source_type IN ('url', 'photo', 'manual')),
        image              TEXT,
        default_version_id INTEGER REFERENCES recipe_versions(id) ON DELETE SET NULL,
        created            TEXT NOT NULL,
        updated            TEXT NOT NULL
    )
    """,
    "CREATE INDEX ix_recipes_source_key ON recipes(source_key)",
    "CREATE INDEX ix_recipes_title ON recipes(title COLLATE NOCASE)",
    """
    CREATE TABLE recipe_versions (
        id           INTEGER PRIMARY KEY,
        recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        version_no   INTEGER NOT NULL,
        label        TEXT NOT NULL,
        data         TEXT NOT NULL,
        is_original  INTEGER NOT NULL DEFAULT 0 CHECK (is_original IN (0, 1)),
        change_note  TEXT,
        cook_log_id  INTEGER REFERENCES cook_log(id) ON DELETE SET NULL,
        user_id      TEXT,
        created      TEXT NOT NULL,
        UNIQUE (recipe_id, version_no)
    )
    """,
    "CREATE UNIQUE INDEX ux_versions_original ON recipe_versions(recipe_id) WHERE is_original = 1",
    # Original darf nicht gelöscht werden – außer das Rezept selbst ist schon weg
    # (ON DELETE CASCADE beim Löschen des Rezepts).
    """
    CREATE TRIGGER trg_versions_protect_original_delete
    BEFORE DELETE ON recipe_versions
    WHEN OLD.is_original = 1
         AND EXISTS (SELECT 1 FROM recipes WHERE id = OLD.recipe_id)
    BEGIN
        SELECT RAISE(ABORT, 'Die Originalversion kann nicht gelöscht werden');
    END
    """,
    # Original darf inhaltlich nicht verändert werden (cook_log_id SET NULL bleibt erlaubt)
    """
    CREATE TRIGGER trg_versions_protect_original_update
    BEFORE UPDATE ON recipe_versions
    WHEN OLD.is_original = 1 AND (
            NEW.data IS NOT OLD.data
         OR NEW.label IS NOT OLD.label
         OR NEW.is_original IS NOT OLD.is_original
         OR NEW.recipe_id IS NOT OLD.recipe_id
         OR NEW.version_no IS NOT OLD.version_no
         OR NEW.change_note IS NOT OLD.change_note
         OR NEW.created IS NOT OLD.created
         OR NEW.user_id IS NOT OLD.user_id)
    BEGIN
        SELECT RAISE(ABORT, 'Die Originalversion kann nicht verändert werden');
    END
    """,
    """
    CREATE TABLE annotations (
        id           INTEGER PRIMARY KEY,
        recipe_id    INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        version_id   INTEGER REFERENCES recipe_versions(id) ON DELETE CASCADE,
        target_type  TEXT NOT NULL CHECK (target_type IN ('ingredient', 'step', 'recipe')),
        target_index INTEGER,
        text         TEXT NOT NULL,
        user_id      TEXT,
        created      TEXT NOT NULL
    )
    """,
    "CREATE INDEX ix_annotations_recipe ON annotations(recipe_id, version_id)",
    """
    CREATE TABLE cook_log (
        id         INTEGER PRIMARY KEY,
        recipe_id  INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        version_id INTEGER REFERENCES recipe_versions(id) ON DELETE SET NULL,
        cooked_at  TEXT,
        stars      REAL CHECK (stars IS NULL OR (stars BETWEEN 0.5 AND 5.0
                                AND stars * 2 = CAST(stars * 2 AS INTEGER))),
        comment    TEXT,
        servings   REAL,
        photo      TEXT,
        user_id    TEXT NOT NULL DEFAULT 'system',
        created    TEXT NOT NULL
    )
    """,
    "CREATE INDEX ix_cook_log_recipe ON cook_log(recipe_id, cooked_at)",
    """
    CREATE TABLE categories (
        id        INTEGER PRIMARY KEY,
        parent_id INTEGER REFERENCES categories(id) ON DELETE RESTRICT,
        name      TEXT NOT NULL,
        icon      TEXT,
        color     TEXT,
        position  INTEGER NOT NULL DEFAULT 0,
        created   TEXT NOT NULL
    )
    """,
    "CREATE UNIQUE INDEX ux_categories_name ON categories(IFNULL(parent_id, 0), name COLLATE NOCASE)",
    "CREATE INDEX ix_categories_parent ON categories(parent_id, position)",
    """
    CREATE TABLE recipe_categories (
        recipe_id   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        category_id INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        PRIMARY KEY (recipe_id, category_id)
    )
    """,
    "CREATE INDEX ix_recipe_categories_cat ON recipe_categories(category_id)",
    """
    CREATE TABLE tags (
        id   INTEGER PRIMARY KEY,
        name TEXT NOT NULL UNIQUE COLLATE NOCASE
    )
    """,
    """
    CREATE TABLE recipe_tags (
        recipe_id INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        tag_id    INTEGER NOT NULL REFERENCES tags(id) ON DELETE CASCADE,
        PRIMARY KEY (recipe_id, tag_id)
    )
    """,
    """
    CREATE TABLE category_mappings (
        source_keyword TEXT PRIMARY KEY COLLATE NOCASE,
        category_id    INTEGER NOT NULL REFERENCES categories(id) ON DELETE CASCADE,
        hits           INTEGER NOT NULL DEFAULT 0,
        updated        TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE recipe_images (
        id          INTEGER PRIMARY KEY,
        recipe_id   INTEGER NOT NULL REFERENCES recipes(id) ON DELETE CASCADE,
        path        TEXT NOT NULL,
        kind        TEXT NOT NULL CHECK (kind IN ('cover', 'source_photo', 'cook_photo')),
        position    INTEGER NOT NULL DEFAULT 0,
        cook_log_id INTEGER REFERENCES cook_log(id) ON DELETE SET NULL,
        created     TEXT NOT NULL
    )
    """,
    "CREATE INDEX ix_recipe_images_recipe ON recipe_images(recipe_id, kind, position)",
    """
    CREATE TABLE import_drafts (
        id          INTEGER PRIMARY KEY,
        source_type TEXT NOT NULL,
        data        TEXT NOT NULL,
        image_paths TEXT NOT NULL DEFAULT '[]',
        user_id     TEXT,
        created     TEXT NOT NULL,
        updated     TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE shopping_items (
        id          INTEGER PRIMARY KEY,
        uid         TEXT NOT NULL UNIQUE,
        name        TEXT NOT NULL,
        amount      REAL,
        amount_max  REAL,
        unit        TEXT,
        note        TEXT,
        summary     TEXT NOT NULL,
        description TEXT,
        status      TEXT NOT NULL DEFAULT 'needs_action'
                    CHECK (status IN ('needs_action', 'completed')),
        recipe_id   INTEGER REFERENCES recipes(id) ON DELETE SET NULL,
        sources     TEXT NOT NULL DEFAULT '[]',
        position    INTEGER NOT NULL DEFAULT 0,
        created     TEXT NOT NULL,
        updated     TEXT NOT NULL
    )
    """,
    # Normale (nicht contentlose) FTS5-Tabelle, rowid = recipe_id
    """
    CREATE VIRTUAL TABLE recipe_fts USING fts5(
        title, ingredients, tags, categories,
        tokenize = "unicode61 remove_diacritics 2"
    )
    """,
    """
    CREATE TRIGGER trg_recipes_fts_delete AFTER DELETE ON recipes
    BEGIN
        DELETE FROM recipe_fts WHERE rowid = OLD.id;
    END
    """,
]

MIGRATION_2 = [
    """
    CREATE TABLE offers (
        id          INTEGER PRIMARY KEY,
        provider    TEXT NOT NULL,
        external_id TEXT NOT NULL,
        retailer    TEXT NOT NULL,
        product     TEXT NOT NULL,
        brand       TEXT,
        price       REAL,
        old_price   REAL,
        unit        TEXT,
        unit_price  TEXT,
        valid_from  TEXT,
        valid_to    TEXT,
        image       TEXT,
        raw         TEXT,
        fetched     TEXT NOT NULL,
        UNIQUE (provider, external_id)
    )
    """,
    "CREATE INDEX ix_offers_valid ON offers(valid_to)",
    "CREATE INDEX ix_offers_retailer ON offers(retailer)",
    """
    CREATE TABLE offer_mappings (
        id              INTEGER PRIMARY KEY,
        ingredient_name TEXT NOT NULL COLLATE NOCASE,
        product_pattern TEXT NOT NULL COLLATE NOCASE,
        accepted        INTEGER NOT NULL CHECK (accepted IN (0, 1)),
        hits            INTEGER NOT NULL DEFAULT 1,
        updated         TEXT NOT NULL,
        UNIQUE (ingredient_name, product_pattern)
    )
    """,
    """
    CREATE TABLE watchlist (
        id        INTEGER PRIMARY KEY,
        query     TEXT NOT NULL,
        max_price REAL,
        retailers TEXT NOT NULL DEFAULT '[]',
        user_id   TEXT,
        created   TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE watch_hits (
        watch_id    INTEGER NOT NULL REFERENCES watchlist(id) ON DELETE CASCADE,
        provider    TEXT NOT NULL,
        external_id TEXT NOT NULL,
        valid_to    TEXT,
        notified_at TEXT NOT NULL,
        PRIMARY KEY (watch_id, provider, external_id)
    )
    """,
    "ALTER TABLE shopping_items ADD COLUMN offer_id INTEGER REFERENCES offers(id) ON DELETE SET NULL",
]

MIGRATIONS: list[list[str]] = [MIGRATION_1, MIGRATION_2]
SCHEMA_VERSION = len(MIGRATIONS)


class SchemaTooNewError(RuntimeError):
    """Die Datenbank stammt von einer neueren Version der Integration."""


def get_schema_version(conn: sqlite3.Connection) -> int:
    """Aktuelle Schema-Version (0 = leere Datenbank)."""
    conn.execute("CREATE TABLE IF NOT EXISTS schema_version (version INTEGER NOT NULL)")
    row = conn.execute("SELECT MAX(version) FROM schema_version").fetchone()
    return int(row[0] or 0)


def migrate(conn: sqlite3.Connection) -> int:
    """Alle ausstehenden Migrationen ausführen. Gibt die neue Version zurück."""
    current = get_schema_version(conn)
    if current > SCHEMA_VERSION:
        raise SchemaTooNewError(f"Datenbank-Schema {current} ist neuer als unterstützt ({SCHEMA_VERSION})")
    for version in range(current + 1, SCHEMA_VERSION + 1):
        _LOGGER.info("Rezeptbuch: Migration auf Schema-Version %s", version)
        conn.execute("BEGIN IMMEDIATE")
        try:
            for statement in MIGRATIONS[version - 1]:
                conn.execute(statement)
            conn.execute("INSERT INTO schema_version (version) VALUES (?)", (version,))
            conn.execute("COMMIT")
        except Exception:
            conn.execute("ROLLBACK")
            raise
    return SCHEMA_VERSION
