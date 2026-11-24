"""Aktionen (Services) der Integration.

Registriert in async_setup (nicht pro Eintrag). Aktionen mit Ergebnis liefern
eine Antwort (SupportsResponse), damit Automationen z. B. recipe_id oder
draft_id weiterverwenden können.
"""

from __future__ import annotations

from collections.abc import Awaitable, Callable
import functools
import logging
from pathlib import Path
from typing import Any

from homeassistant.components import media_source
from homeassistant.core import HomeAssistant, ServiceCall, ServiceResponse, SupportsResponse, callback
from homeassistant.exceptions import HomeAssistantError, ServiceValidationError
from homeassistant.helpers import config_validation as cv
from homeassistant.helpers.dispatcher import async_dispatcher_send
import voluptuous as vol

from .const import DOMAIN, SIGNAL_SHOPPING_UPDATED
from .coordinator import recipe_summary
from .db import ConflictError, DatabaseError, NotFoundError, categories as cats, drafts, ratings, recipes
from .errors import AiTaskFailed, FetchFailed, RezeptbuchError
from .images import async_delete_images
from .importer.photo import async_import_photos
from .importer.url import async_import_url
from .models import ValidationError, VersionData
from .runtime import RezeptbuchRuntime, async_get_runtime
from .scaling import format_ingredient, scale_version
from .shopping_list import add_recipe, item_summary, recipe_ingredients

_LOGGER = logging.getLogger(__name__)

SERVICE_IMPORT_URL = "import_url"
SERVICE_IMPORT_IMAGE = "import_image"
SERVICE_CONFIRM_DRAFT = "confirm_draft"
SERVICE_DISCARD_DRAFT = "discard_draft"
SERVICE_SEARCH = "search"
SERVICE_GET_RECIPE = "get_recipe"
SERVICE_RANDOM_RECIPE = "random_recipe"
SERVICE_RATE_RECIPE = "rate_recipe"
SERVICE_ADD_TO_SHOPPING_LIST = "add_to_shopping_list"
SERVICE_CREATE_CATEGORY = "create_category"
SERVICE_ASSIGN_CATEGORY = "assign_category"
SERVICE_DELETE_RECIPE = "delete_recipe"

OWN_TODO_ENTITY = f"todo.{DOMAIN}_einkaufsliste"

# Laufzeitfehler (nicht vom Nutzer verursacht) → HomeAssistantError
_RUNTIME_ERRORS = (FetchFailed, AiTaskFailed)

_ids = vol.All(cv.ensure_list, [vol.Coerce(int)])
_tags = vol.All(cv.ensure_list, [cv.string])
_stars = vol.All(vol.Coerce(float), vol.Range(min=0.5, max=5))

