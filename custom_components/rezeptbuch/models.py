"""Datenmodelle für Rezeptversionen (Zutaten, Schritte, Zeiten)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
import json
from typing import Any

from .units import normalize_unit


class ValidationError(ValueError):
    """Ungültige Eingabedaten."""


def utcnow_iso() -> str:
    """Aktueller Zeitpunkt (UTC) als ISO-String."""
    return datetime.now(UTC).isoformat(timespec="seconds")


def _opt_float(value: Any, field_name: str) -> float | None:
    if value is None or value == "":
        return None
    try:
        result = float(str(value).replace(",", "."))
    except (TypeError, ValueError) as err:
        raise ValidationError(f"{field_name}: keine Zahl ({value!r})") from err
    if result < 0:
        raise ValidationError(f"{field_name}: darf nicht negativ sein")
    return result


def _opt_int(value: Any, field_name: str) -> int | None:
    result = _opt_float(value, field_name)
    return None if result is None else round(result)


def _opt_str(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


@dataclass
class Ingredient:
    """Eine Zutat."""

    name: str
    amount: float | None = None
    amount_max: float | None = None
    unit: str | None = None
    note: str | None = None
    group: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Ingredient:
        """Aus einem (evtl. unvollständigen) Dict erzeugen."""
        if not isinstance(data, dict):
            raise ValidationError("Zutat muss ein Objekt sein")
        name = _opt_str(data.get("name"))
        if not name:
            raise ValidationError("Zutat ohne Namen")
        amount = _opt_float(data.get("amount"), "Menge")
        amount_max = _opt_float(data.get("amount_max"), "Menge (max)")
        if amount is None or (amount_max is not None and amount_max <= amount):
            amount_max = None
        return cls(
            name=name,
            amount=amount,
            amount_max=amount_max,
            unit=normalize_unit(_opt_str(data.get("unit"))),
            note=_opt_str(data.get("note")),
            group=_opt_str(data.get("group")),
        )

    def to_dict(self) -> dict[str, Any]:
        """Als JSON-fähiges Dict."""
        return {
            "amount": self.amount,
            "amount_max": self.amount_max,
            "unit": self.unit,
            "name": self.name,
            "note": self.note,
            "group": self.group,
        }


@dataclass
class Step:
    """Ein Zubereitungsschritt."""

    text: str
    timer_seconds: int | None = None
    group: str | None = None

    @classmethod
    def from_dict(cls, data: dict[str, Any] | str) -> Step:
        """Aus Dict oder reinem Text erzeugen."""
        if isinstance(data, str):
            data = {"text": data}
        if not isinstance(data, dict):
            raise ValidationError("Schritt muss ein Objekt sein")
        text = _opt_str(data.get("text"))
        if not text:
            raise ValidationError("Schritt ohne Text")
        timer = _opt_int(data.get("timer_seconds"), "Timer")
        return cls(text=text, timer_seconds=timer or None, group=_opt_str(data.get("group")))

    def to_dict(self) -> dict[str, Any]:
        """Als JSON-fähiges Dict."""
        return {"text": self.text, "timer_seconds": self.timer_seconds, "group": self.group}


@dataclass
class VersionData:
    """Inhalt einer Rezeptversion (wird als JSON gespeichert)."""

    servings: float | None = None
    servings_unit: str | None = None
    prep_time: int | None = None  # Minuten
    cook_time: int | None = None
    total_time: int | None = None
    ingredients: list[Ingredient] = field(default_factory=list)
    steps: list[Step] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any] | None) -> VersionData:
        """Aus Dict erzeugen und validieren."""
        data = data or {}
        if not isinstance(data, dict):
            raise ValidationError("Versionsdaten müssen ein Objekt sein")
        servings = _opt_float(data.get("servings"), "Portionen")
        if servings == 0:
            servings = None
        prep = _opt_int(data.get("prep_time"), "Vorbereitungszeit")
        cook = _opt_int(data.get("cook_time"), "Koch-/Backzeit")
        total = _opt_int(data.get("total_time"), "Gesamtzeit")
        if total is None and (prep or cook):
            total = (prep or 0) + (cook or 0)
        return cls(
            servings=servings,
            servings_unit=_opt_str(data.get("servings_unit")),
            prep_time=prep,
            cook_time=cook,
            total_time=total,
            ingredients=[Ingredient.from_dict(i) for i in data.get("ingredients") or []],
            steps=[Step.from_dict(s) for s in data.get("steps") or []],
        )

    @classmethod
    def from_json(cls, raw: str | None) -> VersionData:
        """Aus JSON-String."""
        return cls.from_dict(json.loads(raw) if raw else {})

    def to_dict(self) -> dict[str, Any]:
        """Als JSON-fähiges Dict."""
        return {
            "servings": self.servings,
            "servings_unit": self.servings_unit,
            "prep_time": self.prep_time,
            "cook_time": self.cook_time,
            "total_time": self.total_time,
            "ingredients": [i.to_dict() for i in self.ingredients],
            "steps": [s.to_dict() for s in self.steps],
        }

    def to_json(self) -> str:
        """Als kompakter JSON-String."""
        return json.dumps(self.to_dict(), ensure_ascii=False, separators=(",", ":"))


def validate_stars(stars: Any) -> float | None:
    """Sterne prüfen: 0,5 … 5,0 in halben Schritten (None erlaubt)."""
    if stars is None or stars == "":
        return None
    try:
        value = float(stars)
    except (TypeError, ValueError) as err:
        raise ValidationError("Sterne müssen eine Zahl sein") from err
    if not 0.5 <= value <= 5.0 or value * 2 != int(value * 2):
        raise ValidationError("Sterne müssen zwischen 0,5 und 5 in halben Schritten liegen")
    return value
