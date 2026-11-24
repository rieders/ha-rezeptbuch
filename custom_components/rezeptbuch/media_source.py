"""Media Source für Rezeptbuch-Bilder.

Wird vor allem für ai_task gebraucht: Anhänge werden als
"media-source://rezeptbuch/<relativer Bildpfad>" übergeben und von ai_task
über diese Quelle in eine lokale Datei (PlayMedia.path) aufgelöst.
"""

from __future__ import annotations

import mimetypes

from homeassistant.components.media_player import MediaClass
from homeassistant.components.media_source import (
    BrowseMediaSource,
    MediaSource,
    MediaSourceItem,
    PlayMedia,
    Unresolvable,
)
from homeassistant.core import HomeAssistant

from .const import DOMAIN, NAME
from .runtime import async_get_runtime

URI_PREFIX = f"media-source://{DOMAIN}/"


def media_source_uri(rel_path: str) -> str:
    """URI für einen gespeicherten Bildpfad."""
    return f"{URI_PREFIX}{rel_path}"


async def async_get_media_source(hass: HomeAssistant) -> MediaSource:
    """Plattform-Einstieg für media_source."""
    return RezeptbuchMediaSource(hass)


class RezeptbuchMediaSource(MediaSource):
    """Liefert gespeicherte Rezeptbilder als lokale Dateien."""

    name = NAME

    def __init__(self, hass: HomeAssistant) -> None:
        """Initialisieren."""
        super().__init__(DOMAIN)
        self.hass = hass

    async def async_resolve_media(self, item: MediaSourceItem) -> PlayMedia:
        """Relativen Bildpfad in eine lokale Datei auflösen."""
        runtime = async_get_runtime(self.hass)
        if runtime is None:
            raise Unresolvable("Rezeptbuch ist nicht geladen")
        try:
            path = runtime.storage.image_path(item.identifier)
        except ValueError as err:
            raise Unresolvable(f"Ungültiger Bildpfad: {item.identifier}") from err
        if not await self.hass.async_add_executor_job(path.is_file):
            raise Unresolvable(f"Bild nicht gefunden: {item.identifier}")
        mime_type = mimetypes.guess_type(path.name)[0] or "image/jpeg"
        return PlayMedia(f"/api/{DOMAIN}/image/{item.identifier}", mime_type, path=path)

    async def async_browse_media(self, item: MediaSourceItem) -> BrowseMediaSource:
        """Keine Mediathek-Ansicht – Bilder werden im Rezeptbuch-Panel verwaltet."""
        if item.identifier:
            raise Unresolvable("Durchsuchen wird nicht unterstützt")
        return BrowseMediaSource(
            domain=DOMAIN,
            identifier=None,
            media_class=MediaClass.DIRECTORY,
            media_content_type="",
            title=NAME,
            can_play=False,
            can_expand=False,
            children=[],
        )
