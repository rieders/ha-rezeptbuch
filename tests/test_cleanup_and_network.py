"""Private Netzwerkadressen (Option), Aufräumen von Entwürfen/Bildern, Bildverarbeitung im Executor."""

from __future__ import annotations

from collections.abc import AsyncIterator
from datetime import UTC, datetime, timedelta
import os
from pathlib import Path
import threading
import time
from unittest.mock import patch

from homeassistant.core import HomeAssistant
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rezeptbuch.cleanup import (
    async_cleanup_old_drafts,
    async_delete_orphan_images,
    async_discard_draft,
    async_find_orphan_images,
)
from custom_components.rezeptbuch.db import Database, categories as cats, drafts, recipes, transaction
from custom_components.rezeptbuch.errors import BlockedAddress, DraftNotFound
from custom_components.rezeptbuch.importer.url import async_import_url
from custom_components.rezeptbuch.net import async_safe_get, is_allowed_ip
from custom_components.rezeptbuch.storage import Storage

from .test_url_import import CK_URL, HTML, fixture_html, jpeg_bytes, mock_chefkoch

PUBLIC_IP = "93.184.215.14"


@pytest.fixture
def resolver():
    with patch("custom_components.rezeptbuch.net.async_resolve_host", return_value=[PUBLIC_IP]) as mock:
        yield mock


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[Database]:
    database = Database(tmp_path / "rezepte.db")
    await database.async_open()
    await database.run(cats.create_default_tree)
    yield database
    await database.async_close()


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    s = Storage(tmp_path / "rezeptbuch")
    s.ensure_dirs()
    return s


# --- Punkt 2: Private Netzwerkadressen ------------------------------------------------


@pytest.mark.parametrize(
    ("ip", "default", "with_private"),
    [
        ("93.184.215.14", True, True),
        ("192.168.178.20", False, True),
        ("10.0.0.5", False, True),
        ("172.20.1.1", False, True),
        ("100.101.102.103", False, True),  # Tailscale/CGNAT
        ("fd12:3456::1", False, True),  # IPv6 ULA
        ("127.0.0.1", False, False),
        ("127.8.8.8", False, False),
        ("::1", False, False),
        ("::ffff:127.0.0.1", False, False),
        ("0.0.0.0", False, False),
        ("169.254.169.254", False, False),  # Cloud-Metadaten / Link-Local
        ("fe80::1", False, False),
        ("224.0.0.251", False, False),
        ("240.0.0.1", False, False),
    ],
)
def test_is_allowed_ip(ip: str, default: bool, with_private: bool) -> None:
    assert is_allowed_ip(ip) is default
    assert is_allowed_ip(ip, allow_private=True) is with_private


async def test_lan_blocked_by_default(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver) -> None:
    resolver.return_value = ["192.168.178.30"]
    for url in ("http://192.168.178.30:9000/rezept", "http://mealie.local/r/1", "http://rezepte.example.org/"):
        with pytest.raises(BlockedAddress):
            await async_safe_get(hass, url)
    assert aioclient_mock.call_count == 0


async def test_lan_allowed_with_option(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver) -> None:
    resolver.return_value = ["192.168.178.30"]
    aioclient_mock.get("http://192.168.178.30:9000/rezept", text="ok")
    aioclient_mock.get("http://mealie.local/r/1", text="ok")
    for url in ("http://192.168.178.30:9000/rezept", "http://mealie.local/r/1"):
        result = await async_safe_get(hass, url, allow_private=True)
        assert result.body == b"ok"


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1:8123/api/states",
        "http://localhost:8123/",
        "http://homeassistant.localhost/",
        "http://[::1]/",
        "http://[::ffff:127.0.0.1]/",
        "http://169.254.169.254/latest/meta-data",
        "http://0.0.0.0:8123/",
    ],
)
async def test_loopback_always_blocked(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, url: str) -> None:
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, url, allow_private=True)
    assert aioclient_mock.call_count == 0


async def test_hostname_resolving_to_loopback_blocked_with_option(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver
) -> None:
    resolver.return_value = ["127.0.0.1"]
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, "http://mein-ha.example.org/", allow_private=True)


async def test_redirect_from_lan_to_loopback_blocked(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver
) -> None:
    aioclient_mock.get("http://192.168.1.5/r", status=302, headers={"Location": "http://127.0.0.1:8123/"})
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, "http://192.168.1.5/r", allow_private=True)


async def test_url_import_from_lan_with_option(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver, db: Database, storage: Storage
) -> None:
    url = "http://192.168.178.30:9000/g/home/r/linsensuppe"
    aioclient_mock.get(url, text=fixture_html("blog_linsensuppe.html"), headers=HTML)
    aioclient_mock.get(
        "https://www.mein-kuechenblog.de/wp-content/uploads/linsensuppe.jpg",
        content=jpeg_bytes(),
        headers={"Content-Type": "image/jpeg"},
    )
    with pytest.raises(BlockedAddress):
        await async_import_url(hass, db, storage, url)
    result = await async_import_url(hass, db, storage, url, allow_private_networks=True)
    assert result["status"] == "draft"
    assert result["draft"]["data"]["title"] == "Rote Linsensuppe mit Kokosmilch"


