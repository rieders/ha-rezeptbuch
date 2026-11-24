"""Sensoren: Anzahl Rezepte, Rezept des Tages, Ideen-Sensoren."""

from __future__ import annotations

from typing import Any

from homeassistant.components.sensor import SensorEntity, SensorStateClass
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddConfigEntryEntitiesCallback
from homeassistant.helpers.update_coordinator import CoordinatorEntity
from homeassistant.util import slugify

from .const import CONF_IDEA_SENSORS, DOMAIN, IDEA_ID, IDEA_NAME, IDEA_PERIOD, PERIOD_DAILY
from .coordinator import DAILY_KEY, RezeptbuchCoordinator
from .entity import device_info
from .runtime import RezeptbuchConfigEntry

PARALLEL_UPDATES = 0


async def async_setup_entry(
    hass: HomeAssistant, entry: RezeptbuchConfigEntry, async_add_entities: AddConfigEntryEntitiesCallback
) -> None:
    """Sensoren anlegen."""
    coordinator = entry.runtime_data.coordinator
    assert coordinator is not None
    entities: list[SensorEntity] = [
        RecipeCountSensor(coordinator, entry),
        PickSensor(coordinator, entry, DAILY_KEY, "rezept_des_tages", translation_key="daily_recipe"),
    ]
    for idea in entry.options.get(CONF_IDEA_SENSORS) or []:
        entities.append(
            PickSensor(
                coordinator,
                entry,
                f"idea_{idea[IDEA_ID]}",
                f"idee_{slugify(idea[IDEA_NAME]) or idea[IDEA_ID]}",
                name=idea[IDEA_NAME],
                period=idea.get(IDEA_PERIOD, PERIOD_DAILY),
            )
        )
    async_add_entities(entities)


class _Base(CoordinatorEntity[RezeptbuchCoordinator], SensorEntity):
    _attr_has_entity_name = True

    def __init__(
        self, coordinator: RezeptbuchCoordinator, entry: RezeptbuchConfigEntry, key: str, object_id: str
    ) -> None:
        super().__init__(coordinator)
        self._attr_unique_id = f"{entry.entry_id}_{key}"
        self._attr_device_info = device_info(entry)
        self.entity_id = f"sensor.{DOMAIN}_{object_id}"


class RecipeCountSensor(_Base):
    """Anzahl Rezepte; Attribute: Anzahl je Hauptkategorie."""

    _attr_translation_key = "recipe_count"
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_icon = "mdi:book-open-page-variant"
    _attr_native_unit_of_measurement = "Rezepte"

    def __init__(self, coordinator: RezeptbuchCoordinator, entry: RezeptbuchConfigEntry) -> None:
        """Initialisieren."""
        super().__init__(coordinator, entry, "recipe_count", "anzahl_rezepte")

    @property
    def native_value(self) -> int:
        """Gesamtzahl."""
        return self.coordinator.data["total"]

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Anzahl je Hauptkategorie (inkl. Unterkategorien)."""
        return {
            "kategorien": dict(self.coordinator.data["by_root"]),
            "ohne_kategorie": self.coordinator.data["uncategorized"],
        }


class PickSensor(_Base):
    """Rezept des Tages bzw. Ideen-Sensor; Zustand = Rezepttitel."""

    _attr_icon = "mdi:chef-hat"

    def __init__(
        self,
        coordinator: RezeptbuchCoordinator,
        entry: RezeptbuchConfigEntry,
        key: str,
        object_id: str,
        *,
        translation_key: str | None = None,
        name: str | None = None,
        period: str = PERIOD_DAILY,
    ) -> None:
        """Initialisieren."""
        super().__init__(coordinator, entry, key, object_id)
        self._key = key
        self._period = period
        if translation_key:
            self._attr_translation_key = translation_key
        else:
            self._attr_name = name

    @property
    def _pick(self) -> dict[str, Any] | None:
        return self.coordinator.data["picks"].get(self._key)

    @property
    def native_value(self) -> str | None:
        """Titel des ausgewählten Rezepts."""
        pick = self._pick
        return pick["title"][:255] if pick else None

    @property
    def extra_state_attributes(self) -> dict[str, Any]:
        """Rezept-ID, Bild, Zeiten, Bewertung."""
        return {**(self._pick or {}), "period": self._period}
