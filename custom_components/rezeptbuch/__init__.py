"""Rezeptbuch – eigenständige Rezeptdatenbank für Home Assistant."""

from __future__ import annotations

from datetime import datetime
import logging
from pathlib import Path

from homeassistant.const import EVENT_HOMEASSISTANT_STOP, Platform
from homeassistant.core import Event, HomeAssistant, callback
from homeassistant.exceptions import ConfigEntryNotReady
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.event import async_call_later, async_track_time_change
from homeassistant.helpers.typing import ConfigType

from .cleanup import async_cleanup_old_drafts, async_delete_orphan_images
from .const import (
    CLEANUP_FIRST_RUN_DELAY,
    CLEANUP_HOUR,
    CLEANUP_MINUTE,
    CONF_CREATE_DEFAULT_CATEGORIES,
    CONF_STORAGE_PATH,
    DATA_DEFAULT_CATEGORIES_CREATED,
    DEFAULT_STORAGE_DIR,
    DOMAIN,
)
from .coordinator import RezeptbuchCoordinator
from .db import Database
from .db.categories import create_default_tree
from .media_source import async_register_media_source, async_unregister_media_source
from .runtime import RezeptbuchConfigEntry, RezeptbuchRuntime
from .services import async_setup_services
from .storage import Storage

_LOGGER = logging.getLogger(__name__)

PLATFORMS: list[Platform] = [Platform.SENSOR, Platform.TODO]
CONFIG_SCHEMA = cv.config_entry_only_config_schema(DOMAIN)


async def async_setup(hass: HomeAssistant, config: ConfigType) -> bool:
    """Aktionen einmalig registrieren."""
    async_setup_services(hass)
    return True


def storage_for(hass: HomeAssistant, entry: RezeptbuchConfigEntry) -> Storage:
    """Speicherort aus den Optionen (relativ zum Konfigurationsordner)."""
    return Storage(Path(hass.config.path(entry.options.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_DIR))))


async def async_setup_entry(hass: HomeAssistant, entry: RezeptbuchConfigEntry) -> bool:
    """Datenbank öffnen, Plattformen laden, Aufräumen planen."""
    storage = storage_for(hass, entry)
    db = Database(storage.db_path)
    try:
        await hass.async_add_executor_job(storage.ensure_dirs)
        await db.async_open()
    except Exception as err:
        await db.async_close()
        raise ConfigEntryNotReady(f"Rezeptbuch-Datenbank nicht verfügbar: {err}") from err

    if entry.data.get(CONF_CREATE_DEFAULT_CATEGORIES) and not entry.data.get(DATA_DEFAULT_CATEGORIES_CREATED):
        created = await db.run(create_default_tree)
        _LOGGER.info("Rezeptbuch: %s Standard-Kategorien angelegt", created)
        hass.config_entries.async_update_entry(entry, data={**entry.data, DATA_DEFAULT_CATEGORIES_CREATED: True})

    runtime = RezeptbuchRuntime(db=db, storage=storage, options=dict(entry.options))
    coordinator = RezeptbuchCoordinator(hass, entry, db)
    runtime.coordinator = coordinator
    entry.runtime_data = runtime
    try:
        await coordinator.async_config_entry_first_refresh()
    except Exception:
        await db.async_close()
        raise

    async_register_media_source(hass)
    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)

    async def _async_cleanup(_now: datetime | None = None) -> None:
        try:
            await async_cleanup_old_drafts(hass, db, storage)
            await async_delete_orphan_images(hass, db, storage)
        except Exception:
            _LOGGER.exception("Rezeptbuch: Aufräumen fehlgeschlagen")

    # Nicht direkt beim Start, sondern verzögert – danach täglich nachts.
    entry.async_on_unload(async_call_later(hass, CLEANUP_FIRST_RUN_DELAY, _async_cleanup))
    entry.async_on_unload(
        async_track_time_change(hass, _async_cleanup, hour=CLEANUP_HOUR, minute=CLEANUP_MINUTE, second=0)
    )

    # Tageswechsel: Rezept des Tages sofort neu wählen
    @callback
    def _new_day(_now: datetime) -> None:
        entry.async_create_background_task(hass, coordinator.async_request_refresh(), f"{DOMAIN}_new_day")

    entry.async_on_unload(async_track_time_change(hass, _new_day, hour=0, minute=0, second=5))

    @callback
    def _on_stop(_event: Event) -> None:
        hass.async_create_task(db.async_close(), f"{DOMAIN}_close_db")

    entry.async_on_unload(hass.bus.async_listen_once(EVENT_HOMEASSISTANT_STOP, _on_stop))
    entry.async_on_unload(entry.add_update_listener(_async_options_updated))
    return True


async def _async_options_updated(hass: HomeAssistant, entry: RezeptbuchConfigEntry) -> None:
    """Optionen geändert → neu laden (Speicherpfad, Sensoren, …)."""
    await hass.config_entries.async_reload(entry.entry_id)


async def async_unload_entry(hass: HomeAssistant, entry: RezeptbuchConfigEntry) -> bool:
    """Plattformen entladen, Media Source abmelden, Datenbank schließen."""
    unloaded = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unloaded:
        async_unregister_media_source(hass)
        await entry.runtime_data.db.async_close()
    return unloaded
