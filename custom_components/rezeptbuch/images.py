"""Bilder prüfen, verkleinern, speichern und herunterladen."""

from __future__ import annotations

from io import BytesIO
import logging

from homeassistant.core import HomeAssistant
from PIL import Image, ImageOps, UnidentifiedImageError

from .errors import InvalidImage
from .net import async_safe_get
from .storage import Storage

_LOGGER = logging.getLogger(__name__)

ALLOWED_FORMATS = {"JPEG": "jpg", "PNG": "png", "WEBP": "webp", "GIF": "gif"}
MAX_IMAGE_BYTES = 15 * 1024 * 1024
MAX_PIXELS = 50_000_000  # Schutz vor "Decompression Bombs"
MAX_DIMENSION = 2400  # längere Kante, größere Bilder werden verkleinert
JPEG_QUALITY = 85


def process_image(data: bytes) -> tuple[bytes, str]:
    """Bild prüfen und ggf. drehen/verkleinern. Blockierend (Executor).

    Gibt (Bytes, Dateiendung) zurück. Unveränderte Bilder behalten ihre Bytes.
    """
    if not data:
        raise InvalidImage("Leere Bilddatei")
    if len(data) > MAX_IMAGE_BYTES:
        raise InvalidImage("Bild ist zu groß")
    try:
        with Image.open(BytesIO(data)) as probe:
            fmt = probe.format or ""
            width, height = probe.size
            probe.verify()
    except (UnidentifiedImageError, OSError, SyntaxError, Image.DecompressionBombError) as err:
        raise InvalidImage("Datei ist kein gültiges Bild") from err
    if fmt not in ALLOWED_FORMATS:
        raise InvalidImage(f"Bildformat {fmt or 'unbekannt'} wird nicht unterstützt")
    if width * height > MAX_PIXELS:
        raise InvalidImage("Bild hat zu viele Pixel")

    with Image.open(BytesIO(data)) as img:
        orientation = img.getexif().get(0x0112, 1) if fmt in ("JPEG", "WEBP") else 1
        needs_resize = max(width, height) > MAX_DIMENSION
        if fmt == "GIF" or (not needs_resize and orientation == 1):
            return data, ALLOWED_FORMATS[fmt]
        img = ImageOps.exif_transpose(img)
        if needs_resize:
            img.thumbnail((MAX_DIMENSION, MAX_DIMENSION), Image.Resampling.LANCZOS)
        out = BytesIO()
        if fmt == "PNG" or img.mode in ("RGBA", "LA", "P"):
            img.save(out, format="PNG", optimize=True)
            return out.getvalue(), "png"
        img.convert("RGB").save(out, format="JPEG", quality=JPEG_QUALITY, optimize=True)
        return out.getvalue(), "jpg"


async def async_store_image(hass: HomeAssistant, storage: Storage, data: bytes) -> str:
    """Bild prüfen und speichern; gibt den relativen Pfad zurück."""

    def _store() -> str:
        processed, ext = process_image(data)
        return storage.write_image(processed, ext)

    return await hass.async_add_executor_job(_store)


async def async_download_image(hass: HomeAssistant, storage: Storage, url: str) -> str:
    """Bild (mit SSRF-Schutz) herunterladen, prüfen und lokal speichern."""
    result = await async_safe_get(
        hass, url, max_bytes=MAX_IMAGE_BYTES, accept="image/avif,image/webp,image/png,image/jpeg,image/*;q=0.8"
    )
    if result.content_type and not result.content_type.startswith(("image/", "application/octet-stream")):
        raise InvalidImage(f"Kein Bild (Content-Type {result.content_type})")
    return await async_store_image(hass, storage, result.body)


async def async_delete_images(hass: HomeAssistant, storage: Storage, paths: list[str]) -> None:
    """Mehrere Bilddateien löschen."""

    def _delete() -> None:
        for path in paths:
            storage.delete_image(path)

    if paths:
        await hass.async_add_executor_job(_delete)
