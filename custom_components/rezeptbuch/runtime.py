"""Laufzeitdaten der geladenen Integration (ConfigEntry.runtime_data)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant

from .const import (
    CONF_AI_TASK_ENTITY,
    CONF_ALLOW_PRIVATE_NETWORKS,
    CONF_DEFAULT_SERVINGS,
    DEFAULT_ALLOW_PRIVATE_NETWORKS,
    DEFAULT_SERVINGS,
    DOMAIN,
)
from .db import Database
from .storage import Storage

if TYPE_CHECKING:
    from .coordinator import RezeptbuchCoordinator


@dataclass
class RezeptbuchRuntime:
    """Was die Integration zur Laufzeit braucht."""

    db: Database
    storage: Storage
    options: dict[str, Any] = field(default_factory=dict)
    coordinator: RezeptbuchCoordinator | None = None

    @property
    def ai_task_entity(self) -> str | None:
        """Gewählte ai_task-Entität (None = HA-Standard)."""
        return self.options.get(CONF_AI_TASK_ENTITY) or None

    @property
    def allow_private_networks(self) -> bool:
        """Option „Private Netzwerkadressen erlauben“."""
        return bool(self.options.get(CONF_ALLOW_PRIVATE_NETWORKS, DEFAULT_ALLOW_PRIVATE_NETWORKS))

    @property
    def default_servings(self) -> int:
        """Standard-Portionen für neue Rezepte."""
        return int(self.options.get(CONF_DEFAULT_SERVINGS, DEFAULT_SERVINGS))


type RezeptbuchConfigEntry = ConfigEntry[RezeptbuchRuntime]


def async_get_runtime(hass: HomeAssistant) -> RezeptbuchRuntime | None:
    """Runtime des (einzigen) geladenen Rezeptbuch-Eintrags."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime = getattr(entry, "runtime_data", None)
        if isinstance(runtime, RezeptbuchRuntime):
            return runtime
    return None
