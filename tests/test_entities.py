"""Sensoren, Rezept des Tages, Ideen-Sensoren, Einkaufsliste (todo), Diagnose."""

from __future__ import annotations

from datetime import date, timedelta
import json
from typing import Any
from unittest.mock import AsyncMock, patch

from freezegun.api import FrozenDateTimeFactory
from homeassistant.core import HomeAssistant, ServiceCall
from homeassistant.util import dt as dt_util
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry, async_fire_time_changed

from custom_components.rezeptbuch.const import (
    CONF_DAILY_CATEGORY_IDS,
    CONF_IDEA_SENSORS,
    DOMAIN,
)
from custom_components.rezeptbuch.db import categories as cats, ratings, recipes, shopping
from custom_components.rezeptbuch.diagnostics import async_get_config_entry_diagnostics
from custom_components.rezeptbuch.suggestions import period_id, pick, weight

SAMPLE = {
    "servings": 4,
    "ingredients": [
        {"amount": 500, "unit": "g", "name": "Mehl"},
        {"amount": 2, "unit": "EL", "name": "Zucker"},
        {"amount": 1, "unit": "Prise", "name": "Salz"},
        {"name": "Pfeffer", "note": "etwas"},
        {"amount": 1, "unit": "Dose", "name": "Tomaten"},
    ],
    "steps": [{"text": "Alles mischen."}],
}


async def add_recipe(entry: MockConfigEntry, title: str, **kwargs) -> int:
    return await entry.runtime_data.db.run(
        recipes.create_recipe, title=title, data=kwargs.pop("data", SAMPLE), **kwargs
    )


async def cat_id(entry: MockConfigEntry, name: str) -> int:
    return next(c["id"] for c in await entry.runtime_data.db.run(cats.list_categories) if c["name"] == name)


async def refresh(hass: HomeAssistant, entry: MockConfigEntry) -> None:
    await entry.runtime_data.coordinator.async_refresh()
    await hass.async_block_till_done()


# --- Auswahl-Logik ------------------------------------------------------------------------


def test_period_id() -> None:
    assert period_id(date(2026, 11, 24), "daily") == "2026-11-24"
    assert period_id(date(2026, 11, 24), "weekly") == "2026-W48"
    assert period_id(date(2027, 1, 1), "weekly") == "2026-W53"


def test_weight_prefers_good_and_long_not_cooked() -> None:
    today = date(2026, 11, 24)
    good = {"avg_stars": 5, "last_cooked": "2026-11-20T18:00:00+00:00"}
    bad = {"avg_stars": 1, "last_cooked": "2026-11-20T18:00:00+00:00"}
    old = {"avg_stars": 3, "last_cooked": "2025-11-01T18:00:00+00:00"}
    fresh = {"avg_stars": 3, "last_cooked": "2026-11-23T18:00:00+00:00"}
    assert weight(good, today, 2, 1) > weight(bad, today, 2, 1)
    assert weight(old, today, 2, 1) > weight(fresh, today, 2, 1)
    # Gewichtung 0 → egal
    assert weight(good, today, 0, 0) == weight(bad, today, 0, 0) == 1


def test_pick_is_deterministic_and_weighted() -> None:
    today = date(2026, 11, 24)
    candidates = [{"id": i, "avg_stars": 5 if i == 1 else 1, "last_cooked": None} for i in range(1, 6)]
    first = pick(candidates, seed="2026-11-24:daily", today=today, rating_weight=2, recency_weight=1)
    again = pick(list(reversed(candidates)), seed="2026-11-24:daily", today=today, rating_weight=2, recency_weight=1)
    assert first == again
    hits = sum(
        pick(candidates, seed=f"s{n}", today=today, rating_weight=4, recency_weight=0)["id"] == 1 for n in range(200)
    )
    assert hits > 150  # 5-Sterne-Rezept dominiert deutlich
    assert pick([], seed="x", today=today, rating_weight=1, recency_weight=1) is None


# --- Sensoren --------------------------------------------------------------------------------


