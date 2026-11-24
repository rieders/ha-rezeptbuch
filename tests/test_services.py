"""Aktionen: Antworten, Fehlerübersetzung, Benutzerzuordnung, Import mit confirm."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any
from unittest.mock import patch

from homeassistant.core import Context, HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry
from pytest_homeassistant_custom_component.test_util.aiohttp import AiohttpClientMocker

from custom_components.rezeptbuch.const import DOMAIN
from custom_components.rezeptbuch.db import categories as cats, drafts, ratings, recipes

from .test_url_import import CK_URL, mock_chefkoch

PUBLIC_IP = "93.184.215.14"
AI_FIXTURES = Path(__file__).parent / "fixtures" / "ai"

SAMPLE = {
    "servings": 4,
    "ingredients": [
        {"amount": 250, "unit": "g", "name": "Mehl"},
        {"amount": 1, "unit": "Prise", "name": "Salz"},
        {"name": "Pfeffer", "note": "etwas"},
    ],
    "steps": [{"text": "Rühren.", "timer_seconds": 60}],
}


@pytest.fixture(autouse=True)
def public_dns():
    with patch("custom_components.rezeptbuch.net.async_resolve_host", return_value=[PUBLIC_IP]):
        yield


async def call(hass: HomeAssistant, service: str, data: dict[str, Any] | None = None, **kwargs) -> Any:
    return await hass.services.async_call(DOMAIN, service, data or {}, blocking=True, return_response=True, **kwargs)


async def add_recipe(entry: MockConfigEntry, title: str = "Pfannkuchen", **kwargs) -> int:
    return await entry.runtime_data.db.run(
        recipes.create_recipe, title=title, data=kwargs.pop("data", SAMPLE), **kwargs
    )


async def cat_id(entry: MockConfigEntry, name: str) -> int:
    return next(c["id"] for c in await entry.runtime_data.db.run(cats.list_categories) if c["name"] == name)


# --- Registrierung ----------------------------------------------------------------------


async def test_services_registered_with_responses(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    expected = {
        "import_url": SupportsResponse.OPTIONAL,
        "import_image": SupportsResponse.OPTIONAL,
        "confirm_draft": SupportsResponse.OPTIONAL,
        "discard_draft": SupportsResponse.OPTIONAL,
        "search": SupportsResponse.ONLY,
        "get_recipe": SupportsResponse.ONLY,
        "random_recipe": SupportsResponse.ONLY,
        "rate_recipe": SupportsResponse.OPTIONAL,
        "add_to_shopping_list": SupportsResponse.OPTIONAL,
        "create_category": SupportsResponse.OPTIONAL,
        "assign_category": SupportsResponse.OPTIONAL,
        "delete_recipe": SupportsResponse.OPTIONAL,
    }
    for name, support in expected.items():
        assert hass.services.supports_response(DOMAIN, name) == support, name


# --- import_url ------------------------------------------------------------------------------


async def test_import_url_draft_then_confirm(
    hass: HomeAssistant, rb_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    mock_chefkoch(aioclient_mock)
    response = await call(hass, "import_url", {"url": CK_URL, "tags": ["Familie"]})
    assert response["status"] == "draft" and response["title"] == "Birnen-Streuselkuchen vom Blech"
    draft_id = response["draft_id"]
    assert await rb_entry.runtime_data.db.run(recipes.count_recipes) == 0

    confirmed = await call(hass, "confirm_draft", {"draft_id": draft_id, "title": "Birnenkuchen"})
    assert confirmed["status"] == "created" and confirmed["title"] == "Birnenkuchen"
    recipe = await rb_entry.runtime_data.db.run(recipes.get_recipe, confirmed["recipe_id"])
    assert "Familie" in recipe["tags"]
    await hass.async_block_till_done()
    assert hass.states.get("sensor.rezeptbuch_anzahl_rezepte").state == "1"


async def test_import_url_confirm_true_and_duplicate(
    hass: HomeAssistant, rb_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker, hass_admin_user
) -> None:
    mock_chefkoch(aioclient_mock)
    context = Context(user_id=hass_admin_user.id)
    response = await call(hass, "import_url", {"url": CK_URL, "confirm": True}, context=context)
    assert response["status"] == "created"
    recipe = await rb_entry.runtime_data.db.run(recipes.get_recipe, response["recipe_id"])
    assert recipe["version"]["is_original"] and recipe["version"]["user_id"] == hass_admin_user.id
    assert await rb_entry.runtime_data.db.run(drafts.list_drafts) == []

    again = await call(hass, "import_url", {"url": CK_URL, "confirm": True})
    assert again == {
        "status": "duplicate",
        "recipe_id": response["recipe_id"],
        "title": recipe["title"],
        "source_url": CK_URL,
    }


async def test_import_url_errors_are_translated(
    hass: HomeAssistant, rb_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "import_url", {"url": "ftp://example.org/x"})
    assert err.value.translation_domain == DOMAIN and err.value.translation_key == "invalid_url"

    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "import_url", {"url": "http://127.0.0.1/x"})
    assert err.value.translation_key == "blocked_address"

    aioclient_mock.get("https://example.org/kaputt", status=500)
    with pytest.raises(HomeAssistantError) as err:
        await call(hass, "import_url", {"url": "https://example.org/kaputt"})
    assert not isinstance(err.value, ServiceValidationError)  # Laufzeitfehler, kein Bedienfehler
    assert err.value.translation_key == "fetch_failed"
    assert err.value.translation_placeholders["reason"] == "HTTP 500"


async def test_import_url_respects_private_network_option(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None, aioclient_mock: AiohttpClientMocker
) -> None:
    from custom_components.rezeptbuch.const import CONF_ALLOW_PRIVATE_NETWORKS, CONF_CREATE_DEFAULT_CATEGORIES

    hass.config.config_dir = str(tmp_path)
    url = "http://192.168.178.30:9000/rezept"
    aioclient_mock.get(url, text=(Path(__file__).parent / "fixtures" / "incomplete_recipe.html").read_text("utf-8"))
    for allow in (False, True):
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={CONF_CREATE_DEFAULT_CATEGORIES: False},
            options={CONF_ALLOW_PRIVATE_NETWORKS: allow},
        )
        entry.add_to_hass(hass)
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        if allow:
            assert (await call(hass, "import_url", {"url": url}))["status"] == "draft"
        else:
            with pytest.raises(ServiceValidationError) as err:
                await call(hass, "import_url", {"url": url})
            assert err.value.translation_key == "blocked_address"
        assert await hass.config_entries.async_unload(entry.entry_id)
        await hass.config_entries.async_remove(entry.entry_id)


async def test_discard_draft(
    hass: HomeAssistant, rb_entry: MockConfigEntry, aioclient_mock: AiohttpClientMocker
) -> None:
    mock_chefkoch(aioclient_mock)
    response = await call(hass, "import_url", {"url": CK_URL})
    assert await call(hass, "discard_draft", {"draft_id": response["draft_id"]}) == {"deleted_files": 1}
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "confirm_draft", {"draft_id": response["draft_id"]})
    assert err.value.translation_key == "draft_not_found"


# --- import_image ---------------------------------------------------------------------------


async def test_import_image_from_allowed_file(hass: HomeAssistant, rb_entry: MockConfigEntry, tmp_path: Path) -> None:
    photo_dir = tmp_path / "www"
    photo_dir.mkdir()
    buf = BytesIO()
    Image.new("RGB", (400, 300), (200, 100, 50)).save(buf, format="JPEG")
    (photo_dir / "seite1.jpg").write_bytes(buf.getvalue())
    hass.config.allowlist_external_dirs = {str(photo_dir)}

    ai_response = json.loads((AI_FIXTURES / "clean.json").read_text("utf-8"))

    async def _fake(call_: ServiceCall) -> dict:
        return ai_response

    hass.services.async_register("ai_task", "generate_data", _fake, supports_response=SupportsResponse.ONLY)
    hass.states.async_set("ai_task.ki", "unknown")

    response = await call(hass, "import_image", {"files": [str(photo_dir / "seite1.jpg")], "confirm": True})
    assert response["status"] == "created" and response["title"] == "Zwetschgenkuchen vom Blech"
    recipe = await rb_entry.runtime_data.db.run(recipes.get_recipe, response["recipe_id"])
    assert recipe["source_type"] == "photo"
    assert [i["kind"] for i in recipe["images"]] == ["source_photo"]

    # Datei außerhalb der erlaubten Ordner
    secret = tmp_path / "secrets.yaml"
    secret.write_text("x")
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "import_image", {"files": [str(secret)]})
    assert err.value.translation_key == "path_not_allowed"


async def test_import_image_without_ai_task(hass: HomeAssistant, rb_entry: MockConfigEntry, tmp_path: Path) -> None:
    hass.config.allowlist_external_dirs = {str(tmp_path)}
    buf = BytesIO()
    Image.new("RGB", (40, 30)).save(buf, format="JPEG")
    (tmp_path / "x.jpg").write_bytes(buf.getvalue())
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "import_image", {"files": [str(tmp_path / "x.jpg")]})
    assert err.value.translation_key == "no_ai_task_entity"


async def test_import_image_without_files(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "import_image", {})
    assert err.value.translation_key == "no_photos"


# --- Lesen ------------------------------------------------------------------------------------


async def test_search_get_random(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    kuchen = await cat_id(rb_entry, "Kuchen")
    backen = await cat_id(rb_entry, "Backen")
    rid = await add_recipe(rb_entry, "Apfelkuchen", category_ids=[kuchen], tags=["Herbst"])
    await add_recipe(rb_entry, "Gulasch")

    result = await call(hass, "search", {"query": "apfel"})
    assert result["total"] == 1 and result["recipes"][0]["recipe_id"] == rid
    result = await call(hass, "search", {"category_id": backen})
    assert [r["title"] for r in result["recipes"]] == ["Apfelkuchen"]
    result = await call(hass, "search", {"category_id": backen, "include_subcategories": False})
    assert result["total"] == 0
    result = await call(hass, "search", {"tags": ["herbst"], "never_cooked": True, "limit": 5})
    assert result["total"] == 1

    recipe = await call(hass, "get_recipe", {"recipe_id": rid, "servings": 2})
    assert recipe["servings"] == 2
    assert [i["text"] for i in recipe["ingredients"]] == ["125 g Mehl", "½ Prise Salz", "etwas Pfeffer"]
    assert recipe["categories"] == ["Backen › Kuchen"]
    assert recipe["versions"][0]["is_original"]

    random_one = await call(hass, "random_recipe", {"category_id": backen})
    assert random_one["recipe"]["recipe_id"] == rid
    assert (await call(hass, "random_recipe", {"min_stars": 4}))["recipe"] is None

    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "get_recipe", {"recipe_id": 999})
    assert err.value.translation_key == "not_found"
    assert "999" in err.value.translation_placeholders["message"]


# --- Ändern -------------------------------------------------------------------------------------


async def test_rate_recipe_multi_user(hass: HomeAssistant, rb_entry: MockConfigEntry, hass_admin_user) -> None:
    rid = await add_recipe(rb_entry)
    r1 = await call(hass, "rate_recipe", {"recipe_id": rid, "stars": 4.5}, context=Context(user_id=hass_admin_user.id))
    r2 = await call(hass, "rate_recipe", {"recipe_id": rid, "stars": 3, "cooked": False, "comment": "ok"})
    assert r2["avg_stars"] == 3.75 and r2["rating_count"] == 2 and r1["cook_log_id"] != r2["cook_log_id"]
    stats = await rb_entry.runtime_data.db.run(ratings.recipe_stats, rid)
    assert {u["user_id"] for u in stats["per_user"]} == {hass_admin_user.id, "system"}
    assert stats["cooked_count"] == 1

    # Schema: 0,5 … 5 (Fehlerklasse je nach HA-Version voluptuous bzw. probatio)
    with pytest.raises(Exception, match="at most 5"):
        await call(hass, "rate_recipe", {"recipe_id": rid, "stars": 7})
    with pytest.raises(ServiceValidationError) as err:  # halbe Schritte
        await call(hass, "rate_recipe", {"recipe_id": rid, "stars": 4.2})
    assert err.value.translation_key == "invalid_input"


async def test_categories_and_delete(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry)
    kuchen = await cat_id(rb_entry, "Kuchen")
    created = await call(
        hass, "create_category", {"name": "Obstkuchen", "parent_id": kuchen, "icon": "mdi:fruit-cherries"}
    )
    assert created["path"] == "Backen › Kuchen › Obstkuchen"
    with pytest.raises(ServiceValidationError) as err:
        await call(hass, "create_category", {"name": "obstkuchen", "parent_id": kuchen})
    assert err.value.translation_key == "conflict"

    assigned = await call(hass, "assign_category", {"recipe_id": rid, "category_ids": [created["category_id"]]})
    assert assigned == {"categories": ["Backen › Kuchen › Obstkuchen"]}

    # Bild anlegen und mit dem Rezept löschen
    storage = rb_entry.runtime_data.storage
    rel = await hass.async_add_executor_job(storage.write_image, b"bild", "jpg")
    await rb_entry.runtime_data.db.run(recipes.add_image, rid, rel, "cover")
    result = await call(hass, "delete_recipe", {"recipe_id": rid})
    assert result == {"deleted": True, "deleted_files": 1}
    assert not storage.image_path(rel).exists()
    with pytest.raises(ServiceValidationError):
        await call(hass, "delete_recipe", {"recipe_id": rid})


async def test_service_without_response_works(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry)
    await hass.services.async_call(DOMAIN, "rate_recipe", {"recipe_id": rid, "stars": 5}, blocking=True)
    assert (await rb_entry.runtime_data.db.run(ratings.recipe_stats, rid))["avg_stars"] == 5
