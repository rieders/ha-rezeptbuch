"""Gemeinsame Basis für Rezeptbuch-Entitäten."""

from __future__ import annotations

from homeassistant.helpers.device_registry import DeviceEntryType, DeviceInfo

from .const import DOMAIN, NAME
from .runtime import RezeptbuchConfigEntry


def device_info(entry: RezeptbuchConfigEntry) -> DeviceInfo:
    """Ein „Dienst“-Gerät, an dem alle Entitäten hängen."""
    return DeviceInfo(
        identifiers={(DOMAIN, entry.entry_id)},
        name=NAME,
        manufacturer=NAME,
        entry_type=DeviceEntryType.SERVICE,
    )
