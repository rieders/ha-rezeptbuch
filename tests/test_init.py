"""Setup, Unload, Reload, Standard-Kategorien, zeitgesteuertes Aufräumen."""

from __future__ import annotations

from datetime import timedelta
from pathlib import Path
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.components import media_source
from homeassistant.components.media_source import Unresolvable
from homeassistant.config_entries import ConfigEntryState
from homeassistant.const import EVENT_HOMEASSISTANT_STOP, STATE_UNAVAILABLE
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ServiceValidationError
from homeassistant.setup import async_setup_component
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.rezeptbuch.const import (
    CONF_CREATE_DEFAULT_CATEGORIES,
    CONF_STORAGE_PATH,
    DATA_DEFAULT_CATEGORIES_CREATED,
    DOMAIN,
)
from custom_components.rezeptbuch.db import categories as cats
from custom_components.rezeptbuch.media_source import _platforms
from custom_components.rezeptbuch.runtime import async_get_runtime


async def test_setup_creates_db_and_default_tree(
    hass: HomeAssistant, rb_entry: MockConfigEntry, tmp_path: Path
) -> None:
    assert rb_entry.state is ConfigEntryState.LOADED
    assert (tmp_path / "rezeptbuch" / "rezepte.db").is_file()
    assert (tmp_path / "rezeptbuch" / "images").is_dir()
    runtime = rb_entry.runtime_data
    tree = await runtime.db.run(cats.get_tree)
    assert [c["name"] for c in tree["categories"]] == ["Kochen", "Backen", "Getränke"]
    assert rb_entry.data[DATA_DEFAULT_CATEGORIES_CREATED] is True
    assert hass.states.get("sensor.rezeptbuch_anzahl_rezepte").state == "0"
    assert hass.states.get("sensor.rezeptbuch_rezept_des_tages") is not None
    assert hass.states.get("todo.rezeptbuch_einkaufsliste").state == "0"
    assert hass.services.has_service(DOMAIN, "import_url")


async def test_default_tree_only_on_first_setup(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    runtime = rb_entry.runtime_data
    for cat in (await runtime.db.run(cats.get_tree))["categories"]:
        await runtime.db.run(cats.delete_category, cat["id"])
    # Unterkategorien sind jetzt Wurzeln – alle löschen
    while roots := (await runtime.db.run(cats.get_tree))["categories"]:
        for cat in roots:
            await runtime.db.run(cats.delete_category, cat["id"])
    assert await hass.config_entries.async_reload(rb_entry.entry_id)
    await hass.async_block_till_done()
    assert (await rb_entry.runtime_data.db.run(cats.get_tree))["categories"] == []


async def test_without_default_categories(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None
) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert (await entry.runtime_data.db.run(cats.get_tree))["categories"] == []
    assert await hass.config_entries.async_unload(entry.entry_id)


async def _resolve(hass: HomeAssistant, rel: str):
    return await media_source.async_resolve_media(hass, f"media-source://{DOMAIN}/{rel}", None)


async def test_unload_and_reload(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    assert await async_setup_component(hass, "media_source", {})
    await hass.async_block_till_done()
    # media_source wurde nach uns geladen → beim nächsten Setup registrieren
    assert await hass.config_entries.async_reload(rb_entry.entry_id)
    await hass.async_block_till_done()
    storage = rb_entry.runtime_data.storage
    rel = await hass.async_add_executor_job(storage.write_image, b"JPEG-Testdaten", "jpg")
    assert (await _resolve(hass, rel)).path == storage.image_path(rel)
    db = rb_entry.runtime_data.db

    assert await hass.config_entries.async_unload(rb_entry.entry_id)
    await hass.async_block_till_done()
    assert rb_entry.state is ConfigEntryState.NOT_LOADED
    assert db.closed
    assert async_get_runtime(hass) is None
    platforms = _platforms(hass)  # nur ältere HA-Versionen (2026.2) haben ein Dict
    if platforms is not None:
        assert DOMAIN not in platforms
    with pytest.raises(Unresolvable):
        await _resolve(hass, rel)
    assert hass.states.get("sensor.rezeptbuch_anzahl_rezepte").state == STATE_UNAVAILABLE
    with pytest.raises(ServiceValidationError) as err:
        await hass.services.async_call(DOMAIN, "search", {}, blocking=True, return_response=True)
    assert err.value.translation_key == "not_loaded"

    # Neu laden ohne HA-Neustart
    assert await hass.config_entries.async_setup(rb_entry.entry_id)
    await hass.async_block_till_done()
    assert rb_entry.state is ConfigEntryState.LOADED
    assert not rb_entry.runtime_data.db.closed
    assert (await _resolve(hass, rel)).path == storage.image_path(rel)
    response = await hass.services.async_call(DOMAIN, "search", {}, blocking=True, return_response=True)
    assert response == {"total": 0, "recipes": []}


async def test_setup_retries_when_db_fails(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None
) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: True})
    entry.add_to_hass(hass)
    with patch("custom_components.rezeptbuch.Database.async_open", side_effect=OSError("Datenträger voll")):
        await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
    assert entry.state is ConfigEntryState.SETUP_RETRY


async def test_storage_path_option(hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(
        domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False}, options={CONF_STORAGE_PATH: "daten/rezepte"}
    )
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    assert (tmp_path / "daten" / "rezepte" / "rezepte.db").is_file()
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_ha_stop_closes_db(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    db = rb_entry.runtime_data.db
    hass.bus.async_fire(EVENT_HOMEASSISTANT_STOP)
    await hass.async_block_till_done()
    assert db.closed
    # Späteres Unload darf nicht scheitern
    assert await hass.config_entries.async_unload(rb_entry.entry_id)


async def test_cleanup_is_delayed_then_daily(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None, freezer: FrozenDateTimeFactory
) -> None:
    hass.config.config_dir = str(tmp_path)
    freezer.move_to(dt_util.now().replace(hour=10, minute=0, second=0, microsecond=0))
    drafts_mock = AsyncMock()
    orphans_mock = AsyncMock(return_value=[])
    with (
        patch("custom_components.rezeptbuch.async_cleanup_old_drafts", drafts_mock),
        patch("custom_components.rezeptbuch.async_delete_orphan_images", orphans_mock),
    ):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert drafts_mock.await_count == 0  # nicht direkt beim Start

        freezer.tick(timedelta(minutes=14))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert drafts_mock.await_count == 0

        freezer.tick(timedelta(minutes=2))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert drafts_mock.await_count == 1 and orphans_mock.await_count == 1

        # nächster Lauf: 03:30 Uhr
        freezer.move_to(dt_util.now().replace(hour=3, minute=30, second=0) + timedelta(days=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert drafts_mock.await_count == 2

        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.async_block_till_done()
        # nach dem Unload keine Läufe mehr
        freezer.tick(timedelta(days=1))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
        assert drafts_mock.await_count == 2


async def test_cleanup_errors_are_logged_not_raised(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None, freezer: FrozenDateTimeFactory, caplog
) -> None:
    hass.config.config_dir = str(tmp_path)
    with patch("custom_components.rezeptbuch.async_cleanup_old_drafts", AsyncMock(side_effect=OSError("kaputt"))):
        entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False})
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        freezer.tick(timedelta(minutes=16))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert "Aufräumen fehlgeschlagen" in caplog.text
    assert entry.state is ConfigEntryState.LOADED
    assert await hass.config_entries.async_unload(entry.entry_id)
