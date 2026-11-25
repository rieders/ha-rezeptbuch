"""Aufbereitung von DB-Daten für Panel/WebSocket: signierte Bild-URLs, Benutzernamen, Zeilen."""

from __future__ import annotations

from datetime import timedelta
from typing import Any

from homeassistant.components.http.auth import async_sign_path
from homeassistant.core import HomeAssistant

from .const import IMAGE_URL_PREFIX, SYSTEM_USER_ID, SYSTEM_USER_NAME
from .ingredient_parser import parse_ingredient_lines
from .models import Ingredient, Step, VersionData
from .scaling import format_ingredient, format_quantity
from .timers import detect_timer_seconds

SIGNED_URL_VALIDITY = timedelta(hours=24)


class Signer:
    """Signiert Bildpfade mit HAs eigenem async_sign_path (an die Sitzung gebunden)."""

    def __init__(self, hass: HomeAssistant, refresh_token_id: str | None) -> None:
        """Initialisieren."""
        self._hass = hass
        self._refresh_token_id = refresh_token_id

    def url(self, rel_path: str | None) -> str | None:
        """Signierte URL für einen relativen Bildpfad."""
        if not rel_path:
            return None
        return async_sign_path(
            self._hass,
            f"{IMAGE_URL_PREFIX}{rel_path}",
            SIGNED_URL_VALIDITY,
            refresh_token_id=self._refresh_token_id,
        )


async def async_user_names(hass: HomeAssistant, user_ids: set[str | None]) -> dict[str, str]:
    """user_id → Anzeigename ("System" für Automationen)."""
    names: dict[str, str] = {}
    for user_id in user_ids:
        if not user_id or user_id == SYSTEM_USER_ID:
            names[user_id or SYSTEM_USER_ID] = SYSTEM_USER_NAME
            continue
        user = await hass.auth.async_get_user(user_id)
        names[user_id] = user.name if user and user.name else user_id[:8]
    return names


def ingredient_view(ing: Ingredient) -> dict[str, Any]:
    """Zutat inkl. fertiger Anzeige-Texte."""
    return {
        **ing.to_dict(),
        "quantity": format_quantity(ing.amount, ing.unit, ing.amount_max),
        "text": format_ingredient(ing),
    }


def version_view(data: VersionData) -> dict[str, Any]:
    """Versionsdaten für die Anzeige."""
    return {
        **data.to_dict(),
        "ingredients": [ingredient_view(i) for i in data.ingredients],
    }


def ingredient_lines(data: VersionData) -> list[str]:
    """Zutaten als bearbeitbare Textzeilen, Gruppen als "Gruppe:"-Zeilen."""
    lines: list[str] = []
    group: str | None = None
    for ing in data.ingredients:
        if ing.group != group:
            group = ing.group
            if group:
                lines.append(f"{group}:")
        lines.append(format_ingredient(ing))
    return lines


def apply_lines(data: VersionData, ingredient_text: list[str] | None, step_text: list[str] | None) -> VersionData:
    """Bearbeitete Textzeilen wieder durch Parser und Timer-Erkennung schicken."""
    if ingredient_text is not None:
        data.ingredients = parse_ingredient_lines(ingredient_text)
    if step_text is not None:
        data.steps = [
            Step(text=t.strip(), timer_seconds=detect_timer_seconds(t.strip())) for t in step_text if t.strip()
        ]
    return data
