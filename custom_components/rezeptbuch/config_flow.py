"""Config Flow (Einrichtung) und Options Flow (Einstellungen)."""

from __future__ import annotations

from pathlib import PurePosixPath, PureWindowsPath
from typing import Any
import uuid

from homeassistant.config_entries import ConfigEntry, ConfigFlow, ConfigFlowResult, OptionsFlow
from homeassistant.core import callback
from homeassistant.helpers import selector
import voluptuous as vol

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALLOW_PRIVATE_NETWORKS,
    CONF_CREATE_DEFAULT_CATEGORIES,
    CONF_DAILY_CATEGORY_IDS,
    CONF_DEFAULT_SERVINGS,
    CONF_IDEA_SENSORS,
    CONF_RATING_WEIGHT,
    CONF_RECENCY_WEIGHT,
    CONF_STORAGE_PATH,
    DEFAULT_ALLOW_PRIVATE_NETWORKS,
    DEFAULT_RATING_WEIGHT,
    DEFAULT_RECENCY_WEIGHT,
    DEFAULT_SERVINGS,
    DEFAULT_STORAGE_DIR,
    DOMAIN,
    IDEA_CATEGORY_ID,
    IDEA_ID,
    IDEA_NAME,
    IDEA_PERIOD,
    NAME,
    PERIOD_DAILY,
    PERIODS,
)
from .db.categories import list_categories

CONF_IDEAS_TO_REMOVE = "ideas"


def validate_storage_path(value: str) -> str:
    """Speicherpfad relativ zum HA-Konfigurationsordner, ohne "..".

    Raises ValueError bei ungültigen Pfaden.
    """
    value = (value or "").strip().replace("\\", "/")
    if value.startswith("/") or PureWindowsPath(value).drive:
        raise ValueError("absolut")
    value = value.strip("/")
    if not value:
        raise ValueError("leer")
    parts = PurePosixPath(value).parts
    if any(p in ("..", ".") for p in parts):
        raise ValueError("..")
    return "/".join(parts)


