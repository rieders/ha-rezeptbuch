"""Panel-Backend: WebSocket-Befehle, Rechte, signierte Bild-URLs, Foto-Upload, Panel-Registrierung."""

from __future__ import annotations

from io import BytesIO
import json
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import aiohttp
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rezeptbuch.const import CONF_CREATE_DEFAULT_CATEGORIES, DOMAIN
from custom_components.rezeptbuch.db import categories as cats, drafts, recipes, versions
from custom_components.rezeptbuch.panel import BUNDLE_NAME, STATIC_URL

AI_FIXTURES = Path(__file__).parent / "fixtures" / "ai"
SAMPLE = {
    "servings": 4,
    "ingredients": [{"amount": 200, "unit": "g", "name": "Mehl"}, {"name": "Salz", "note": "etwas"}],
    "steps": [{"text": "20 Minuten backen.", "timer_seconds": 1200}],
}


def jpeg(size=(60, 40)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, (10, 120, 200)).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture
async def ws(hass: HomeAssistant, rb_entry: MockConfigEntry, hass_ws_client):
    client = await hass_ws_client(hass)

    async def send(type_: str, **data: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"rezeptbuch/{type_}", **data})
        return await client.receive_json()

    return send


@pytest.fixture
async def ws_user(hass: HomeAssistant, rb_entry: MockConfigEntry, hass_ws_client, hass_read_only_access_token):
    """WebSocket eines Nicht-Admins."""
    client = await hass_ws_client(hass, hass_read_only_access_token)

    async def send(type_: str, **data: Any) -> dict[str, Any]:
        await client.send_json_auto_id({"type": f"rezeptbuch/{type_}", **data})
        return await client.receive_json()

    return send


async def add_recipe(entry: MockConfigEntry, title: str = "Brot", with_image: bool = False, **kw) -> int:
    runtime = entry.runtime_data
    image = None
    if with_image:
        image = await runtime.db._submit(runtime.storage.write_image, jpeg(), "jpg")
    return await runtime.db.run(recipes.create_recipe, title=title, data=SAMPLE, image=image, **kw)


# --- Lesen -------------------------------------------------------------------------------


async def test_info(ws, hass_admin_user) -> None:
    msg = await ws("info")
    assert msg["success"]
    assert msg["result"]["is_admin"] is True
    assert msg["result"]["ai_task_available"] is False
    assert msg["result"]["default_servings"] == 4


async def test_list_and_get_with_scaling(ws, rb_entry: MockConfigEntry) -> None:
    kuchen = next(c["id"] for c in await rb_entry.runtime_data.db.run(cats.list_categories) if c["name"] == "Kuchen")
    rid = await add_recipe(rb_entry, "Zopf", category_ids=[kuchen], tags=["Ostern"])
    await add_recipe(rb_entry, "Suppe")

    msg = await ws("recipes/list", query="zopf")
    assert msg["result"]["total"] == 1 and msg["result"]["items"][0]["recipe_id"] == rid
    msg = await ws("recipes/list", category_id=kuchen)
    assert [i["title"] for i in msg["result"]["items"]] == ["Zopf"]
    msg = await ws("recipes/list", uncategorized=True)
    assert [i["title"] for i in msg["result"]["items"]] == ["Suppe"]
    msg = await ws("recipes/list", tags=["ostern"], sort="new", limit=10)
    assert msg["result"]["total"] == 1

    msg = await ws("recipe/get", recipe_id=rid, servings=2)
    recipe = msg["result"]
    assert recipe["version"]["data"]["servings"] == 2
    assert recipe["version"]["original_servings"] == 4
    texts = [i["text"] for i in recipe["version"]["data"]["ingredients"]]
    assert texts == ["100 g Mehl", "etwas Salz"]
    assert recipe["version"]["data"]["steps"][0]["timer_seconds"] == 1200
    assert recipe["categories"][0]["path"] == ["Backen", "Kuchen"]
    assert "source_key" not in recipe

    msg = await ws("recipe/get", recipe_id=999)
    assert not msg["success"] and msg["error"]["code"] == "not_found"


