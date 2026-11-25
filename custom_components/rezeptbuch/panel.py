"""Seitenleisten-Panel „Rezeptbuch“ (panel_custom) und statische Auslieferung des Bundles."""

from __future__ import annotations

import hashlib
from pathlib import Path

from homeassistant.components import frontend, panel_custom
from homeassistant.components.http import StaticPathConfig
from homeassistant.core import HomeAssistant, callback

from .const import DOMAIN, NAME

PANEL_URL_PATH = DOMAIN
PANEL_ICON = "mdi:chef-hat"
WEBCOMPONENT = "rezeptbuch-panel"
STATIC_URL = f"/{DOMAIN}_static"
FRONTEND_DIR = Path(__file__).parent / "frontend"
BUNDLE_NAME = "rezeptbuch-panel.js"
_DATA_STATIC = f"{DOMAIN}_static_registered"
_DATA_PANEL = f"{DOMAIN}_panel_registered"


def bundle_version() -> str:
    """Kurzer Hash des Bundles (Cache-Busting). Blockierend → Executor."""
    path = FRONTEND_DIR / BUNDLE_NAME
    if not path.is_file():
        return "missing"
    return hashlib.sha256(path.read_bytes()).hexdigest()[:12]


async def async_register_static(hass: HomeAssistant) -> None:
    """Frontend-Ordner einmal pro HA-Lauf statisch bereitstellen (kein Abmelde-API in HA)."""
    if hass.data.get(_DATA_STATIC):
        return
    await hass.http.async_register_static_paths([StaticPathConfig(STATIC_URL, str(FRONTEND_DIR), cache_headers=True)])
    hass.data[_DATA_STATIC] = True


async def async_register_panel(hass: HomeAssistant) -> bool:
    """Panel in der Seitenleiste anmelden (für alle Benutzer sichtbar)."""
    if "frontend" not in hass.config.components:
        return False
    version = await hass.async_add_executor_job(bundle_version)
    await panel_custom.async_register_panel(
        hass,
        frontend_url_path=PANEL_URL_PATH,
        webcomponent_name=WEBCOMPONENT,
        sidebar_title=NAME,
        sidebar_icon=PANEL_ICON,
        module_url=f"{STATIC_URL}/{BUNDLE_NAME}?v={version}",
        embed_iframe=False,
        require_admin=False,
        config={"version": version},
    )
    hass.data[_DATA_PANEL] = True
    return True


@callback
def async_unregister_panel(hass: HomeAssistant) -> None:
    """Panel beim Entladen wieder entfernen."""
    if hass.data.pop(_DATA_PANEL, False):
        frontend.async_remove_panel(hass, PANEL_URL_PATH)
