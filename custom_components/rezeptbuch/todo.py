"""todo.rezeptbuch_einkaufsliste – die eigene Einkaufsliste."""

from __future__ import annotations

from typing import Any

from homeassistant.components.todo import TodoItem, TodoItemStatus, TodoListEntity, TodoListEntityFeature
from homeassistant.core import HomeAssistant, callback
from homeassistant.helpers.dispatcher import async_dispatcher_connect
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback

from .const import DOMAIN, SIGNAL_SHOPPING_UPDATED
from .db import shopping
from .entity import device_info
from .runtime import RezeptbuchConfigEntry, RezeptbuchRuntime
from .shopping_list import parse_manual_item

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: RezeptbuchConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Einkaufsliste anlegen."""
    async_add_entities([ShoppingListEntity(entry)])


def _status(value: str) -> TodoItemStatus:
    return TodoItemStatus.COMPLETED if value == shopping.STATUS_DONE else TodoItemStatus.NEEDS_ACTION


def _db_status(status: TodoItemStatus | None) -> str:
    return shopping.STATUS_DONE if status == TodoItemStatus.COMPLETED else shopping.STATUS_OPEN


class ShoppingListEntity(TodoListEntity):
    """Einkaufsliste aus der Rezeptbuch-Datenbank."""

    _attr_has_entity_name = True
    _attr_translation_key = "shopping_list"
    _attr_icon = "mdi:cart"
    _attr_supported_features = (
        TodoListEntityFeature.CREATE_TODO_ITEM
        | TodoListEntityFeature.UPDATE_TODO_ITEM
        | TodoListEntityFeature.DELETE_TODO_ITEM
        | TodoListEntityFeature.MOVE_TODO_ITEM
        | TodoListEntityFeature.SET_DESCRIPTION_ON_ITEM
    )

    def __init__(self, entry: RezeptbuchConfigEntry) -> None:
        """Initialisieren."""
        self._runtime: RezeptbuchRuntime = entry.runtime_data
        self._attr_unique_id = f"{entry.entry_id}_shopping_list"
        self._attr_device_info = device_info(entry)
        self._attr_todo_items = []
        self.entity_id = f"todo.{DOMAIN}_einkaufsliste"

    async def async_added_to_hass(self) -> None:
        """Liste laden und auf Änderungen durch Aktionen hören."""
        self.async_on_remove(async_dispatcher_connect(self.hass, SIGNAL_SHOPPING_UPDATED, self._schedule_refresh))
        await self._async_refresh(write=False)

    @callback
    def _schedule_refresh(self) -> None:
        self.hass.async_create_task(self._async_refresh(), eager_start=True)

    async def _async_refresh(self, write: bool = True) -> None:
        items = await self._runtime.db.run(shopping.list_items)
        self._attr_todo_items = [
            TodoItem(summary=i["summary"], uid=i["uid"], status=_status(i["status"]), description=i["description"])
            for i in items
        ]
        if write:
            self.async_write_ha_state()

    async def async_create_todo_item(self, item: TodoItem) -> None:
        """Eintrag anlegen (Text wird für späteres Zusammenfassen zerlegt)."""
        await self._runtime.db.run(
            shopping.add_item,
            summary=item.summary or "",
            description=item.description,
            status=_db_status(item.status),
            **parse_manual_item(item.summary or ""),
        )
        await self._async_refresh()

    async def async_update_todo_item(self, item: TodoItem) -> None:
        """Eintrag ändern."""
        assert item.uid is not None
        fields: dict[str, Any] = {"status": _db_status(item.status), "description": item.description}
        if item.summary is not None:
            fields["summary"] = item.summary
            fields.update(parse_manual_item(item.summary))
        await self._runtime.db.run(shopping.update_item, item.uid, **fields)
        await self._async_refresh()

    async def async_delete_todo_items(self, uids: list[str]) -> None:
        """Einträge löschen."""
        await self._runtime.db.run(shopping.delete_items, uids)
        await self._async_refresh()

    async def async_move_todo_item(self, uid: str, previous_uid: str | None = None) -> None:
        """Eintrag verschieben."""
        await self._runtime.db.run(shopping.move_item, uid, previous_uid)
        await self._async_refresh()
