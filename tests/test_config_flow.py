"""Config Flow und Options Flow – vollständig."""

from __future__ import annotations

from pathlib import Path

from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.data_entry_flow import FlowResultType
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rezeptbuch.config_flow import validate_storage_path
from custom_components.rezeptbuch.const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALLOW_PRIVATE_NETWORKS,
    CONF_CREATE_DEFAULT_CATEGORIES,
    CONF_DAILY_CATEGORY_IDS,
    CONF_DEFAULT_SERVINGS,
    CONF_IDEA_SENSORS,
    CONF_RATING_WEIGHT,
    CONF_RECENCY_WEIGHT,
    CONF_STORAGE_PATH,
    DOMAIN,
)
from custom_components.rezeptbuch.db import categories as cats

# --- Config Flow --------------------------------------------------------------------


@pytest.mark.parametrize("create_defaults", [True, False])
async def test_user_flow(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None, create_defaults: bool
) -> None:
    hass.config.config_dir = str(tmp_path)
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "user"
    result = await hass.config_entries.flow.async_configure(
        result["flow_id"], {CONF_CREATE_DEFAULT_CATEGORIES: create_defaults}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    assert result["title"] == "Rezeptbuch"
    assert result["data"] == {CONF_CREATE_DEFAULT_CATEGORIES: create_defaults}
    await hass.async_block_till_done()
    entry = hass.config_entries.async_entries(DOMAIN)[0]
    tree = await entry.runtime_data.db.run(cats.get_tree)
    assert bool(tree["categories"]) is create_defaults
    assert await hass.config_entries.async_unload(entry.entry_id)


async def test_single_instance(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.flow.async_init(DOMAIN, context={"source": config_entries.SOURCE_USER})
    assert result["type"] is FlowResultType.ABORT
    assert result["reason"] == "single_instance_allowed"


# --- Options Flow -------------------------------------------------------------------------


async def _open(hass: HomeAssistant, entry: MockConfigEntry, step: str) -> dict:
    result = await hass.config_entries.options.async_init(entry.entry_id)
    assert result["type"] is FlowResultType.MENU
    return await hass.config_entries.options.async_configure(result["flow_id"], {"next_step_id": step})


async def test_menu_without_ideas(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    result = await hass.config_entries.options.async_init(rb_entry.entry_id)
    assert result["menu_options"] == ["general", "daily", "idea_add"]


async def test_general_options(hass: HomeAssistant, rb_entry: MockConfigEntry, tmp_path: Path) -> None:
    hass.states.async_set("ai_task.meine_ki", "unknown")
    result = await _open(hass, rb_entry, "general")
    assert result["type"] is FlowResultType.FORM and result["step_id"] == "general"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {
            CONF_AI_TASK_ENTITY: "ai_task.meine_ki",
            CONF_DEFAULT_SERVINGS: 2,
            CONF_STORAGE_PATH: "rezeptbuch",
            CONF_ALLOW_PRIVATE_NETWORKS: True,
        },
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert rb_entry.options == {
        CONF_AI_TASK_ENTITY: "ai_task.meine_ki",
        CONF_DEFAULT_SERVINGS: 2,
        CONF_STORAGE_PATH: "rezeptbuch",
        CONF_ALLOW_PRIVATE_NETWORKS: True,
    }
    # Optionen werden nach Reload wirksam
    runtime = rb_entry.runtime_data
    assert runtime.ai_task_entity == "ai_task.meine_ki"
    assert runtime.allow_private_networks is True
    assert runtime.default_servings == 2

    # KI-Entität leeren → HA-Standard
    result = await _open(hass, rb_entry, "general")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DEFAULT_SERVINGS: 4, CONF_STORAGE_PATH: "rezeptbuch", CONF_ALLOW_PRIVATE_NETWORKS: False},
    )
    await hass.async_block_till_done()
    assert CONF_AI_TASK_ENTITY not in rb_entry.options
    assert rb_entry.runtime_data.ai_task_entity is None
    assert rb_entry.runtime_data.allow_private_networks is False


async def test_private_networks_default_off(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    assert rb_entry.runtime_data.allow_private_networks is False
    result = await _open(hass, rb_entry, "general")
    schema = result["data_schema"].schema
    default = next(k for k in schema if k == CONF_ALLOW_PRIVATE_NETWORKS).default()
    assert default is False


@pytest.mark.parametrize(
    "path",
    ["../geheim", "/etc", "//server/share", "C:\\Daten", "C:/Daten", "\\\\server\\x", "a/../../b", "", "  ", "/"],
)
async def test_general_invalid_path(hass: HomeAssistant, rb_entry: MockConfigEntry, path: str) -> None:
    result = await _open(hass, rb_entry, "general")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DEFAULT_SERVINGS: 4, CONF_STORAGE_PATH: path, CONF_ALLOW_PRIVATE_NETWORKS: False},
    )
    assert result["type"] is FlowResultType.FORM
    assert result["errors"] == {CONF_STORAGE_PATH: "invalid_path"}


