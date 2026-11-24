"""URL-Import: Fixtures + gemocktes HTTP (aioclient_mock), kein echter Netzwerkzugriff."""

from __future__ import annotations

from collections.abc import AsyncIterator
from io import BytesIO
from pathlib import Path
from unittest.mock import patch

import aiohttp
from homeassistant.core import HomeAssistant
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rezeptbuch.db import Database, categories as cats, drafts, recipes, versions
from custom_components.rezeptbuch.errors import (
    BlockedAddress,
    DraftNotFound,
    DuplicateRecipe,
    FetchFailed,
    InvalidImage,
    InvalidUrl,
    NoRecipeFound,
    ResponseTooLarge,
)
from custom_components.rezeptbuch.images import MAX_DIMENSION, process_image
from custom_components.rezeptbuch.importer.url import async_import_url
from custom_components.rezeptbuch.net import async_safe_get, is_public_ip
from custom_components.rezeptbuch.storage import Storage

FIXTURES = Path(__file__).parent / "fixtures"
CK_SHORT = "https://www.chefkoch.de/rezepte/1234567890123456/Birnenkuchen.html"
CK_URL = "https://www.chefkoch.de/rezepte/1234567890123456/Birnen-Streuselkuchen-vom-Blech.html"
CK_IMG = "https://img.chefkoch-cdn.de/rezepte/1108101216891426/bilder/668306/crop-960x540/apfelkuchen.jpg"
BLOG_URL = "https://www.mein-kuechenblog.de/rote-linsensuppe/"
BLOG_IMG = "https://www.mein-kuechenblog.de/wp-content/uploads/linsensuppe.jpg"
PUBLIC_IP = "93.184.215.14"


def fixture_html(name: str) -> str:
    return (FIXTURES / name).read_text(encoding="utf-8")


def jpeg_bytes(size=(64, 48), color=(200, 120, 40)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, format="JPEG")
    return out.getvalue()


HTML = {"Content-Type": "text/html; charset=utf-8"}
JPEG = {"Content-Type": "image/jpeg"}


@pytest.fixture(autouse=True)
def public_dns():
    """DNS-Auflösung im SSRF-Check: alle Hosts gelten als öffentlich."""
    with patch("custom_components.rezeptbuch.net.async_resolve_host", return_value=[PUBLIC_IP]) as resolver:
        yield resolver


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


async def _cat_id(db: Database, name: str) -> int:
    def _find(conn):
        return next(c["id"] for c in cats.list_categories(conn) if c["name"] == name)

    return await db.run(_find)


def mock_chefkoch(aioclient_mock: AiohttpClientMocker, image: bytes | None = None) -> None:
    aioclient_mock.get(CK_SHORT, status=301, headers={"Location": CK_URL})
    aioclient_mock.get(CK_URL, text=fixture_html("chefkoch_streuselkuchen.html"), headers=HTML)
    aioclient_mock.get(CK_IMG, content=image if image is not None else jpeg_bytes(), headers=JPEG)


# --- Erfolgsfälle -----------------------------------------------------------------


async def test_import_chefkoch_draft_and_confirm(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock)
    result = await async_import_url(hass, db, storage, CK_SHORT + "?utm_source=app", user_id="anna")
    assert result["status"] == "draft"
    draft = result["draft"]["data"]
    assert draft["title"] == "Birnen-Streuselkuchen vom Blech"  # " von testkoch" entfernt
    assert draft["source_url"] == CK_URL  # nach Weiterleitung, ohne Tracking
    version = draft["version"]
    assert (version["servings"], version["servings_unit"]) == (1, "Portionen")
    assert (version["prep_time"], version["cook_time"], version["total_time"]) == (30, 45, 75)
    names = [i["name"] for i in version["ingredients"]]
    assert len(names) == 13 and names[3] == "Ei" and names[11] == "Salz"
    zimt = version["ingredients"][10]
    assert (zimt["amount"], zimt["unit"], zimt["name"], zimt["note"]) == (1, "TL", "Zimt", "gestr.")
    assert [s["timer_seconds"] for s in version["steps"]] == [None, None, None, 2700]
    assert all(s["group"] is None for s in version["steps"])
    assert result["warnings"] == []

    # Bild lokal gespeichert
    assert draft["image"] and storage.image_path(draft["image"]).is_file()

    # Kategorien: recipeCategory "Backen" + Keyword "Kuchen" → nur "Kuchen" (spezifischer),
    # "Vegetarisch" liegt unter "Kochen" → wird Tag
    kuchen = await _cat_id(db, "Kuchen")
    assert draft["category_ids"] == [kuchen]
    assert draft["tags"] == ["Vegetarisch", "Herbst", "Obst", "Einfach"]

    # Noch kein Rezept angelegt
    assert await db.run(recipes.count_recipes) == 0

    confirmed = await db.run(drafts.confirm_draft, result["draft_id"], {"title": "Omas Birnenkuchen"})
    recipe = await db.run(recipes.get_recipe, confirmed["recipe_id"])
    assert recipe["title"] == "Omas Birnenkuchen"
    assert recipe["source_type"] == "url" and recipe["source_url"] == CK_URL
    assert recipe["image"] == draft["image"]
    assert recipe["version"]["is_original"] and recipe["version"]["label"] == "Original"
    assert [c["name"] for c in recipe["categories"]] == ["Kuchen"]
    assert recipe["version"]["user_id"] == "anna"
    with pytest.raises(DraftNotFound):
        await db.run(drafts.get_draft, result["draft_id"])