SCHEMAS: dict[str, vol.Schema] = {
    SERVICE_IMPORT_URL: vol.Schema(
        {
            vol.Required("url"): cv.string,
            vol.Optional("category_ids", default=list): _ids,
            vol.Optional("tags", default=list): _tags,
            vol.Optional("confirm", default=False): cv.boolean,
            vol.Optional("allow_duplicate", default=False): cv.boolean,
        }
    ),
    SERVICE_IMPORT_IMAGE: vol.Schema(
        {
            vol.Optional("files", default=list): vol.All(cv.ensure_list, [cv.string]),
            vol.Optional("media", default=list): vol.All(cv.ensure_list, [vol.Any(cv.string, dict)]),
            vol.Optional("category_ids", default=list): _ids,
            vol.Optional("tags", default=list): _tags,
            vol.Optional("confirm", default=False): cv.boolean,
        }
    ),
    SERVICE_CONFIRM_DRAFT: vol.Schema(
        {
            vol.Required("draft_id"): vol.Coerce(int),
            vol.Optional("title"): cv.string,
            vol.Optional("category_ids"): _ids,
            vol.Optional("tags"): _tags,
            vol.Optional("allow_duplicate", default=False): cv.boolean,
        }
    ),
    SERVICE_DISCARD_DRAFT: vol.Schema({vol.Required("draft_id"): vol.Coerce(int)}),
    SERVICE_SEARCH: vol.Schema(
        {
            vol.Optional("query"): cv.string,
            vol.Optional("category_id"): vol.Coerce(int),
            vol.Optional("include_subcategories", default=True): cv.boolean,
            vol.Optional("tags", default=list): _tags,
            vol.Optional("min_stars"): _stars,
            vol.Optional("never_cooked", default=False): cv.boolean,
            vol.Optional("not_cooked_days"): vol.All(vol.Coerce(int), vol.Range(min=1)),
            vol.Optional("sort", default="name"): vol.In(
                ["name", "rating", "last_cooked", "least_recently_cooked", "new", "relevance"]
            ),
            vol.Optional("limit", default=20): vol.All(vol.Coerce(int), vol.Range(min=1, max=200)),
        }
    ),
    SERVICE_GET_RECIPE: vol.Schema(
        {
            vol.Required("recipe_id"): vol.Coerce(int),
            vol.Optional("version_id"): vol.Coerce(int),
            vol.Optional("servings"): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=500)),
        }
    ),
    SERVICE_RANDOM_RECIPE: vol.Schema(
        {
            vol.Optional("category_id"): vol.Coerce(int),
            vol.Optional("tags", default=list): _tags,
            vol.Optional("min_stars"): _stars,
        }
    ),
    SERVICE_RATE_RECIPE: vol.Schema(
        {
            vol.Required("recipe_id"): vol.Coerce(int),
            vol.Optional("stars"): _stars,
            vol.Optional("comment"): cv.string,
            vol.Optional("cooked", default=True): cv.boolean,
            vol.Optional("servings"): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=500)),
        }
    ),
    SERVICE_ADD_TO_SHOPPING_LIST: vol.Schema(
        {
            vol.Required("recipe_id"): vol.Coerce(int),
            vol.Optional("servings"): vol.All(vol.Coerce(float), vol.Range(min=0.25, max=500)),
            vol.Optional("todo_entity"): cv.entity_id,
        }
    ),
    SERVICE_CREATE_CATEGORY: vol.Schema(
        {
            vol.Required("name"): cv.string,
            vol.Optional("parent_id"): vol.Coerce(int),
            vol.Optional("icon"): cv.icon,
            vol.Optional("color"): cv.string,
        }
    ),
    SERVICE_ASSIGN_CATEGORY: vol.Schema(
        {
            vol.Required("recipe_id"): vol.Coerce(int),
            vol.Required("category_ids"): _ids,
            vol.Optional("replace", default=True): cv.boolean,
        }
    ),
    SERVICE_DELETE_RECIPE: vol.Schema({vol.Required("recipe_id"): vol.Coerce(int)}),
}


def _translate_error(err: Exception) -> HomeAssistantError:
    """Fachliche Fehler → übersetzte HA-Fehler."""
    if isinstance(err, RezeptbuchError):
        cls = HomeAssistantError if isinstance(err, _RUNTIME_ERRORS) else ServiceValidationError
        return cls(
            str(err),
            translation_domain=DOMAIN,
            translation_key=err.translation_key,
            translation_placeholders=err.placeholders,
        )
    key = {NotFoundError: "not_found", ConflictError: "conflict", ValidationError: "invalid_input"}.get(
        type(err), "invalid_input"
    )
    return ServiceValidationError(
        str(err), translation_domain=DOMAIN, translation_key=key, translation_placeholders={"message": str(err)}
    )


def _runtime(hass: HomeAssistant) -> RezeptbuchRuntime:
    runtime = async_get_runtime(hass)
    if runtime is None:
        raise ServiceValidationError(
            "Rezeptbuch ist nicht geladen", translation_domain=DOMAIN, translation_key="not_loaded"
        )
    return runtime


Handler = Callable[[ServiceCall, RezeptbuchRuntime], Awaitable[ServiceResponse]]


