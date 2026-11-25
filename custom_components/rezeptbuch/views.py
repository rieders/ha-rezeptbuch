"""Authentifizierte HTTP-Views: Bilder ausliefern, Fotos hochladen.

Bilder: GET /api/rezeptbuch/image/<pfad>
  requires_auth=True – das Panel bekommt per WebSocket mit HAs eigenem
  async_sign_path signierte URLs (authSig, 24 h gültig), weil <img> keinen
  Authorization-Header mitschicken kann.
Upload: POST /api/rezeptbuch/import/photo (multipart, Feld "photo", mehrfach,
  Reihenfolge = Seitenreihenfolge) → Foto-Import → Entwurf.
"""

from __future__ import annotations

from http import HTTPStatus
import logging
import mimetypes
from typing import Any

from aiohttp import BodyPartReader, web
from homeassistant.components.http import KEY_HASS, KEY_HASS_USER, HomeAssistantView
from homeassistant.components.http.const import KEY_HASS_REFRESH_TOKEN_ID
from homeassistant.core import HomeAssistant, callback

from .api_format import Signer
from .const import DOMAIN
from .errors import AiTaskFailed, FetchFailed, RezeptbuchError
from .images import MAX_IMAGE_BYTES
from .importer.photo import MAX_PHOTOS, async_import_photos
from .runtime import async_get_runtime

_LOGGER = logging.getLogger(__name__)

IMAGE_URL = f"/api/{DOMAIN}/image/{{path:.+}}"
UPLOAD_URL = f"/api/{DOMAIN}/import/photo"


def _error(status: HTTPStatus, code: str, message: str, placeholders: dict[str, str] | None = None) -> web.Response:
    return web.json_response({"code": code, "message": message, "placeholders": placeholders or {}}, status=status)


class RezeptbuchImageView(HomeAssistantView):
    """Liefert gespeicherte Rezeptbilder (nur angemeldet bzw. mit signierter URL)."""

    url = IMAGE_URL
    name = f"api:{DOMAIN}:image"
    requires_auth = True

    async def get(self, request: web.Request, path: str) -> web.StreamResponse:
        """Bild ausliefern."""
        hass: HomeAssistant = request.app[KEY_HASS]
        runtime = async_get_runtime(hass)
        if runtime is None:
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "not_loaded", "Rezeptbuch ist nicht geladen")
        try:
            file_path = runtime.storage.image_path(path)
        except ValueError:
            return _error(HTTPStatus.NOT_FOUND, "not_found", "Bild nicht gefunden")
        if not await hass.async_add_executor_job(file_path.is_file):
            return _error(HTTPStatus.NOT_FOUND, "not_found", "Bild nicht gefunden")
        content_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
        if not content_type.startswith("image/"):
            return _error(HTTPStatus.NOT_FOUND, "not_found", "Bild nicht gefunden")
        return web.FileResponse(
            file_path,
            headers={
                "Content-Type": content_type,
                "Cache-Control": "private, max-age=86400",
                "X-Content-Type-Options": "nosniff",
            },
        )


class RezeptbuchPhotoUploadView(HomeAssistantView):
    """Foto-Import aus dem Panel (Datei oder Kamera)."""

    url = UPLOAD_URL
    name = f"api:{DOMAIN}:import_photo"
    requires_auth = True

    async def post(self, request: web.Request) -> web.Response:
        """Fotos entgegennehmen und Entwurf erzeugen."""
        hass: HomeAssistant = request.app[KEY_HASS]
        runtime = async_get_runtime(hass)
        if runtime is None:
            return _error(HTTPStatus.SERVICE_UNAVAILABLE, "not_loaded", "Rezeptbuch ist nicht geladen")
        user = request[KEY_HASS_USER]
        photos: list[bytes] = []
        try:
            reader = await request.multipart()
            while (part := await reader.next()) is not None:
                if not isinstance(part, BodyPartReader) or part.name != "photo":
                    continue
                if len(photos) >= MAX_PHOTOS:
                    return _error(HTTPStatus.BAD_REQUEST, "no_photos", f"Höchstens {MAX_PHOTOS} Fotos")
                data = bytearray()
                while chunk := await part.read_chunk(64 * 1024):
                    data.extend(chunk)
                    if len(data) > MAX_IMAGE_BYTES:
                        return _error(HTTPStatus.REQUEST_ENTITY_TOO_LARGE, "invalid_image", "Foto ist zu groß")
                photos.append(bytes(data))
        except (ValueError, AssertionError) as err:
            return _error(HTTPStatus.BAD_REQUEST, "invalid_input", f"Ungültige Anfrage: {err}")

        try:
            result = await async_import_photos(
                hass,
                runtime.db,
                runtime.storage,
                photos,
                user_id=user.id,
                ai_task_entity=runtime.ai_task_entity,
            )
        except RezeptbuchError as err:
            status = HTTPStatus.BAD_GATEWAY if isinstance(err, (AiTaskFailed, FetchFailed)) else HTTPStatus.BAD_REQUEST
            return _error(status, err.translation_key, str(err), err.placeholders)

        from .websocket_api import _draft_view

        refresh_token_id = request.get(KEY_HASS_REFRESH_TOKEN_ID)
        payload: dict[str, Any] = {
            "status": "draft",
            "draft": _draft_view(result["draft"], Signer(hass, refresh_token_id)),
        }
        return web.json_response(payload)


@callback
def async_register_views(hass: HomeAssistant) -> None:
    """Views einmalig registrieren (HA kennt kein Abmelden; ohne Runtime → 503)."""
    hass.http.register_view(RezeptbuchImageView())
    hass.http.register_view(RezeptbuchPhotoUploadView())
