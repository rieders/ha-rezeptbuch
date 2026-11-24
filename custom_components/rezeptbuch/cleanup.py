"""Aufräumen: Entwürfe verwerfen, alte Entwürfe löschen, verwaiste Bilder finden.

Dateien werden immer erst *nach* dem Commit der DB-Transaktion gelöscht
(Database.run committet beim Verlassen). Schlägt die Transaktion fehl, bleiben
die Dateien erhalten.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
import logging
import time

from homeassistant.core import HomeAssistant

from .db import Database
from .db.drafts import delete_draft, delete_drafts_older_than, referenced_image_paths
from .images import async_delete_images
from .storage import Storage

_LOGGER = logging.getLogger(__name__)

DRAFT_MAX_AGE_DAYS = 14
# Dateien jünger als das gelten nie als verwaist: zwischen Speichern eines
# Bildes und dem Commit des zugehörigen Entwurfs liegt ein kurzes Zeitfenster.
ORPHAN_MIN_AGE_SECONDS = 3600


@dataclass(frozen=True)
class CleanupResult:
    """Ergebnis einer Aufräumaktion."""

    drafts: int = 0
    files: tuple[str, ...] = ()


async def async_discard_draft(hass: HomeAssistant, db: Database, storage: Storage, draft_id: int) -> CleanupResult:
    """Entwurf verwerfen und seine Bilddateien löschen."""
    paths = await db.run(delete_draft, draft_id)  # committet
    await async_delete_images(hass, storage, paths)
    return CleanupResult(drafts=1, files=tuple(paths))


async def async_cleanup_old_drafts(
    hass: HomeAssistant,
    db: Database,
    storage: Storage,
    *,
    max_age_days: int = DRAFT_MAX_AGE_DAYS,
    now: datetime | None = None,
) -> CleanupResult:
    """Unbestätigte Entwürfe älter als `max_age_days` samt Bildern löschen."""
    cutoff = (now or datetime.now(UTC)) - timedelta(days=max_age_days)
    count, paths = await db.run(delete_drafts_older_than, cutoff.isoformat(timespec="seconds"))
    await async_delete_images(hass, storage, paths)
    if count:
        _LOGGER.info("Rezeptbuch: %s alte Import-Entwürfe gelöscht", count)
    return CleanupResult(drafts=count, files=tuple(paths))


async def async_find_orphan_images(
    hass: HomeAssistant,
    db: Database,
    storage: Storage,
    *,
    min_age_seconds: int = ORPHAN_MIN_AGE_SECONDS,
) -> list[str]:
    """Bilddateien ohne DB-Bezug (relativ zum Bilderverzeichnis), älteste zuerst."""
    referenced = await db.run(referenced_image_paths)

    def _scan() -> list[str]:
        root = storage.images_dir
        if not root.is_dir():
            return []
        limit = time.time() - min_age_seconds
        found: list[tuple[float, str]] = []
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            mtime = path.stat().st_mtime
            if mtime > limit:
                continue
            rel = path.relative_to(root).as_posix()
            if rel not in referenced:
                found.append((mtime, rel))
        return [rel for _, rel in sorted(found)]

    return await hass.async_add_executor_job(_scan)


async def async_delete_orphan_images(
    hass: HomeAssistant,
    db: Database,
    storage: Storage,
    *,
    min_age_seconds: int = ORPHAN_MIN_AGE_SECONDS,
) -> list[str]:
    """Verwaiste Bilddateien löschen; gibt die gelöschten Pfade zurück."""
    orphans = await async_find_orphan_images(hass, db, storage, min_age_seconds=min_age_seconds)
    await async_delete_images(hass, storage, orphans)
    if orphans:
        _LOGGER.info("Rezeptbuch: %s verwaiste Bilddateien gelöscht", len(orphans))
    return orphans