def _wrap(func: Handler) -> Callable[[ServiceCall], Awaitable[ServiceResponse]]:
    @functools.wraps(func)
    async def _handler(call: ServiceCall) -> ServiceResponse:
        runtime = _runtime(call.hass)
        try:
            return await func(call, runtime)
        except (RezeptbuchError, DatabaseError, ValidationError) as err:
            raise _translate_error(err) from err

    return _handler


async def _refresh(hass: HomeAssistant, runtime: RezeptbuchRuntime) -> None:
    if runtime.coordinator is not None:
        await runtime.coordinator.async_request_refresh()


# ---------------------------------------------------------------------------
# Import
# ---------------------------------------------------------------------------


async def _confirm(
    hass: HomeAssistant,
    runtime: RezeptbuchRuntime,
    draft_id: int,
    overrides: dict[str, Any] | None,
    user_id: str | None,
    allow_duplicate: bool,
) -> dict[str, Any]:
    result = await runtime.db.run(
        drafts.confirm_draft, draft_id, overrides, user_id=user_id, allow_duplicate=allow_duplicate
    )
    await _refresh(hass, runtime)
    recipe = await runtime.db.run(recipes.get_recipe, result["recipe_id"])
    return {"status": "created", "recipe_id": result["recipe_id"], "title": recipe["title"]}


