"""Fachliche Fehler der Integration.

Jeder Fehler hat einen `translation_key` (siehe translations/*.json →
"exceptions"), damit Services/WebSocket verständliche Meldungen liefern.
"""

from __future__ import annotations

from typing import Any


class RezeptbuchError(Exception):
    """Basisklasse."""

    translation_key = "unknown_error"

    def __init__(self, message: str, **placeholders: Any) -> None:
        """Mit deutscher Meldung und Platzhaltern für die Übersetzung."""
        super().__init__(message)
        self.placeholders = {k: str(v) for k, v in placeholders.items()}


class InvalidUrl(RezeptbuchError):
    """URL ungültig oder nicht erlaubt."""

    translation_key = "invalid_url"


class BlockedAddress(RezeptbuchError):
    """Ziel-Adresse ist privat/lokal (SSRF-Schutz)."""

    translation_key = "blocked_address"


class FetchFailed(RezeptbuchError):
    """Seite nicht erreichbar (Timeout, HTTP-Fehler, zu groß …)."""

    translation_key = "fetch_failed"


class ResponseTooLarge(FetchFailed):
    """Antwort größer als erlaubt."""

    translation_key = "response_too_large"


class NoRecipeFound(RezeptbuchError):
    """Auf der Seite wurde kein Rezept gefunden."""

    translation_key = "no_recipe_found"


class InvalidImage(RezeptbuchError):
    """Datei ist kein unterstütztes Bild."""

    translation_key = "invalid_image"


class DraftNotFound(RezeptbuchError):
    """Import-Entwurf existiert nicht (mehr)."""

    translation_key = "draft_not_found"


class DuplicateRecipe(RezeptbuchError):
    """Rezept mit derselben Quelle existiert bereits."""

    translation_key = "duplicate_recipe"

    def __init__(self, recipe_id: int, title: str) -> None:
        """Mit ID und Titel des vorhandenen Rezepts."""
        super().__init__(
            f"Dieses Rezept ist bereits vorhanden: „{title}“ (ID {recipe_id})",
            recipe_id=recipe_id,
            title=title,
        )
        self.recipe_id = recipe_id
        self.title = title


class NoAiTaskEntity(RezeptbuchError):
    """Keine (eindeutige) ai_task-Entität verfügbar."""

    translation_key = "no_ai_task_entity"


class AiTaskEntityNotFound(RezeptbuchError):
    """Die konfigurierte ai_task-Entität existiert nicht (mehr)."""

    translation_key = "ai_task_entity_not_found"


class AiTaskFailed(RezeptbuchError):
    """Die KI-Auswertung ist fehlgeschlagen."""

    translation_key = "ai_task_failed"


class NoPhotos(RezeptbuchError):
    """Keine Fotos übergeben."""

    translation_key = "no_photos"