@pytest.mark.parametrize(
    ("value", "expected"), [("rezeptbuch", "rezeptbuch"), ("daten/rezepte/", "daten/rezepte"), ("a\\b", "a/b")]
)
def test_validate_storage_path(value: str, expected: str) -> None:
    assert validate_storage_path(value) == expected


async def test_daily_options(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    categories = await rb_entry.runtime_data.db.run(cats.list_categories)
    backen = next(c for c in categories if c["name"] == "Backen")
    result = await _open(hass, rb_entry, "daily")
    assert result["step_id"] == "daily"
    options = result["data_schema"].schema[CONF_DAILY_CATEGORY_IDS].config["options"]
    assert {"value": str(backen["id"]), "label": "Backen"} in options
    assert any(o["label"] == "Backen › Kuchen" for o in options)
    result = await hass.config_entries.options.async_configure(
        result["flow_id"],
        {CONF_DAILY_CATEGORY_IDS: [str(backen["id"])], CONF_RATING_WEIGHT: 3, CONF_RECENCY_WEIGHT: 0.5},
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert rb_entry.options[CONF_DAILY_CATEGORY_IDS] == [backen["id"]]
    assert rb_entry.options[CONF_RATING_WEIGHT] == 3.0
    assert rb_entry.options[CONF_RECENCY_WEIGHT] == 0.5


async def test_idea_add_and_remove(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    categories = await rb_entry.runtime_data.db.run(cats.list_categories)
    backen = next(c for c in categories if c["name"] == "Backen")

    result = await _open(hass, rb_entry, "idea_add")
    assert result["step_id"] == "idea_add"
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "  ", "category_id": str(backen["id"]), "period": "weekly"}
    )
    assert result["errors"] == {"name": "name_required"}
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "Backidee der Woche", "category_id": str(backen["id"]), "period": "weekly"}
    )
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    ideas = rb_entry.options[CONF_IDEA_SENSORS]
    assert len(ideas) == 1 and ideas[0]["name"] == "Backidee der Woche" and ideas[0]["period"] == "weekly"
    state = hass.states.get("sensor.rezeptbuch_idee_backidee_der_woche")
    assert state is not None and state.attributes["period"] == "weekly"

    # gleicher Name nochmal → Fehler
    result = await _open(hass, rb_entry, "idea_add")
    result = await hass.config_entries.options.async_configure(
        result["flow_id"], {"name": "backidee der woche", "category_id": str(backen["id"]), "period": "daily"}
    )
    assert result["errors"] == {"name": "name_exists"}

    # Menü bietet jetzt „entfernen“ an
    menu = await hass.config_entries.options.async_init(rb_entry.entry_id)
    assert "idea_remove" in menu["menu_options"]
    result = await hass.config_entries.options.async_configure(menu["flow_id"], {"next_step_id": "idea_remove"})
    result = await hass.config_entries.options.async_configure(result["flow_id"], {"ideas": [ideas[0]["id"]]})
    assert result["type"] is FlowResultType.CREATE_ENTRY
    await hass.async_block_till_done()
    assert rb_entry.options[CONF_IDEA_SENSORS] == []
    assert hass.states.get("sensor.rezeptbuch_idee_backidee_der_woche") is None or (
        hass.states.get("sensor.rezeptbuch_idee_backidee_der_woche").state == "unavailable"
    )


async def test_idea_add_without_categories(
    hass: HomeAssistant, tmp_path: Path, enable_custom_integrations: None
) -> None:
    hass.config.config_dir = str(tmp_path)
    entry = MockConfigEntry(domain=DOMAIN, data={CONF_CREATE_DEFAULT_CATEGORIES: False})
    entry.add_to_hass(hass)
    assert await hass.config_entries.async_setup(entry.entry_id)
    await hass.async_block_till_done()
    result = await _open(hass, entry, "idea_add")
    assert result["type"] is FlowResultType.ABORT and result["reason"] == "no_categories"
    assert await hass.config_entries.async_unload(entry.entry_id)