async def test_categories_tags_and_versions(ws, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry, tags=["Party"])
    orig = await rb_entry.runtime_data.db.run(versions.original_version_id, rid)
    changed = {**SAMPLE, "ingredients": [{"amount": 150, "unit": "g", "name": "Mehl"}]}
    v2 = await rb_entry.runtime_data.db.run(versions.create_version, rid, changed, make_default=False)

    tree = (await ws("categories"))["result"]
    assert [c["name"] for c in tree["categories"]] == ["Kochen", "Backen", "Getränke"]
    assert (await ws("tags"))["result"]["tags"] == [{"name": "Party", "count": 1}]

    diff = (await ws("recipe/diff", old_version_id=orig, new_version_id=v2))["result"]
    assert diff["has_changes"] and "Mehl 200 g → 150 g" in diff["summary"]
    assert (await ws("recipe/set_default_version", recipe_id=rid, version_id=v2))["success"]
    assert (await ws("recipe/get", recipe_id=rid))["result"]["version"]["id"] == v2


async def test_rate_and_annotate_use_connection_user(ws, rb_entry: MockConfigEntry, hass_admin_user) -> None:
    rid = await add_recipe(rb_entry)
    assert (await ws("recipe/rate", recipe_id=rid, stars=4.5, comment="lecker"))["success"]
    assert (await ws("recipe/annotate", recipe_id=rid, text="weniger Salz"))["success"]
    recipe = (await ws("recipe/get", recipe_id=rid))["result"]
    assert recipe["history"][0]["user_name"] == hass_admin_user.name
    assert recipe["stats"]["per_user"][0]["user_name"] == hass_admin_user.name
    assert recipe["annotations"][0]["user_name"] == hass_admin_user.name
    bad = await ws("recipe/rate", recipe_id=rid, stars=4.2)
    assert bad["error"]["code"] == "invalid_input"


# --- Rechte --------------------------------------------------------------------------------


async def test_admin_only_commands(ws_user, ws, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry)
    kuchen = next(c["id"] for c in await rb_entry.runtime_data.db.run(cats.list_categories) if c["name"] == "Kuchen")
    for type_, data in (
        ("recipe/delete", {"recipe_id": rid}),
        ("category/delete", {"category_id": kuchen}),
        ("category/move", {"category_id": kuchen, "parent_id": None}),
    ):
        msg = await ws_user(type_, **data)
        assert not msg["success"] and msg["error"]["code"] == "unauthorized", type_
    # Daten unverändert
    assert await rb_entry.runtime_data.db.run(recipes.count_recipes) == 1
    assert (await rb_entry.runtime_data.db.run(cats.get_category, kuchen))["parent_id"] is not None

    # Normale Benutzer dürfen lesen, bewerten, Einkaufsliste, Kategorien anlegen
    assert (await ws_user("info"))["result"]["is_admin"] is False
    assert (await ws_user("recipes/list"))["success"]
    assert (await ws_user("recipe/rate", recipe_id=rid, stars=3))["success"]
    assert (await ws_user("shopping/add", recipe_id=rid))["success"]
    assert (await ws_user("category/create", name="Brote", parent_id=kuchen))["success"]

    # Admin darf
    assert (await ws("category/move", category_id=kuchen, parent_id=None))["success"]
    assert (await ws("recipe/delete", recipe_id=rid))["success"]
    assert await rb_entry.runtime_data.db.run(recipes.count_recipes) == 0


# --- Entwürfe & Import -------------------------------------------------------------------------


