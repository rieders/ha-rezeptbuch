"""Laufzeitdaten der geladenen Integration (ConfigEntry.runtime_data)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from homeassistant.core import HomeAssistant

from .const import DOMAIN
from .db import Database
from .storage import Storage


@dataclass
class RezeptbuchRuntime:
    """Was die Integration zur Laufzeit braucht."""

    db: Database
    storage: Storage
    options: dict[str, Any] = field(default_factory=dict)


def async_get_runtime(hass: HomeAssistant) -> RezeptbuchRuntime | None:
    """Runtime des (einzigen) geladenen Rezeptbuch-Eintrags."""
    for entry in hass.config_entries.async_loaded_entries(DOMAIN):
        runtime = getattr(entry, "runtime_data", None)
        if isinstance(runtime, RezeptbuchRuntime):
            return runtime
    return None