async def _import_url(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    data = call.data
    result = await async_import_url(
        call.hass,
        runtime.db,
        runtime.storage,
        data["url"],
        user_id=call.context.user_id,
        category_ids=data["category_ids"],
        tags=data["tags"],
        allow_duplicate=data["allow_duplicate"],
        allow_private_networks=runtime.allow_private_networks,
    )
    if result["status"] == "duplicate":
        return {k: result[k] for k in ("status", "recipe_id", "title", "source_url")}
    response = {
        "status": "draft",
        "draft_id": result["draft_id"],
        "title": result["draft"]["data"]["title"],
        "warnings": result["warnings"],
    }
    if data["confirm"]:
        confirmed = await _confirm(
            call.hass, runtime, result["draft_id"], None, call.context.user_id, data["allow_duplicate"]
        )
        response = {**confirmed, "warnings": result["warnings"]}
    return response


async def _read_photo(hass: HomeAssistant, path: str) -> bytes:
    if not hass.config.is_allowed_path(path):
        raise ServiceValidationError(
            f"Zugriff auf {path} nicht erlaubt",
            translation_domain=DOMAIN,
            translation_key="path_not_allowed",
            translation_placeholders={"path": path},
        )
    try:
        return await hass.async_add_executor_job(Path(path).read_bytes)
    except OSError as err:
        raise ServiceValidationError(
            f"Datei nicht lesbar: {path}",
            translation_domain=DOMAIN,
            translation_key="path_not_allowed",
            translation_placeholders={"path": path},
        ) from err


async def _read_media(hass: HomeAssistant, item: str | dict[str, Any]) -> bytes:
    media_id = item if isinstance(item, str) else item.get("media_content_id", "")
    try:
        resolved = await media_source.async_resolve_media(hass, media_id, None)
    except HomeAssistantError as err:
        raise ServiceValidationError(
            str(err),
            translation_domain=DOMAIN,
            translation_key="media_not_local",
            translation_placeholders={"media": media_id},
        ) from err
    if resolved.path is None:
        raise ServiceValidationError(
            f"Medium ist keine lokale Datei: {media_id}",
            translation_domain=DOMAIN,
            translation_key="media_not_local",
            translation_placeholders={"media": media_id},
        )
    return await hass.async_add_executor_job(Path(resolved.path).read_bytes)


async def _import_image(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    hass = call.hass
    photos = [await _read_photo(hass, p) for p in call.data["files"]]
    photos += [await _read_media(hass, m) for m in call.data["media"]]
    result = await async_import_photos(
        hass,
        runtime.db,
        runtime.storage,
        photos,
        user_id=call.context.user_id,
        ai_task_entity=runtime.ai_task_entity,
        category_ids=call.data["category_ids"],
        tags=call.data["tags"],
    )
    response = {
        "status": "draft",
        "draft_id": result["draft_id"],
        "title": result["draft"]["data"]["title"],
        "warnings": result["warnings"],
    }
    if call.data["confirm"]:
        confirmed = await _confirm(hass, runtime, result["draft_id"], None, call.context.user_id, True)
        response = {**confirmed, "warnings": result["warnings"]}
    return response


async def _confirm_draft(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    overrides = {k: call.data[k] for k in ("title", "category_ids", "tags") if k in call.data}
    return await _confirm(
        call.hass, runtime, call.data["draft_id"], overrides, call.context.user_id, call.data["allow_duplicate"]
    )


async def _discard_draft(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    from .cleanup import async_discard_draft

    result = await async_discard_draft(call.hass, runtime.db, runtime.storage, call.data["draft_id"])
    return {"deleted_files": len(result.files)}


# ---------------------------------------------------------------------------
# Lesen
# ---------------------------------------------------------------------------


async def _search(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    d = call.data
    result = await runtime.db.run(
        recipes.search_recipes,
        query=d.get("query"),
        category_id=d.get("category_id"),
        include_subcategories=d["include_subcategories"],
        tags=d["tags"],
        min_stars=d.get("min_stars"),
        never_cooked=d["never_cooked"],
        not_cooked_since_days=d.get("not_cooked_days"),
        sort=d["sort"],
        limit=d["limit"],
    )
    return {"total": result["total"], "recipes": [recipe_summary(i) for i in result["items"]]}


async def _get_recipe(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    recipe = await runtime.db.run(recipes.get_recipe, call.data["recipe_id"], call.data.get("version_id"))
    data = VersionData.from_dict(recipe["version"]["data"])
    scaled = scale_version(data, call.data.get("servings"))
    return {
        "recipe_id": recipe["id"],
        "title": recipe["title"],
        "description": recipe["description"],
        "source_url": recipe["source_url"],
        "source_type": recipe["source_type"],
        "image_url": recipe_summary(recipe)["image_url"],
        "version_id": recipe["version"]["id"],
        "version_label": recipe["version"]["label"],
        "servings": scaled.servings,
        "servings_unit": scaled.servings_unit,
        "prep_time": scaled.prep_time,
        "cook_time": scaled.cook_time,
        "total_time": scaled.total_time,
        "ingredients": [i.to_dict() | {"text": format_ingredient(i)} for i in scaled.ingredients],
        "steps": [s.to_dict() for s in scaled.steps],
        "categories": [" › ".join(c["path"]) for c in recipe["categories"]],
        "tags": recipe["tags"],
        "stats": recipe["stats"],
        "versions": [
            {k: v[k] for k in ("id", "version_no", "label", "is_original", "is_default")} for v in recipe["versions"]
        ],
    }


async def _random_recipe(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    item = await runtime.db.run(
        recipes.random_recipe,
        category_id=call.data.get("category_id"),
        tags=call.data["tags"],
        min_stars=call.data.get("min_stars"),
    )
    return {"recipe": recipe_summary(item) if item else None}


# ---------------------------------------------------------------------------
# Ändern
# ---------------------------------------------------------------------------


async def _rate_recipe(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    entry_id = await runtime.db.run(
        ratings.add_cook_log,
        call.data["recipe_id"],
        stars=call.data.get("stars"),
        comment=call.data.get("comment"),
        cooked=call.data["cooked"],
        servings=call.data.get("servings"),
        user_id=call.context.user_id,
    )
    stats = await runtime.db.run(ratings.recipe_stats, call.data["recipe_id"])
    await _refresh(call.hass, runtime)
    return {"cook_log_id": entry_id, "avg_stars": stats["avg_stars"], "rating_count": stats["rating_count"]}


async def _add_to_shopping_list(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    hass = call.hass
    target = call.data.get("todo_entity")
    recipe_id = call.data["recipe_id"]
    servings = call.data.get("servings")
    if target and target != OWN_TODO_ENTITY:
        if hass.states.get(target) is None:
            raise ServiceValidationError(
                f"{target} nicht gefunden",
                translation_domain=DOMAIN,
                translation_key="not_found",
                translation_placeholders={"message": target},
            )
        recipe, ingredients = await runtime.db.run(recipe_ingredients, recipe_id, servings)
        added = []
        for ing in ingredients:
            summary = item_summary(ing.name, ing.amount, ing.unit, ing.amount_max, ing.note)
            await hass.services.async_call(
                "todo",
                "add_item",
                {"item": summary, "description": f"für: {recipe['title']}"},
                target={"entity_id": target},
                blocking=True,
            )
            added.append(summary)
        return {"todo_entity": target, "items": added}
    changed = await runtime.db.run(add_recipe, recipe_id, servings)
    async_dispatcher_send(hass, SIGNAL_SHOPPING_UPDATED)
    return {"todo_entity": OWN_TODO_ENTITY, "items": [i["summary"] for i in changed]}


async def _create_category(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    cid = await runtime.db.run(
        cats.create_category,
        call.data["name"],
        call.data.get("parent_id"),
        call.data.get("icon"),
        call.data.get("color"),
    )
    await _refresh(call.hass, runtime)
    return {"category_id": cid, "path": await runtime.db.run(cats.category_path, cid)}


async def _assign_category(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    await runtime.db.run(
        cats.set_recipe_categories, call.data["recipe_id"], call.data["category_ids"], call.data["replace"]
    )
    await _refresh(call.hass, runtime)
    names = await runtime.db.run(cats.recipe_categories, call.data["recipe_id"])
    return {"categories": [" › ".join(c["path"]) for c in names]}


async def _delete_recipe(call: ServiceCall, runtime: RezeptbuchRuntime) -> ServiceResponse:
    paths = await runtime.db.run(recipes.delete_recipe, call.data["recipe_id"])  # committet
    await async_delete_images(call.hass, runtime.storage, paths)
    await _refresh(call.hass, runtime)
    return {"deleted": True, "deleted_files": len(paths)}


HANDLERS: dict[str, tuple[Handler, SupportsResponse]] = {
    SERVICE_IMPORT_URL: (_import_url, SupportsResponse.OPTIONAL),
    SERVICE_IMPORT_IMAGE: (_import_image, SupportsResponse.OPTIONAL),
    SERVICE_CONFIRM_DRAFT: (_confirm_draft, SupportsResponse.OPTIONAL),
    SERVICE_DISCARD_DRAFT: (_discard_draft, SupportsResponse.OPTIONAL),
    SERVICE_SEARCH: (_search, SupportsResponse.ONLY),
    SERVICE_GET_RECIPE: (_get_recipe, SupportsResponse.ONLY),
    SERVICE_RANDOM_RECIPE: (_random_recipe, SupportsResponse.ONLY),
    SERVICE_RATE_RECIPE: (_rate_recipe, SupportsResponse.OPTIONAL),
    SERVICE_ADD_TO_SHOPPING_LIST: (_add_to_shopping_list, SupportsResponse.OPTIONAL),
    SERVICE_CREATE_CATEGORY: (_create_category, SupportsResponse.OPTIONAL),
    SERVICE_ASSIGN_CATEGORY: (_assign_category, SupportsResponse.OPTIONAL),
    SERVICE_DELETE_RECIPE: (_delete_recipe, SupportsResponse.OPTIONAL),
}


@callback
def async_setup_services(hass: HomeAssistant) -> None:
    """Alle Aktionen registrieren (einmalig in async_setup)."""
    for name, (handler, supports_response) in HANDLERS.items():
        hass.services.async_register(
            DOMAIN, name, _wrap(handler), schema=SCHEMAS[name], supports_response=supports_response
        )
