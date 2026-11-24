"""Diagnose: nur Zähler, Schema-Version und Optionen – keine Rezeptinhalte."""

from __future__ import annotations

import sqlite3
from typing import Any

from homeassistant.components.diagnostics import async_redact_data
from homeassistant.core import HomeAssistant

from .const import CONF_IDEA_SENSORS
from .db.schema import SCHEMA_VERSION, get_schema_version
from .runtime import RezeptbuchConfigEntry

# Für spätere Optionen (Angebote) – Zugangsdaten nie ausgeben
TO_REDACT = {"api_key", "token", "password", "zip_code", "plz"}

_COUNT_TABLES = (
    "recipes",
    "recipe_versions",
    "annotations",
    "cook_log",
    "categories",
    "recipe_categories",
    "tags",
    "category_mappings",
    "recipe_images",
    "import_drafts",
    "shopping_items",
    "offers",
    "offer_mappings",
    "watchlist",
)


def _counts(conn: sqlite3.Connection) -> dict[str, Any]:
    counts = {t: conn.execute(f"SELECT COUNT(*) FROM {t}").fetchone()[0] for t in _COUNT_TABLES}
    counts["recipes_by_source"] = dict(conn.execute("SELECT source_type, COUNT(*) FROM recipes GROUP BY source_type"))
    counts["distinct_users_rating"] = conn.execute("SELECT COUNT(DISTINCT user_id) FROM cook_log").fetchone()[0]
    return {
        "schema_version": get_schema_version(conn),
        "schema_version_expected": SCHEMA_VERSION,
        "sqlite_version": sqlite3.sqlite_version,
        "counts": counts,
    }


async def async_get_config_entry_diagnostics(hass: HomeAssistant, entry: RezeptbuchConfigEntry) -> dict[str, Any]:
    """Diagnosedaten für den Eintrag."""
    runtime = entry.runtime_data
    db_info = await runtime.db.run(_counts)

    def _files() -> dict[str, Any]:
        images = [p for p in runtime.storage.images_dir.rglob("*") if p.is_file()]
        db_path = runtime.storage.db_path
        return {
            "image_files": len(images),
            "image_bytes": sum(p.stat().st_size for p in images),
            "db_bytes": db_path.stat().st_size if db_path.exists() else 0,
        }

    options = dict(entry.options)
    # Namen der Ideen-Sensoren sind Nutzereingaben – nur Anzahl und Zeitraum ausgeben
    ideas = options.pop(CONF_IDEA_SENSORS, [])
    options["idea_sensors"] = [{"period": i.get("period")} for i in ideas]
    coordinator = runtime.coordinator
    return {
        "entry": {
            "data": async_redact_data(dict(entry.data), TO_REDACT),
            "options": async_redact_data(options, TO_REDACT),
        },
        "database": db_info,
        "files": await hass.async_add_executor_job(_files),
        "coordinator": {
            "last_update_success": coordinator.last_update_success if coordinator else None,
            "picks": sorted((coordinator.data or {}).get("picks", {})) if coordinator else [],
        },
    }
