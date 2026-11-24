"""Speicherorte: Datenbank und Bilder unter <config>/rezeptbuch/.

In der Datenbank werden nur Pfade *relativ* zum Bilderverzeichnis gespeichert
(z. B. "ab/abcdef….jpg"), damit sich der Speicherort verschieben lässt.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import uuid

from .const import DB_FILENAME, IMAGES_DIRNAME


@dataclass(frozen=True)
class Storage:
    """Pfade der Integration (alles blockierend → im Executor benutzen)."""

    base_dir: Path

    @property
    def db_path(self) -> Path:
        """Pfad der SQLite-Datei."""
        return self.base_dir / DB_FILENAME

    @property
    def images_dir(self) -> Path:
        """Bilderverzeichnis."""
        return self.base_dir / IMAGES_DIRNAME

    def ensure_dirs(self) -> None:
        """Verzeichnisse anlegen."""
        self.images_dir.mkdir(parents=True, exist_ok=True)

    def image_path(self, rel_path: str) -> Path:
        """Absoluter Pfad zu einem gespeicherten Bild – ohne Ausbruch aus dem Ordner."""
        root = self.images_dir.resolve()
        path = (root / rel_path).resolve()
        if root not in path.parents:
            raise ValueError(f"Ungültiger Bildpfad: {rel_path}")
        return path

    def new_image_rel_path(self, ext: str) -> str:
        """Neuer, eindeutiger relativer Pfad (2-stelliger Unterordner)."""
        name = uuid.uuid4().hex
        return f"{name[:2]}/{name}.{ext.lstrip('.')}"

    def write_image(self, data: bytes, ext: str) -> str:
        """Bild schreiben, relativen Pfad zurückgeben."""
        rel = self.new_image_rel_path(ext)
        path = self.image_path(rel)
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        tmp.write_bytes(data)
        tmp.replace(path)
        return rel

    def delete_image(self, rel_path: str | None) -> bool:
        """Bild löschen (fehlende Dateien sind kein Fehler)."""
        if not rel_path:
            return False
        try:
            self.image_path(rel_path).unlink()
        except (FileNotFoundError, ValueError):
            return False
        return True