async def test_draft_edit_confirm_discard(ws, rb_entry: MockConfigEntry) -> None:
    db = rb_entry.runtime_data.db
    data = {"title": "Entwurf", "version": SAMPLE, "category_ids": [], "tags": [], "warnings": ["Hinweis"]}
    draft_id = await db.run(drafts.create_draft, "manual", data)

    listed = (await ws("drafts"))["result"]["drafts"]
    assert listed[0]["id"] == draft_id and listed[0]["warnings"] == ["Hinweis"]
    draft = (await ws("draft/get", draft_id=draft_id))["result"]
    assert draft["ingredient_lines"] == ["200 g Mehl", "etwas Salz"]
    assert draft["step_lines"] == ["20 Minuten backen."]

    updated = await ws(
        "draft/update",
        draft_id=draft_id,
        title="Brötchen",
        servings=6,
        ingredient_lines=["Für den Teig:", "500 g Mehl", "1 Würfel Hefe"],
        step_lines=["Teig 1 Std. gehen lassen.", "Backen."],
        tags=["Frühstück"],
    )
    assert updated["success"], updated
    d = updated["result"]
    assert d["title"] == "Brötchen" and d["version"]["servings"] == 6
    assert [(i["name"], i["group"]) for i in d["version"]["ingredients"]] == [("Mehl", "Teig"), ("Hefe", "Teig")]
    assert d["version"]["steps"][0]["timer_seconds"] == 3600  # Timer-Erkennung beim Bearbeiten
    assert d["ingredient_lines"] == ["Teig:", "500 g Mehl", "1 Würfel Hefe"]

    bad = await ws("draft/update", draft_id=draft_id, image="../../secrets.yaml")
    assert bad["error"]["code"] == "invalid_input"

    confirmed = await ws("draft/confirm", draft_id=draft_id)
    assert confirmed["success"]
    recipe = await db.run(recipes.get_recipe, confirmed["result"]["recipe_id"])
    assert recipe["title"] == "Brötchen" and recipe["tags"] == ["Frühstück"]

    other = await db.run(drafts.create_draft, "manual", data)
    assert (await ws("draft/discard", draft_id=other))["success"]
    assert (await ws("draft/get", draft_id=other))["error"]["code"] == "draft_not_found"


async def test_import_url_errors(ws) -> None:
    msg = await ws("import/url", url="http://127.0.0.1/x")
    assert not msg["success"] and msg["error"]["code"] == "blocked_address"


# --- Bilder: signierte URLs ------------------------------------------------------------------


async def test_signed_image_urls(
    hass: HomeAssistant, ws, rb_entry: MockConfigEntry, hass_client_no_auth, hass_client
) -> None:
    rid = await add_recipe(rb_entry, with_image=True)
    item = (await ws("recipes/list"))["result"]["items"][0]
    url = item["image_url"]
    assert url.startswith("/api/rezeptbuch/image/") and "authSig=" in url

    anon = await hass_client_no_auth()
    resp = await anon.get(url)
    assert resp.status == 200
    assert resp.headers["Content-Type"] == "image/jpeg"
    assert resp.headers["Cache-Control"].startswith("private")
    assert (await resp.read())[:2] == b"\xff\xd8"

    # ohne Signatur bzw. mit manipuliertem Pfad: abgelehnt
    plain = url.split("?")[0]
    assert (await anon.get(plain)).status == 401
    tampered = url.replace("/image/", "/image/x")
    assert (await anon.get(tampered)).status == 401

    # neu signiert bei jedem Laden
    again = (await ws("recipe/get", recipe_id=rid))["result"]["image_url"]
    assert again.split("?")[0] == plain

    # angemeldet: Pfad-Ausbruch wird abgewiesen
    client = await hass_client()
    resp = await client.get("/api/rezeptbuch/image/..%2F..%2Fsecrets.yaml")
    assert resp.status in (400, 404)  # HAs Security-Filter (400) bzw. unsere Pfadprüfung (404)
    resp = await client.get("/api/rezeptbuch/image/ab/gibt-es-nicht.jpg")
    assert resp.status == 404


# --- Foto-Upload -------------------------------------------------------------------------------