# --- Punkt 3: Aufräumen ------------------------------------------------------------------


async def _chefkoch_draft(hass, aioclient_mock, db, storage) -> dict:
    mock_chefkoch(aioclient_mock)
    return await async_import_url(hass, db, storage, CK_URL)


async def test_discard_draft_deletes_files(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver, db: Database, storage: Storage
) -> None:
    result = await _chefkoch_draft(hass, aioclient_mock, db, storage)
    image = result["draft"]["data"]["image"]
    assert storage.image_path(image).is_file()
    cleanup = await async_discard_draft(hass, db, storage, result["draft_id"])
    assert cleanup.files == (image,)
    assert not storage.image_path(image).exists()
    with pytest.raises(DraftNotFound):
        await db.run(drafts.get_draft, result["draft_id"])


async def test_discard_unknown_draft_keeps_files(hass: HomeAssistant, db: Database, storage: Storage) -> None:
    rel = storage.write_image(jpeg_bytes(), "jpg")
    with pytest.raises(DraftNotFound):
        await async_discard_draft(hass, db, storage, 999)
    assert storage.image_path(rel).is_file()


async def test_cleanup_old_drafts(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver, db: Database, storage: Storage
) -> None:
    old = await _chefkoch_draft(hass, aioclient_mock, db, storage)
    young = await async_import_url(hass, db, storage, CK_URL, allow_duplicate=True)

    def _age(conn):
        with transaction(conn):
            conn.execute(
                "UPDATE import_drafts SET updated = ? WHERE id = ?",
                ((datetime.now(UTC) - timedelta(days=15)).isoformat(timespec="seconds"), old["draft_id"]),
            )

    await db._submit(_age, db.conn)
    result = await async_cleanup_old_drafts(hass, db, storage)
    assert result.drafts == 1
    assert not storage.image_path(old["draft"]["data"]["image"]).exists()
    assert storage.image_path(young["draft"]["data"]["image"]).is_file()
    assert [d["id"] for d in await db.run(drafts.list_drafts)] == [young["draft_id"]]


async def test_orphan_images(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, resolver, db: Database, storage: Storage
) -> None:
    result = await _chefkoch_draft(hass, aioclient_mock, db, storage)
    draft_image = result["draft"]["data"]["image"]
    recipe_image = storage.write_image(jpeg_bytes(), "jpg")
    await db.run(recipes.create_recipe, title="Mit Bild", data={}, image=recipe_image)
    orphan = storage.write_image(jpeg_bytes(), "jpg")
    fresh_orphan = storage.write_image(jpeg_bytes(), "jpg")
    leftover_tmp = storage.images_dir / "ab" / "halb.jpg.tmp"
    leftover_tmp.parent.mkdir(parents=True, exist_ok=True)
    leftover_tmp.write_bytes(b"x")

    old = time.time() - 7200
    for rel in (draft_image, recipe_image, orphan):
        os.utime(storage.image_path(rel), (old, old))
    os.utime(leftover_tmp, (old, old))

    found = await async_find_orphan_images(hass, db, storage)
    assert sorted(found) == sorted([orphan, "ab/halb.jpg.tmp"])  # frische Datei geschützt
    deleted = await async_delete_orphan_images(hass, db, storage)
    assert sorted(deleted) == sorted(found)
    assert not storage.image_path(orphan).exists()
    for rel in (draft_image, recipe_image, fresh_orphan):
        assert storage.image_path(rel).is_file()


# --- Punkt 4: Bildverarbeitung nur im Executor ------------------------------------------


@pytest.fixture
def pil_thread_log():
    """Zeichnet für Image.open/Image.save den ausführenden Thread auf."""
    calls: list[tuple[str, int]] = []
    real_open = Image.open
    real_save = Image.Image.save

    def _open(*args, **kwargs):
        calls.append(("open", threading.get_ident()))
        return real_open(*args, **kwargs)

    def _save(self, *args, **kwargs):
        calls.append(("save", threading.get_ident()))
        return real_save(self, *args, **kwargs)

    with patch.object(Image, "open", _open), patch.object(Image.Image, "save", _save):
        yield calls


async def test_image_processing_runs_in_executor(
    hass: HomeAssistant,
    aioclient_mock: AiohttpClientMocker,
    resolver,
    db: Database,
    storage: Storage,
    pil_thread_log,
) -> None:
    loop_thread = threading.get_ident()
    # Großes Bild → open, verify, thumbnail, save. Das Testbild selbst wird hier im
    # Eventloop-Thread erzeugt – diese Aufrufe gehören nicht zur Integration.
    big = jpeg_bytes(size=(3000, 2000))
    pil_thread_log.clear()
    mock_chefkoch(aioclient_mock, image=big)
    result = await async_import_url(hass, db, storage, CK_URL)
    assert result["draft"]["data"]["image"]
    assert pil_thread_log, "Bildverarbeitung wurde nicht aufgerufen"
    assert {name for name, _ in pil_thread_log} >= {"open", "save"}
    assert all(thread != loop_thread for _, thread in pil_thread_log), pil_thread_log
