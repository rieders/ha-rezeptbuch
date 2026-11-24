"""DataUpdateCoordinator: Zählungen, Rezept des Tages, Ideen-Sensoren."""

from __future__ import annotations

from datetime import date, timedelta
import logging
import sqlite3
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator
from homeassistant.util import dt as dt_util

from .const import (
    CONF_DAILY_CATEGORY_IDS,
    CONF_IDEA_SENSORS,
    CONF_RATING_WEIGHT,
    CONF_RECENCY_WEIGHT,
    DEFAULT_RATING_WEIGHT,
    DEFAULT_RECENCY_WEIGHT,
    DOMAIN,
    IDEA_CATEGORY_ID,
    IDEA_ID,
    IDEA_PERIOD,
    IMAGE_URL_PREFIX,
    PERIOD_DAILY,
)
from .db import Database
from .db.categories import descendant_ids, get_tree
from .db.recipes import search_recipes
from .suggestions import period_id, pick

_LOGGER = logging.getLogger(__name__)

UPDATE_INTERVAL = timedelta(minutes=30)
DAILY_KEY = "daily"


def recipe_summary(item: dict[str, Any]) -> dict[str, Any]:
    """Kurzfassung eines Rezepts für Sensor-Attribute und Aktionen."""
    return {
        "recipe_id": item["id"],
        "title": item["title"],
        "image_url": f"{IMAGE_URL_PREFIX}{item['image']}" if item.get("image") else None,
        "servings": item.get("servings"),
        "prep_time": item.get("prep_time"),
        "cook_time": item.get("cook_time"),
        "total_time": item.get("total_time"),
        "avg_stars": item.get("avg_stars"),
        "rating_count": item.get("rating_count") or 0,
        "cooked_count": item.get("cooked_count") or 0,
        "last_cooked": item.get("last_cooked"),
        "tags": item.get("tags") or [],
    }


def _candidates(conn: sqlite3.Connection, category_ids: list[int]) -> list[dict[str, Any]]:
    if not category_ids:
        return search_recipes(conn, limit=None)["items"]
    ids: set[int] = set()
    for cid in category_ids:
        try:
            ids.update(descendant_ids(conn, cid))
        except sqlite3.Error:
            continue
    if not ids:
        return []
    allowed = {
        r[0]
        for r in conn.execute(
            f"SELECT DISTINCT recipe_id FROM recipe_categories WHERE category_id IN ({','.join('?' * len(ids))})",
            sorted(ids),
        )
    }
    return [item for item in search_recipes(conn, limit=None)["items"] if item["id"] in allowed]


class RezeptbuchCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Hält die Daten für alle Sensoren."""

    def __init__(self, hass: HomeAssistant, entry: Any, db: Database) -> None:
        """Initialisieren."""
        super().__init__(hass, _LOGGER, config_entry=entry, name=DOMAIN, update_interval=UPDATE_INTERVAL)
        self.db = db
        # Auswahl je Sensor: key → (Zeitraum, recipe_id) – bleibt im Zeitraum stabil
        self._picks: dict[str, tuple[str, int]] = {}

    @property
    def _options(self) -> dict[str, Any]:
        return dict(self.config_entry.options) if self.config_entry else {}

    def _slots(self) -> list[tuple[str, list[int], str]]:
        """(Schlüssel, Kategorie-IDs, Zeitraum) für Tagesrezept und Ideen."""
        opts = self._options
        slots = [(DAILY_KEY, [int(c) for c in opts.get(CONF_DAILY_CATEGORY_IDS) or []], PERIOD_DAILY)]
        for idea in opts.get(CONF_IDEA_SENSORS) or []:
            slots.append((f"idea_{idea[IDEA_ID]}", [int(idea[IDEA_CATEGORY_ID])], idea.get(IDEA_PERIOD, PERIOD_DAILY)))
        return slots

    async def _async_update_data(self) -> dict[str, Any]:
        today = dt_util.now().date()
        return await self.db.run(self._compute, today)

    def _compute(self, conn: sqlite3.Connection, today: date) -> dict[str, Any]:
        """Läuft im DB-Thread."""
        opts = self._options
        rating_weight = float(opts.get(CONF_RATING_WEIGHT, DEFAULT_RATING_WEIGHT))
        recency_weight = float(opts.get(CONF_RECENCY_WEIGHT, DEFAULT_RECENCY_WEIGHT))
        tree = get_tree(conn)
        picks: dict[str, dict[str, Any] | None] = {}
        for key, category_ids, period in self._slots():
            pid = period_id(today, period)
            candidates = _candidates(conn, category_ids)
            by_id = {c["id"]: c for c in candidates}
            previous = self._picks.get(key)
            if previous and previous[0] == pid and previous[1] in by_id:
                chosen = by_id[previous[1]]
            else:
                chosen = pick(
                    candidates,
                    seed=f"{pid}:{key}",
                    today=today,
                    rating_weight=rating_weight,
                    recency_weight=recency_weight,
                )
            if chosen is None:
                self._picks.pop(key, None)
                picks[key] = None
            else:
                self._picks[key] = (pid, chosen["id"])
                picks[key] = recipe_summary(chosen)
        return {
            "total": tree["total"],
            "uncategorized": tree["uncategorized"],
            "by_root": {node["name"]: node["count_total"] for node in tree["categories"]},
            "picks": picks,
            "date": today.isoformat(),
        }