async def test_photo_upload(hass: HomeAssistant, rb_entry: MockConfigEntry, hass_client) -> None:
    client = await hass_client()

    form = aiohttp.FormData()
    form.add_field("photo", jpeg(), filename="seite1.jpg", content_type="image/jpeg")
    resp = await client.post("/api/rezeptbuch/import/photo", data=form)
    assert resp.status == 400
    assert (await resp.json())["code"] == "no_ai_task_entity"

    ai = json.loads((AI_FIXTURES / "clean.json").read_text("utf-8"))

    async def _fake(call: ServiceCall) -> dict:
        return ai

    hass.services.async_register("ai_task", "generate_data", _fake, supports_response=SupportsResponse.ONLY)
    hass.states.async_set("ai_task.ki", "unknown")
    form = aiohttp.FormData()
    form.add_field("photo", jpeg(), filename="seite1.jpg", content_type="image/jpeg")
    form.add_field("photo", jpeg((80, 50)), filename="seite2.jpg", content_type="image/jpeg")
    resp = await client.post("/api/rezeptbuch/import/photo", data=form)
    assert resp.status == 200, await resp.text()
    body = await resp.json()
    draft = body["draft"]
    assert draft["title"] == "Zwetschgenkuchen vom Blech"
    assert len(draft["images"]) == 2 and all("authSig=" in i["url"] for i in draft["images"])

    form = aiohttp.FormData()
    form.add_field("photo", b"kein bild", filename="x.jpg", content_type="image/jpeg")
    resp = await client.post("/api/rezeptbuch/import/photo", data=form)
    assert resp.status == 400 and (await resp.json())["code"] == "invalid_image"


async def test_upload_requires_auth(hass: HomeAssistant, rb_entry: MockConfigEntry, hass_client_no_auth) -> None:
    client = await hass_client_no_auth()
    resp = await client.post("/api/rezeptbuch/import/photo", data=aiohttp.FormData({"photo": "x"}))
    assert resp.status == 401


# --- Panel-Registrierung ---------------------------------------------------------------------------


async def test_panel_registered_and_removed(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None, hass_client
) -> None:
    hass.config.config_dir = str(tmp_path)
    hass.config.components.add("frontend")  # Frontend-Paket ist in Tests nicht installiert
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False})
    entry.add_to_hass(hass)
    with (
        patch("custom_components.rezeptbuch.panel.panel_custom.async_register_panel", AsyncMock()) as register,
        patch("custom_components.rezeptbuch.panel.frontend.async_remove_panel") as remove,
    ):
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        kwargs = register.call_args.kwargs
        assert kwargs["frontend_url_path"] == "rezeptbuch"
        assert kwargs["webcomponent_name"] == "rezeptbuch-panel"
        assert kwargs["sidebar_title"] == "Rezeptbuch" and kwargs["sidebar_icon"] == "mdi:chef-hat"
        assert kwargs["require_admin"] is False
        assert kwargs["module_url"].startswith(f"{STATIC_URL}/{BUNDLE_NAME}?v=")
        assert kwargs["module_url"].split("?v=")[1] != "missing"

        assert await hass.config_entries.async_unload(entry.entry_id)
        remove.assert_called_once_with(hass, "rezeptbuch")

        # Reload ohne HA-Neustart: Panel wieder da
        assert await hass.config_entries.async_setup(entry.entry_id)
        await hass.async_block_till_done()
        assert register.call_count == 2
        assert await hass.config_entries.async_unload(entry.entry_id)

    client = await hass_client()
    resp = await client.get(f"{STATIC_URL}/{BUNDLE_NAME}")
    assert resp.status == 200
    assert "javascript" in resp.headers["Content-Type"]
    body = await resp.text()
    assert "rezeptbuch-panel" in body


async def test_bundle_has_no_external_resources() -> None:
    bundle = (Path(__file__).parents[1] / "custom_components" / "rezeptbuch" / "frontend" / BUNDLE_NAME).read_text(
        "utf-8"
    )
    import re

    urls = set(re.findall(r"https?://[\w.-]+[^\s\"'`)]*", bundle))
    # nur der SVG-Namensraum (kein Abruf) ist erlaubt
    assert urls <= {"http://www.w3.org/2000/svg", "http://www.w3.org/1999/xhtml"}, urls
    assert "@import" not in bundle and "fonts.googleapis" not in bundle