async def test_count_sensor(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    kuchen = await cat_id(rb_entry, "Kuchen")
    torten = await cat_id(rb_entry, "Torten")
    await add_recipe(rb_entry, "A", category_ids=[kuchen, torten])
    await add_recipe(rb_entry, "B", category_ids=[kuchen])
    await add_recipe(rb_entry, "C")
    await refresh(hass, rb_entry)
    state = hass.states.get("sensor.rezeptbuch_anzahl_rezepte")
    assert state.state == "3"
    assert state.attributes["kategorien"] == {"Kochen": 0, "Backen": 2, "Getränke": 0}
    assert state.attributes["ohne_kategorie"] == 1
    assert state.attributes["friendly_name"] == "Rezeptbuch Anzahl Rezepte" or state.attributes[
        "friendly_name"
    ].startswith("Rezeptbuch")


async def test_daily_recipe_stable_within_day(
    hass: HomeAssistant, rb_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    freezer.move_to("2026-11-24 12:00:00+01:00")
    for n in range(8):
        await add_recipe(rb_entry, f"Rezept {n}")
    await refresh(hass, rb_entry)
    state = hass.states.get("sensor.rezeptbuch_rezept_des_tages")
    first = state.attributes["recipe_id"]
    assert state.state == state.attributes["title"]
    assert {"image_url", "prep_time", "cook_time", "total_time", "avg_stars"} <= set(state.attributes)

    # neue Rezepte am selben Tag ändern die Auswahl nicht
    for n in range(8, 20):
        await add_recipe(rb_entry, f"Rezept {n}")
    await refresh(hass, rb_entry)
    assert hass.states.get("sensor.rezeptbuch_rezept_des_tages").attributes["recipe_id"] == first

    # an mehreren Folgetagen wechselt sie (mindestens einmal)
    seen = {first}
    for day in range(1, 6):
        freezer.move_to(f"2026-11-{24 + day} 12:00:00+01:00")
        await refresh(hass, rb_entry)
        seen.add(hass.states.get("sensor.rezeptbuch_rezept_des_tages").attributes["recipe_id"])
    assert len(seen) > 1


async def test_daily_recipe_empty(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    state = hass.states.get("sensor.rezeptbuch_rezept_des_tages")
    assert state.state == "unknown"
    assert state.attributes.get("recipe_id") is None


async def test_midnight_triggers_refresh(
    hass: HomeAssistant, rb_entry: MockConfigEntry, freezer: FrozenDateTimeFactory
) -> None:
    coordinator = rb_entry.runtime_data.coordinator
    freezer.move_to(dt_util.now().replace(hour=23, minute=59, second=50))
    with patch.object(coordinator, "async_request_refresh", AsyncMock()) as refresh_mock:
        freezer.tick(timedelta(seconds=20))
        async_fire_time_changed(hass)
        await hass.async_block_till_done()
    assert refresh_mock.await_count == 1


@pytest.fixture
def entry_options() -> dict[str, Any]:
    return {}


async def test_daily_category_filter_and_ideas(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    backen = await cat_id(rb_entry, "Backen")
    kuchen = await cat_id(rb_entry, "Kuchen")
    cocktails = await cat_id(rb_entry, "Cocktails")
    cake = await add_recipe(rb_entry, "Kuchen", category_ids=[kuchen])
    drink = await add_recipe(rb_entry, "Mojito", category_ids=[cocktails])
    hass.config_entries.async_update_entry(
        rb_entry,
        options={
            CONF_DAILY_CATEGORY_IDS: [backen],
            CONF_IDEA_SENSORS: [{"id": "x1", "name": "Drink der Woche", "category_id": cocktails, "period": "weekly"}],
        },
    )
    await hass.async_block_till_done()  # Reload durch Update-Listener
    daily = hass.states.get("sensor.rezeptbuch_rezept_des_tages")
    assert daily.attributes["recipe_id"] == cake  # Unterkategorie zählt mit
    idea = hass.states.get("sensor.rezeptbuch_idee_drink_der_woche")
    assert idea.state == "Mojito" and idea.attributes["recipe_id"] == drink
    assert idea.attributes["period"] == "weekly"


async def test_ratings_influence_attributes(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry, "Einzig")
    await rb_entry.runtime_data.db.run(ratings.add_cook_log, rid, stars=4.5)
    await refresh(hass, rb_entry)
    state = hass.states.get("sensor.rezeptbuch_rezept_des_tages")
    assert state.attributes["avg_stars"] == 4.5 and state.attributes["cooked_count"] == 1


# --- Einkaufsliste ------------------------------------------------------------------------------


async def _items(hass: HomeAssistant) -> list[dict[str, Any]]:
    result = await hass.services.async_call(
        "todo",
        "get_items",
        {},
        target={"entity_id": "todo.rezeptbuch_einkaufsliste"},
        blocking=True,
        return_response=True,
    )
    return result["todo.rezeptbuch_einkaufsliste"]["items"]


async def test_add_recipe_to_shopping_list_merges(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry, "Pizza")
    other = await add_recipe(
        rb_entry,
        "Brot",
        data={
            "servings": 1,
            "ingredients": [
                {"amount": 1, "unit": "kg", "name": "Mehl"},
                {"amount": 1, "unit": "TL", "name": "Zucker"},
                {"amount": 400, "unit": "g", "name": "Tomaten"},
                {"amount": 1, "unit": "Prise", "name": "Salz"},
            ],
        },
    )
    response = await hass.services.async_call(
        DOMAIN, "add_to_shopping_list", {"recipe_id": rid, "servings": 8}, blocking=True, return_response=True
    )
    assert response["items"] == ["1 kg Mehl", "4 EL Zucker", "2 Prisen Salz", "Pfeffer (etwas)", "2 Dosen Tomaten"]
    await hass.services.async_call(DOMAIN, "add_to_shopping_list", {"recipe_id": other}, blocking=True)
    await hass.async_block_till_done()
    items = {i["summary"]: i for i in await _items(hass)}
    assert "2 kg Mehl" in items  # 1 kg + 1 kg
    assert "13 TL Zucker" in items  # 4 EL (=12 TL) + 1 TL
    assert "2 Prisen Salz" in items  # Prise nicht weiter addiert
    assert "2 Dosen Tomaten" in items and "400 g Tomaten" in items  # verschiedene Dimensionen
    assert items["2 kg Mehl"]["description"] == "für: Pizza, Brot"
    assert hass.states.get("todo.rezeptbuch_einkaufsliste").state == str(len(items))


async def test_todo_entity_crud(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    entity = {"entity_id": "todo.rezeptbuch_einkaufsliste"}
    await hass.services.async_call("todo", "add_item", {"item": "200 g Butter"}, target=entity, blocking=True)
    await hass.services.async_call(
        "todo", "add_item", {"item": "Milch", "description": "fettarm"}, target=entity, blocking=True
    )
    items = await _items(hass)
    assert [i["summary"] for i in items] == ["200 g Butter", "Milch"]
    stored = await rb_entry.runtime_data.db.run(shopping.list_items)
    assert (stored[0]["amount"], stored[0]["unit"], stored[0]["name"]) == (200, "g", "Butter")

    await hass.services.async_call(
        "todo", "update_item", {"item": "Milch", "status": "completed"}, target=entity, blocking=True
    )
    await hass.services.async_call(
        "todo", "update_item", {"item": "200 g Butter", "rename": "250 g Butter"}, target=entity, blocking=True
    )
    items = await _items(hass)
    assert {i["summary"]: i["status"] for i in items} == {"250 g Butter": "needs_action", "Milch": "completed"}
    assert hass.states.get("todo.rezeptbuch_einkaufsliste").state == "1"

    await hass.services.async_call("todo", "remove_completed_items", {}, target=entity, blocking=True)
    assert [i["summary"] for i in await _items(hass)] == ["250 g Butter"]
    await hass.services.async_call("todo", "remove_item", {"item": ["250 g Butter"]}, target=entity, blocking=True)
    assert await _items(hass) == []


async def test_add_to_external_todo_list(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    rid = await add_recipe(rb_entry, "Pizza")
    hass.states.async_set("todo.bring", "0")
    calls: list[dict] = []

    async def _fake_add_item(call_: ServiceCall) -> None:
        calls.append(dict(call_.data))

    # Ersatz für die todo-Aktion (eine echte zweite Liste brauchen wir nicht)
    hass.services.async_register("todo", "add_item", _fake_add_item)
    response = await hass.services.async_call(
        DOMAIN,
        "add_to_shopping_list",
        {"recipe_id": rid, "todo_entity": "todo.bring"},
        blocking=True,
        return_response=True,
    )
    assert response["todo_entity"] == "todo.bring"
    assert [c["item"] for c in calls] == [
        "500 g Mehl",
        "2 EL Zucker",
        "1 Prise Salz",
        "Pfeffer (etwas)",
        "1 Dose Tomaten",
    ]
    assert all(c["entity_id"] in ("todo.bring", ["todo.bring"]) for c in calls), calls
    assert all(c["description"] == "für: Pizza" for c in calls)
    assert await rb_entry.runtime_data.db.run(shopping.list_items) == []


# --- Diagnose ------------------------------------------------------------------------------------


async def test_diagnostics_without_recipe_content(hass: HomeAssistant, rb_entry: MockConfigEntry) -> None:
    await add_recipe(rb_entry, "Geheimes Familienrezept", tags=["Oma"])
    hass.config_entries.async_update_entry(
        rb_entry, options={CONF_IDEA_SENSORS: [{"id": "a", "name": "Omas Ideen", "category_id": 1, "period": "daily"}]}
    )
    await hass.async_block_till_done()
    diag = await async_get_config_entry_diagnostics(hass, rb_entry)
    text = json.dumps(diag, ensure_ascii=False)
    for secret in ("Geheimes Familienrezept", "Oma", "Mehl", "Omas Ideen"):
        assert secret not in text
    assert diag["database"]["schema_version"] == diag["database"]["schema_version_expected"] == 2
    assert diag["database"]["counts"]["recipes"] == 1
    assert diag["database"]["counts"]["recipes_by_source"] == {"manual": 1}
    assert diag["entry"]["options"]["idea_sensors"] == [{"period": "daily"}]
    assert diag["files"]["db_bytes"] > 0