async def test_import_blog_jsonld(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    aioclient_mock.get(BLOG_URL, text=fixture_html("blog_linsensuppe.html"), headers=HTML)
    aioclient_mock.get(BLOG_IMG, content=jpeg_bytes(), headers=JPEG)
    result = await async_import_url(hass, db, storage, BLOG_URL)
    draft = result["draft"]["data"]
    assert draft["title"] == "Rote Linsensuppe mit Kokosmilch"
    assert draft["description"].endswith("Kokosmilch & Limette.")
    assert draft["source_url"] == "https://www.mein-kuechenblog.de/rote-linsensuppe"
    assert draft["source"]["image_url"] == BLOG_IMG  # größtes Bild
    version = draft["version"]
    assert (version["servings"], version["servings_unit"]) == (4, "Portionen")
    kurkuma = version["ingredients"][7]
    assert (kurkuma["amount"], kurkuma["unit"], kurkuma["name"]) == (0.5, "TL", "Kurkuma")
    assert [s["timer_seconds"] for s in version["steps"]] == [240, 1200, None]
    suppen = await _cat_id(db, "Suppen & Eintöpfe")
    vegetarisch = await _cat_id(db, "Vegetarisch")
    assert sorted(draft["category_ids"]) == sorted([suppen, vegetarisch])
    assert draft["tags"] == ["Linsen", "schnell", "Meal Prep"]


async def test_incomplete_recipe_gives_draft_with_warnings(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    url = "https://example.org/omas-rezept"
    aioclient_mock.get(url, text=fixture_html("incomplete_recipe.html"), headers=HTML)
    result = await async_import_url(hass, db, storage, url)
    assert result["status"] == "draft"
    assert "Keine Zutaten gefunden – bitte ergänzen." in result["warnings"]
    assert "Keine Portionsangabe gefunden." in result["warnings"]
    steps = result["draft"]["data"]["version"]["steps"]
    assert [s["text"] for s in steps] == ["Alles vermengen.", "30 Minuten ruhen lassen.", "Ausbacken."]
    assert steps[1]["timer_seconds"] == 1800


# --- Duplikate -----------------------------------------------------------------------


async def test_duplicate_detected_before_fetch(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    rid = await db.run(recipes.create_recipe, title="Vorhanden", data={}, source_url=CK_URL, source_type="url")
    result = await async_import_url(
        hass, db, storage, "http://chefkoch.de/rezepte/1234567890123456/Birnen-Streuselkuchen-vom-Blech.html/#x"
    )
    assert result == {"status": "duplicate", "recipe_id": rid, "title": "Vorhanden", "source_url": CK_URL}
    assert aioclient_mock.call_count == 0


async def test_duplicate_detected_after_redirect(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    rid = await db.run(recipes.create_recipe, title="Vorhanden", data={}, source_url=CK_URL, source_type="url")
    mock_chefkoch(aioclient_mock)
    result = await async_import_url(hass, db, storage, CK_SHORT)
    assert result["status"] == "duplicate" and result["recipe_id"] == rid
    assert await db.run(drafts.list_drafts) == []


async def test_allow_duplicate_and_confirm_guard(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock)
    first = await async_import_url(hass, db, storage, CK_URL)
    second = await async_import_url(hass, db, storage, CK_URL, allow_duplicate=True)
    await db.run(drafts.confirm_draft, first["draft_id"])
    # Beim Bestätigen wird erneut geprüft
    with pytest.raises(DuplicateRecipe):
        await db.run(drafts.confirm_draft, second["draft_id"])
    await db.run(drafts.confirm_draft, second["draft_id"], allow_duplicate=True)
    assert await db.run(recipes.count_recipes) == 2


# --- Fehlerfälle -----------------------------------------------------------------------


async def test_no_recipe_found(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    url = "https://example.org/messer-test"
    aioclient_mock.get(url, text=fixture_html("no_recipe.html"), headers=HTML)
    with pytest.raises(NoRecipeFound):
        await async_import_url(hass, db, storage, url)
    assert await db.run(drafts.list_drafts) == []


@pytest.mark.parametrize(
    ("kwargs", "error"),
    [
        ({"status": 404}, FetchFailed),
        ({"status": 503}, FetchFailed),
        ({"exc": TimeoutError()}, FetchFailed),
        ({"exc": aiohttp.ClientConnectionError()}, FetchFailed),
        ({"headers": {"Content-Length": str(50 * 1024 * 1024)}, "text": "x"}, ResponseTooLarge),
    ],
)
async def test_fetch_errors(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage, kwargs, error
) -> None:
    url = "https://example.org/rezept"
    aioclient_mock.get(url, **kwargs)
    with pytest.raises(error):
        await async_import_url(hass, db, storage, url)


async def test_body_size_limit_without_content_length(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    url = "https://example.org/gross"
    aioclient_mock.get(url, content=b"a" * 3000)
    with pytest.raises(ResponseTooLarge):
        await async_safe_get(hass, url, max_bytes=1000)


async def test_too_many_redirects(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    url = "https://example.org/loop"
    aioclient_mock.get(url, status=302, headers={"Location": "/loop"})
    with pytest.raises(FetchFailed, match="Weiterleitungen"):
        await async_safe_get(hass, url)


async def test_invalid_urls(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    for url in ("", "ftp://example.org/x", "javascript:alert(1)", "https://user:pw@example.org/x"):
        with pytest.raises(InvalidUrl):
            await async_import_url(hass, db, storage, url)
    assert aioclient_mock.call_count == 0


# --- SSRF -----------------------------------------------------------------------------


@pytest.mark.parametrize(
    "url",
    [
        "http://127.0.0.1/rezept",
        "http://10.0.0.5/rezept",
        "http://192.168.178.1/rezept",
        "http://169.254.169.254/latest/meta-data",
        "http://[::1]/rezept",
        "http://localhost:8123/api",
        "http://homeassistant.local:8123/",
    ],
)
async def test_ssrf_literal_and_local_hosts_blocked(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, url: str
) -> None:
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, url)
    assert aioclient_mock.call_count == 0


async def test_ssrf_hostname_resolving_to_private_ip(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, public_dns
) -> None:
    public_dns.return_value = [PUBLIC_IP, "192.168.1.20"]
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, "https://intern.example.org/")
    assert aioclient_mock.call_count == 0


async def test_ssrf_redirect_to_private_target(hass: HomeAssistant, aioclient_mock: AiohttpClientMocker) -> None:
    aioclient_mock.get("https://example.org/r", status=302, headers={"Location": "http://127.0.0.1:8123/api/states"})
    with pytest.raises(BlockedAddress):
        await async_safe_get(hass, "https://example.org/r")
    assert aioclient_mock.call_count == 1


@pytest.mark.parametrize(
    ("ip", "public"),
    [
        (PUBLIC_IP, True),
        ("2a00:1450:4001:82b::200e", True),
        ("127.0.0.1", False),
        ("10.1.2.3", False),
        ("172.16.0.1", False),
        ("192.168.0.1", False),
        ("100.64.0.1", False),
        ("169.254.1.1", False),
        ("0.0.0.0", False),
        ("224.0.0.1", False),
        ("::1", False),
        ("fe80::1", False),
        ("fd00::1", False),
        ("::ffff:127.0.0.1", False),
        ("kein-ip", False),
    ],
)
def test_is_public_ip(ip: str, public: bool) -> None:
    assert is_public_ip(ip) is public


# --- Bilder -------------------------------------------------------------------------------


async def test_image_failure_is_only_a_warning(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    aioclient_mock.get(CK_URL, text=fixture_html("chefkoch_streuselkuchen.html"), headers=HTML)
    aioclient_mock.get(CK_IMG, text="<html>kein Bild</html>", headers=HTML)
    result = await async_import_url(hass, db, storage, CK_URL)
    assert result["draft"]["data"]["image"] is None
    assert "Bild konnte nicht geladen werden." in result["warnings"]


async def test_corrupt_image_is_rejected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock, image=b"\xff\xd8\xff\xe0kaputt")
    result = await async_import_url(hass, db, storage, CK_URL)
    assert result["draft"]["data"]["image"] is None
    assert list(storage.images_dir.rglob("*.*")) == []


def test_process_image_downscales_and_rotates() -> None:
    big = BytesIO()
    img = Image.new("RGB", (4000, 1000), (10, 20, 30))
    exif = img.getexif()
    exif[0x0112] = 6  # 90° gedreht
    img.save(big, format="JPEG", exif=exif)
    data, ext = process_image(big.getvalue())
    assert ext == "jpg"
    with Image.open(BytesIO(data)) as out:
        assert max(out.size) == MAX_DIMENSION
        assert out.size[1] > out.size[0]  # Hochformat nach EXIF-Drehung


def test_process_image_keeps_small_images_unchanged() -> None:
    raw = jpeg_bytes()
    assert process_image(raw) == (raw, "jpg")


@pytest.mark.parametrize("data", [b"", b"GIF89a-kaputt", b"<svg xmlns='http://www.w3.org/2000/svg'/>"])
def test_process_image_rejects_invalid(data: bytes) -> None:
    with pytest.raises(InvalidImage):
        process_image(data)


def test_process_image_rejects_unsupported_format() -> None:
    out = BytesIO()
    Image.new("RGB", (10, 10)).save(out, format="BMP")
    with pytest.raises(InvalidImage, match="BMP"):
        process_image(out.getvalue())


def test_storage_blocks_path_traversal(storage: Storage) -> None:
    with pytest.raises(ValueError):
        storage.image_path("../../secrets.yaml")
    assert storage.delete_image("../rezepte.db") is False


async def test_discard_draft_returns_image_paths(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock)
    result = await async_import_url(hass, db, storage, CK_URL)
    paths = await db.run(drafts.delete_draft, result["draft_id"])
    assert paths == [result["draft"]["data"]["image"]]


# --- Mapping lernt aus Korrekturen ----------------------------------------------------------


async def test_mapping_learns_from_correction(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock)
    torten = await _cat_id(db, "Torten")
    result = await async_import_url(hass, db, storage, CK_URL)
    # Nutzer ersetzt "Kuchen" durch "Torten"
    await db.run(drafts.confirm_draft, result["draft_id"], {"category_ids": [torten]})
    assert await db.run(cats.get_mapping, "Kuchen") == torten

    # Nächster Import mit gleichen Schlagworten schlägt "Torten" vor
    await db.run(recipes.delete_recipe, 1)
    result = await async_import_url(hass, db, storage, CK_URL)
    assert result["draft"]["data"]["category_ids"] == [torten]

    # Entfernt der Nutzer den gelernten Vorschlag wieder, wird das Mapping vergessen
    await db.run(drafts.confirm_draft, result["draft_id"], {"category_ids": []})
    assert await db.run(cats.get_mapping, "Kuchen") is None


async def test_unmapped_primary_category_learned(db: Database) -> None:
    def _run(conn):
        from custom_components.rezeptbuch.importer.mapping import learn_from_correction, map_keywords

        res = map_keywords(conn, ["Ostergebäck"], [])
        assert res.category_ids == [] and res.tags == ["Ostergebäck"]
        kuchen = next(c["id"] for c in cats.list_categories(conn) if c["name"] == "Kuchen")
        learn_from_correction(
            conn, primary_keywords=res.primary_keywords, matched=res.matched, suggested_ids=[], final_ids=[kuchen]
        )
        again = map_keywords(conn, ["ostergebäck"], [])
        assert again.category_ids == [kuchen] and again.tags == []

    await db.run(_run)


async def test_original_of_imported_recipe_is_protected(
    hass: HomeAssistant, aioclient_mock: AiohttpClientMocker, db: Database, storage: Storage
) -> None:
    mock_chefkoch(aioclient_mock)
    result = await async_import_url(hass, db, storage, CK_URL)
    rid = (await db.run(drafts.confirm_draft, result["draft_id"]))["recipe_id"]
    orig = await db.run(versions.original_version_id, rid)
    with pytest.raises(Exception, match="Original"):
        await db.run(versions.update_version, orig, label="x")