class RezeptbuchConfigFlow(ConfigFlow, domain=DOMAIN):
    """Einrichtung über die Oberfläche."""

    VERSION = 1

    async def async_step_user(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Einziger Schritt: Standard-Kategorien anlegen?"""
        if user_input is not None:
            return self.async_create_entry(
                title=NAME,
                data={CONF_CREATE_DEFAULT_CATEGORIES: bool(user_input[CONF_CREATE_DEFAULT_CATEGORIES])},
            )
        return self.async_show_form(
            step_id="user",
            data_schema=vol.Schema({vol.Required(CONF_CREATE_DEFAULT_CATEGORIES, default=True): bool}),
        )

    @staticmethod
    @callback
    def async_get_options_flow(config_entry: ConfigEntry) -> OptionsFlow:
        """Options Flow."""
        return RezeptbuchOptionsFlow()


class RezeptbuchOptionsFlow(OptionsFlow):
    """Einstellungen als Menü."""

    async def _categories(self) -> list[dict[str, Any]]:
        runtime = getattr(self.config_entry, "runtime_data", None)
        if runtime is None:
            return []
        return await runtime.db.run(list_categories)

    def _ideas(self) -> list[dict[str, Any]]:
        return list(self.config_entry.options.get(CONF_IDEA_SENSORS) or [])

    def _save(self, changes: dict[str, Any]) -> ConfigFlowResult:
        options = {**self.config_entry.options, **changes}
        return self.async_create_entry(data={k: v for k, v in options.items() if v is not None})

    async def async_step_init(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Menü."""
        menu = ["general", "daily", "idea_add"]
        if self._ideas():
            menu.append("idea_remove")
        return self.async_show_menu(step_id="init", menu_options=menu)

    async def async_step_general(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """KI-Entität, Portionen, Speicherpfad, private Netzwerke."""
        opts = self.config_entry.options
        errors: dict[str, str] = {}
        if user_input is not None:
            try:
                path = validate_storage_path(user_input.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_DIR))
            except ValueError:
                errors[CONF_STORAGE_PATH] = "invalid_path"
            else:
                return self._save(
                    {
                        CONF_AI_TASK_ENTITY: user_input.get(CONF_AI_TASK_ENTITY) or None,
                        CONF_DEFAULT_SERVINGS: int(user_input[CONF_DEFAULT_SERVINGS]),
                        CONF_STORAGE_PATH: path,
                        CONF_ALLOW_PRIVATE_NETWORKS: bool(user_input[CONF_ALLOW_PRIVATE_NETWORKS]),
                    }
                )
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_AI_TASK_ENTITY,
                    description={"suggested_value": opts.get(CONF_AI_TASK_ENTITY)},
                ): selector.EntitySelector(selector.EntitySelectorConfig(domain="ai_task")),
                vol.Required(
                    CONF_DEFAULT_SERVINGS, default=opts.get(CONF_DEFAULT_SERVINGS, DEFAULT_SERVINGS)
                ): selector.NumberSelector(
                    selector.NumberSelectorConfig(min=1, max=50, step=1, mode=selector.NumberSelectorMode.BOX)
                ),
                vol.Required(
                    CONF_STORAGE_PATH, default=opts.get(CONF_STORAGE_PATH, DEFAULT_STORAGE_DIR)
                ): selector.TextSelector(),
                vol.Required(
                    CONF_ALLOW_PRIVATE_NETWORKS,
                    default=opts.get(CONF_ALLOW_PRIVATE_NETWORKS, DEFAULT_ALLOW_PRIVATE_NETWORKS),
                ): selector.BooleanSelector(),
            }
        )
        return self.async_show_form(step_id="general", data_schema=schema, errors=errors)

    async def async_step_daily(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Rezept des Tages: Kategorie-Filter und Gewichtung."""
        opts = self.config_entry.options
        if user_input is not None:
            return self._save(
                {
                    CONF_DAILY_CATEGORY_IDS: [int(c) for c in user_input.get(CONF_DAILY_CATEGORY_IDS) or []],
                    CONF_RATING_WEIGHT: float(user_input[CONF_RATING_WEIGHT]),
                    CONF_RECENCY_WEIGHT: float(user_input[CONF_RECENCY_WEIGHT]),
                }
            )
        categories = await self._categories()
        weight_selector = selector.NumberSelector(
            selector.NumberSelectorConfig(min=0, max=5, step=0.5, mode=selector.NumberSelectorMode.SLIDER)
        )
        schema = vol.Schema(
            {
                vol.Optional(
                    CONF_DAILY_CATEGORY_IDS,
                    default=[str(c) for c in opts.get(CONF_DAILY_CATEGORY_IDS) or []],
                ): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=str(c["id"]), label=c["path"]) for c in categories],
                        multiple=True,
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(
                    CONF_RATING_WEIGHT, default=opts.get(CONF_RATING_WEIGHT, DEFAULT_RATING_WEIGHT)
                ): weight_selector,
                vol.Required(
                    CONF_RECENCY_WEIGHT, default=opts.get(CONF_RECENCY_WEIGHT, DEFAULT_RECENCY_WEIGHT)
                ): weight_selector,
            }
        )
        return self.async_show_form(step_id="daily", data_schema=schema)

    async def async_step_idea_add(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ideen-Sensor anlegen (z. B. „Backidee der Woche“)."""
        categories = await self._categories()
        if not categories:
            return self.async_abort(reason="no_categories")
        errors: dict[str, str] = {}
        if user_input is not None:
            name = (user_input.get(IDEA_NAME) or "").strip()
            if not name:
                errors[IDEA_NAME] = "name_required"
            elif any(i[IDEA_NAME].casefold() == name.casefold() for i in self._ideas()):
                errors[IDEA_NAME] = "name_exists"
            else:
                idea = {
                    IDEA_ID: uuid.uuid4().hex[:8],
                    IDEA_NAME: name,
                    IDEA_CATEGORY_ID: int(user_input[IDEA_CATEGORY_ID]),
                    IDEA_PERIOD: user_input.get(IDEA_PERIOD, PERIOD_DAILY),
                }
                return self._save({CONF_IDEA_SENSORS: [*self._ideas(), idea]})
        schema = vol.Schema(
            {
                vol.Required(IDEA_NAME): selector.TextSelector(),
                vol.Required(IDEA_CATEGORY_ID): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=str(c["id"]), label=c["path"]) for c in categories],
                        mode=selector.SelectSelectorMode.DROPDOWN,
                    )
                ),
                vol.Required(IDEA_PERIOD, default=PERIOD_DAILY): selector.SelectSelector(
                    selector.SelectSelectorConfig(options=list(PERIODS), translation_key="period")
                ),
            }
        )
        return self.async_show_form(step_id="idea_add", data_schema=schema, errors=errors)

    async def async_step_idea_remove(self, user_input: dict[str, Any] | None = None) -> ConfigFlowResult:
        """Ideen-Sensoren entfernen."""
        ideas = self._ideas()
        if not ideas:
            return self.async_abort(reason="no_ideas")
        if user_input is not None:
            remove = set(user_input.get(CONF_IDEAS_TO_REMOVE) or [])
            return self._save({CONF_IDEA_SENSORS: [i for i in ideas if i[IDEA_ID] not in remove]})
        schema = vol.Schema(
            {
                vol.Optional(CONF_IDEAS_TO_REMOVE, default=[]): selector.SelectSelector(
                    selector.SelectSelectorConfig(
                        options=[selector.SelectOptionDict(value=i[IDEA_ID], label=i[IDEA_NAME]) for i in ideas],
                        multiple=True,
                        mode=selector.SelectSelectorMode.LIST,
                    )
                )
            }
        )
        return self.async_show_form(step_id="idea_remove", data_schema=schema)
