"""WebSocket-Befehle für das Panel (rezeptbuch/…).

Rechte (serverseitig geprüft):
- alle Benutzer: lesen, bewerten, Notizen, Einkaufsliste, Import, Entwürfe,
  Kategorien anlegen/umbenennen, Standardversion wählen
- nur Admins: Rezept löschen, Kategorien löschen/verschieben
  (Einstellungen laufen über den Options-Flow und sind in HA ohnehin Admin-only)
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import functools
import logging
from typing import Any

from homeassistant.components import websocket_api
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_send
import voluptuous as vol

from .api_format import Signer, apply_lines, async_user_names, ingredient_lines, version_view
from .cleanup import async_discard_draft
from .const import DOMAIN, SIGNAL_SHOPPING_UPDATED
from .coordinator import recipe_summary
from .db import ConflictError, DatabaseError, NotFoundError, categories as cats, drafts, ratings, recipes, versions
from .errors import RezeptbuchError
from .images import async_delete_images
from .importer.photo import resolve_ai_task_entity
from .importer.url import async_import_url
from .models import ValidationError, VersionData
from .net import VERSION
from .runtime import RezeptbuchRuntime, async_get_runtime
from .scaling import scale_version
from .shopping_list import add_recipe

_LOGGER = logging.getLogger(__name__)

WsHandler = Callable[
    [HomeAssistant, websocket_api.ActiveConnection, dict[str, Any], RezeptbuchRuntime], Awaitable[None]
]


def _with_runtime(func: WsHandler) -> Callable[..., Awaitable[None]]:
    """Runtime holen und fachliche Fehler als WebSocket-Fehler melden."""

    @functools.wraps(func)
    async def _handler(hass: HomeAssistant, connection: websocket_api.ActiveConnection, msg: dict[str, Any]) -> None:
        runtime = async_get_runtime(hass)
        if runtime is None:
            connection.send_error(msg["id"], "not_loaded", "Rezeptbuch ist nicht geladen")
            return
        try:
            await func(hass, connection, msg, runtime)
        except RezeptbuchError as err:
            connection.send_error(
                msg["id"],
                err.translation_key,
                str(err),
                translation_domain=DOMAIN,
                translation_key=err.translation_key,
                translation_placeholders=err.placeholders,
            )
        except NotFoundError as err:
            connection.send_error(msg["id"], websocket_api.ERR_NOT_FOUND, str(err))
        except (ValidationError, ConflictError, DatabaseError) as err:
            code = "conflict" if isinstance(err, ConflictError) else "invalid_input"
            connection.send_error(msg["id"], code, str(err))

    return _handler


async def _refresh(runtime: RezeptbuchRuntime) -> None:
    if runtime.coordinator is not None:
        await runtime.coordinator.async_request_refresh()


def _summary(item: dict[str, Any], signer: Signer) -> dict[str, Any]:
    out = recipe_summary(item)
    out["image_url"] = signer.url(item.get("image"))
    out["category_ids"] = item.get("category_ids", [])
    return out


# ---------------------------------------------------------------------------
# Allgemein
# ---------------------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/info"})
@websocket_api.async_response
@_with_runtime
async def ws_info(hass, connection, msg, runtime) -> None:
    """Rechte und Einstellungen für das Panel."""
    try:
        resolve_ai_task_entity(hass, runtime.ai_task_entity)
        ai_available = True
    except RezeptbuchError:
        ai_available = False
    connection.send_result(
        msg["id"],
        {
            "version": VERSION,
            "is_admin": connection.user.is_admin,
            "default_servings": runtime.default_servings,
            "ai_task_available": ai_available,
        },
    )


# ---------------------------------------------------------------------------
# Rezepte
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipes/list",
        vol.Optional("query"): str,
        vol.Optional("category_id"): vol.Any(None, int),
        vol.Optional("include_subcategories", default=True): bool,
        vol.Optional("uncategorized", default=False): bool,
        vol.Optional("tags", default=[]): [str],
        vol.Optional("min_stars"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("never_cooked", default=False): bool,
        vol.Optional("not_cooked_days"): vol.Any(None, int),
        vol.Optional("sort", default="name"): vol.In(
            ["name", "rating", "last_cooked", "least_recently_cooked", "new", "updated", "relevance"]
        ),
        vol.Optional("limit", default=60): vol.All(int, vol.Range(min=1, max=500)),
        vol.Optional("offset", default=0): vol.All(int, vol.Range(min=0)),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_recipes_list(hass, connection, msg, runtime) -> None:
    """Gefilterte Rezeptliste."""
    result = await runtime.db.run(
        recipes.search_recipes,
        query=msg.get("query") or None,
        category_id=msg.get("category_id"),
        include_subcategories=msg["include_subcategories"],
        uncategorized=msg["uncategorized"],
        tags=msg["tags"],
        min_stars=msg.get("min_stars"),
        never_cooked=msg["never_cooked"],
        not_cooked_since_days=msg.get("not_cooked_days"),
        sort=msg["sort"],
        limit=msg["limit"],
        offset=msg["offset"],
    )
    signer = Signer(hass, connection.refresh_token_id)
    connection.send_result(
        msg["id"], {"total": result["total"], "items": [_summary(i, signer) for i in result["items"]]}
    )


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipe/get",
        vol.Required("recipe_id"): int,
        vol.Optional("version_id"): vol.Any(None, int),
        vol.Optional("servings"): vol.Any(None, vol.All(vol.Coerce(float), vol.Range(min=0.25, max=500))),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_recipe_get(hass, connection, msg, runtime) -> None:
    """Rezept mit (skalierter) Version, Bildern, Notizen, Bewertungen."""
    recipe = await runtime.db.run(recipes.get_recipe, msg["recipe_id"], msg.get("version_id"))
    history = await runtime.db.run(ratings.history, msg["recipe_id"], 50)
    signer = Signer(hass, connection.refresh_token_id)
    data = VersionData.from_dict(recipe["version"]["data"])
    scaled = scale_version(data, msg.get("servings"))
    user_ids = {h["user_id"] for h in history} | {u["user_id"] for u in recipe["stats"]["per_user"]}
    user_ids |= {a["user_id"] for a in recipe["annotations"]} | {v["user_id"] for v in recipe["versions"]}
    names = await async_user_names(hass, user_ids)
    recipe.pop("source_key", None)
    recipe["image_url"] = signer.url(recipe["image"])
    recipe["images"] = [{**i, "url": signer.url(i["path"])} for i in recipe["images"]]
    recipe["version"] = {**recipe["version"], "data": version_view(scaled), "original_servings": data.servings}
    recipe["versions"] = [{**v, "user_name": names.get(v["user_id"])} for v in recipe["versions"]]
    recipe["annotations"] = [{**a, "user_name": names.get(a["user_id"])} for a in recipe["annotations"]]
    recipe["stats"]["per_user"] = [{**u, "user_name": names.get(u["user_id"])} for u in recipe["stats"]["per_user"]]
    recipe["history"] = [
        {**h, "user_name": names.get(h["user_id"]), "photo_url": signer.url(h.get("photo"))} for h in history
    ]
    connection.send_result(msg["id"], recipe)


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipe/diff",
        vol.Required("old_version_id"): int,
        vol.Required("new_version_id"): int,
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_recipe_diff(hass, connection, msg, runtime) -> None:
    """Diff zwischen zwei Versionen."""
    connection.send_result(msg["id"], await runtime.db.run(versions.diff, msg["old_version_id"], msg["new_version_id"]))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipe/set_default_version",
        vol.Required("recipe_id"): int,
        vol.Required("version_id"): int,
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_set_default_version(hass, connection, msg, runtime) -> None:
    """Version als Standard markieren (Original jederzeit wieder wählbar)."""
    await runtime.db.run(versions.set_default_version, msg["recipe_id"], msg["version_id"])
    await _refresh(runtime)
    connection.send_result(msg["id"], {"default_version_id": msg["version_id"]})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipe/rate",
        vol.Required("recipe_id"): int,
        vol.Optional("stars"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("comment"): vol.Any(None, str),
        vol.Optional("cooked", default=True): bool,
        vol.Optional("servings"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("version_id"): vol.Any(None, int),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_recipe_rate(hass, connection, msg, runtime) -> None:
    """Bewertung/Kochvorgang des angemeldeten Benutzers speichern."""
    entry_id = await runtime.db.run(
        ratings.add_cook_log,
        msg["recipe_id"],
        stars=msg.get("stars"),
        comment=msg.get("comment"),
        cooked=msg["cooked"],
        servings=msg.get("servings"),
        version_id=msg.get("version_id"),
        user_id=connection.user.id,
    )
    await _refresh(runtime)
    connection.send_result(msg["id"], {"cook_log_id": entry_id})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/recipe/annotate",
        vol.Required("recipe_id"): int,
        vol.Required("text"): str,
        vol.Optional("target_type", default="recipe"): vol.In(["recipe", "ingredient", "step"]),
        vol.Optional("target_index"): vol.Any(None, int),
        vol.Optional("version_id"): vol.Any(None, int),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_recipe_annotate(hass, connection, msg, runtime) -> None:
    """Inline-Notiz anlegen."""
    annotation_id = await runtime.db.run(
        versions.add_annotation,
        msg["recipe_id"],
        text=msg["text"],
        target_type=msg["target_type"],
        target_index=msg.get("target_index"),
        version_id=msg.get("version_id"),
        user_id=connection.user.id,
    )
    connection.send_result(msg["id"], {"annotation_id": annotation_id})


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/recipe/delete", vol.Required("recipe_id"): int})
@websocket_api.require_admin
@websocket_api.async_response
@_with_runtime
async def ws_recipe_delete(hass, connection, msg, runtime) -> None:
    """Rezept löschen (nur Admins)."""
    paths = await runtime.db.run(recipes.delete_recipe, msg["recipe_id"])
    await async_delete_images(hass, runtime.storage, paths)
    await _refresh(runtime)
    connection.send_result(msg["id"], {"deleted": True})


# ---------------------------------------------------------------------------
# Kategorien & Tags
# ---------------------------------------------------------------------------


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/categories"})
@websocket_api.async_response
@_with_runtime
async def ws_categories(hass, connection, msg, runtime) -> None:
    """Kategoriebaum mit Zählung."""
    connection.send_result(msg["id"], await runtime.db.run(cats.get_tree))


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/tags"})
@websocket_api.async_response
@_with_runtime
async def ws_tags(hass, connection, msg, runtime) -> None:
    """Alle Tags mit Anzahl."""
    connection.send_result(msg["id"], {"tags": await runtime.db.run(recipes.list_tags)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/category/create",
        vol.Required("name"): str,
        vol.Optional("parent_id"): vol.Any(None, int),
        vol.Optional("icon"): vol.Any(None, str),
        vol.Optional("color"): vol.Any(None, str),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_category_create(hass, connection, msg, runtime) -> None:
    """Kategorie anlegen."""
    cid = await runtime.db.run(
        cats.create_category, msg["name"], msg.get("parent_id"), msg.get("icon"), msg.get("color")
    )
    await _refresh(runtime)
    connection.send_result(msg["id"], {"category_id": cid})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/category/update",
        vol.Required("category_id"): int,
        vol.Optional("name"): str,
        vol.Optional("icon"): str,
        vol.Optional("color"): str,
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_category_update(hass, connection, msg, runtime) -> None:
    """Kategorie umbenennen, Icon/Farbe ändern."""
    await runtime.db.run(
        cats.update_category, msg["category_id"], name=msg.get("name"), icon=msg.get("icon"), color=msg.get("color")
    )
    await _refresh(runtime)
    connection.send_result(msg["id"], {})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/category/move",
        vol.Required("category_id"): int,
        vol.Optional("parent_id"): vol.Any(None, int),
        vol.Optional("position"): vol.Any(None, int),
    }
)
@websocket_api.require_admin
@websocket_api.async_response
@_with_runtime
async def ws_category_move(hass, connection, msg, runtime) -> None:
    """Kategorie verschieben (nur Admins)."""
    await runtime.db.run(cats.move_category, msg["category_id"], msg.get("parent_id"), msg.get("position"))
    await _refresh(runtime)
    connection.send_result(msg["id"], {})


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/category/delete", vol.Required("category_id"): int})
@websocket_api.require_admin
@websocket_api.async_response
@_with_runtime
async def ws_category_delete(hass, connection, msg, runtime) -> None:
    """Kategorie löschen (nur Admins)."""
    result = await runtime.db.run(cats.delete_category, msg["category_id"])
    await _refresh(runtime)
    connection.send_result(msg["id"], result)


# ---------------------------------------------------------------------------
# Import & Entwürfe
# ---------------------------------------------------------------------------


def _draft_view(draft: dict[str, Any], signer: Signer) -> dict[str, Any]:
    data = dict(draft["data"])
    version = VersionData.from_dict(data.get("version"))
    images = list(dict.fromkeys([*(draft["image_paths"] or []), *([data["image"]] if data.get("image") else [])]))
    return {
        "id": draft["id"],
        "source_type": draft["source_type"],
        "created": draft["created"],
        "updated": draft["updated"],
        "title": data.get("title") or "",
        "description": data.get("description") or "",
        "source_url": data.get("source_url"),
        "image": data.get("image"),
        "images": [{"path": p, "url": signer.url(p)} for p in images],
        "version": version_view(version),
        "ingredient_lines": ingredient_lines(version),
        "step_lines": [s.text for s in version.steps],
        "category_ids": data.get("category_ids") or [],
        "tags": data.get("tags") or [],
        "warnings": data.get("warnings") or [],
        "similar_recipes": data.get("similar_recipes") or [],
    }


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/drafts"})
@websocket_api.async_response
@_with_runtime
async def ws_drafts(hass, connection, msg, runtime) -> None:
    """Offene Entwürfe (alle Benutzer)."""
    signer = Signer(hass, connection.refresh_token_id)
    items = await runtime.db.run(drafts.list_drafts)
    connection.send_result(msg["id"], {"drafts": [_draft_view(d, signer) for d in items]})


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/draft/get", vol.Required("draft_id"): int})
@websocket_api.async_response
@_with_runtime
async def ws_draft_get(hass, connection, msg, runtime) -> None:
    """Ein Entwurf."""
    draft = await runtime.db.run(drafts.get_draft, msg["draft_id"])
    connection.send_result(msg["id"], _draft_view(draft, Signer(hass, connection.refresh_token_id)))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/draft/update",
        vol.Required("draft_id"): int,
        vol.Optional("title"): str,
        vol.Optional("description"): str,
        vol.Optional("image"): vol.Any(None, str),
        vol.Optional("category_ids"): [int],
        vol.Optional("tags"): [str],
        vol.Optional("servings"): vol.Any(None, vol.Coerce(float)),
        vol.Optional("servings_unit"): vol.Any(None, str),
        vol.Optional("prep_time"): vol.Any(None, int),
        vol.Optional("cook_time"): vol.Any(None, int),
        vol.Optional("total_time"): vol.Any(None, int),
        vol.Optional("ingredient_lines"): [str],
        vol.Optional("step_lines"): [str],
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_draft_update(hass, connection, msg, runtime) -> None:
    """Entwurf bearbeiten; Zutaten/Schritte als Textzeilen (laufen durch den Parser)."""

    def _update(conn) -> dict[str, Any]:
        draft = drafts.get_draft(conn, msg["draft_id"])
        allowed = set(draft["image_paths"]) | ({draft["data"]["image"]} if draft["data"].get("image") else set())
        if msg.get("image") and msg["image"] not in allowed:
            raise ValidationError("Das Rezeptbild muss eines der Bilder dieses Entwurfs sein")
        version = VersionData.from_dict(draft["data"].get("version"))
        for key in ("servings", "servings_unit", "prep_time", "cook_time", "total_time"):
            if key in msg:
                setattr(version, key, msg[key])
        version = apply_lines(version, msg.get("ingredient_lines"), msg.get("step_lines"))
        changes: dict[str, Any] = {"version": VersionData.from_dict(version.to_dict()).to_dict()}
        for key in ("title", "description", "image", "category_ids", "tags"):
            if key in msg:
                changes[key] = msg[key]
        return drafts.update_draft(conn, msg["draft_id"], changes)

    draft = await runtime.db.run(_update)
    connection.send_result(msg["id"], _draft_view(draft, Signer(hass, connection.refresh_token_id)))


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/draft/confirm",
        vol.Required("draft_id"): int,
        vol.Optional("allow_duplicate", default=False): bool,
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_draft_confirm(hass, connection, msg, runtime) -> None:
    """Entwurf als Rezept übernehmen."""
    result = await runtime.db.run(
        drafts.confirm_draft, msg["draft_id"], None, user_id=connection.user.id, allow_duplicate=msg["allow_duplicate"]
    )
    await _refresh(runtime)
    connection.send_result(msg["id"], result)


@websocket_api.websocket_command({vol.Required("type"): "rezeptbuch/draft/discard", vol.Required("draft_id"): int})
@websocket_api.async_response
@_with_runtime
async def ws_draft_discard(hass, connection, msg, runtime) -> None:
    """Entwurf verwerfen (inkl. Bilddateien)."""
    result = await async_discard_draft(hass, runtime.db, runtime.storage, msg["draft_id"])
    connection.send_result(msg["id"], {"deleted_files": len(result.files)})


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/import/url",
        vol.Required("url"): str,
        vol.Optional("allow_duplicate", default=False): bool,
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_import_url(hass, connection, msg, runtime) -> None:
    """URL importieren → Entwurf oder Duplikat-Hinweis."""
    result = await async_import_url(
        hass,
        runtime.db,
        runtime.storage,
        msg["url"],
        user_id=connection.user.id,
        allow_duplicate=msg["allow_duplicate"],
        allow_private_networks=runtime.allow_private_networks,
    )
    if result["status"] == "duplicate":
        connection.send_result(msg["id"], result)
        return
    connection.send_result(
        msg["id"],
        {"status": "draft", "draft": _draft_view(result["draft"], Signer(hass, connection.refresh_token_id))},
    )


# ---------------------------------------------------------------------------
# Einkaufsliste
# ---------------------------------------------------------------------------


@websocket_api.websocket_command(
    {
        vol.Required("type"): "rezeptbuch/shopping/add",
        vol.Required("recipe_id"): int,
        vol.Optional("servings"): vol.Any(None, vol.Coerce(float)),
    }
)
@websocket_api.async_response
@_with_runtime
async def ws_shopping_add(hass, connection, msg, runtime) -> None:
    """Zutaten auf die Rezeptbuch-Einkaufsliste setzen."""
    changed = await runtime.db.run(add_recipe, msg["recipe_id"], msg.get("servings"))
    async_dispatcher_send(hass, SIGNAL_SHOPPING_UPDATED)
    connection.send_result(msg["id"], {"items": [i["summary"] for i in changed]})


COMMANDS = (
    ws_info,
    ws_recipes_list,
    ws_recipe_get,
    ws_recipe_diff,
    ws_set_default_version,
    ws_recipe_rate,
    ws_recipe_annotate,
    ws_recipe_delete,
    ws_categories,
    ws_tags,
    ws_category_create,
    ws_category_update,
    ws_category_move,
    ws_category_delete,
    ws_drafts,
    ws_draft_get,
    ws_draft_update,
    ws_draft_confirm,
    ws_draft_discard,
    ws_import_url,
    ws_shopping_add,
)


@callback
def async_register_commands(hass: HomeAssistant) -> None:
    """Alle Befehle registrieren (einmalig in async_setup)."""
    for command in COMMANDS:
        websocket_api.async_register_command(hass, command)
