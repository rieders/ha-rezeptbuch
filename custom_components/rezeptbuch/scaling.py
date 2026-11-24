"""Portionen skalieren und Mengen lesbar formatieren."""

from __future__ import annotations

from dataclasses import replace

from .models import Ingredient, VersionData
from .units import get_unit, is_vague_note, unit_display

_FRACTIONS: tuple[tuple[float, str], ...] = (
    (0.125, "⅛"),
    (0.25, "¼"),
    (1 / 3, "⅓"),
    (0.5, "½"),
    (2 / 3, "⅔"),
    (0.75, "¾"),
)


def format_amount(value: float | None, *, fractions: bool = True) -> str:
    """Menge deutsch formatieren: 0.5 → ½, 1.5 → 1½, 2.25 → 2¼, 1.2 → 1,2."""
    if value is None:
        return ""
    if abs(value - round(value)) < 0.01:
        return str(round(value))
    whole = int(value)
    frac = value - whole
    if fractions:
        for f_val, f_str in _FRACTIONS:
            if abs(frac - f_val) < 0.02:
                return f"{whole}{f_str}" if whole else f_str
    text = f"{value:.2f}".rstrip("0").rstrip(".")
    return text.replace(".", ",")


def format_quantity(amount: float | None, unit: str | None, amount_max: float | None = None) -> str:
    """Menge + Einheit, z. B. "200 g", "2–3", "1 Prise"."""
    use_fractions = not (get_unit(unit) and get_unit(unit).dimension == "mass")  # type: ignore[union-attr]
    parts: list[str] = []
    if amount is not None:
        text = format_amount(amount, fractions=use_fractions)
        if amount_max is not None:
            text += "–" + format_amount(amount_max, fractions=use_fractions)
        parts.append(text)
    if unit:
        parts.append(unit_display(unit, amount_max if amount_max is not None else amount))
    return " ".join(parts)


def format_ingredient(ing: Ingredient) -> str:
    """Zutat als Zeile, z. B. "200 g Mehl (Type 405)" oder "etwas Pfeffer"."""
    qty = format_quantity(ing.amount, ing.unit, ing.amount_max)
    if not qty and is_vague_note(ing.note):
        return f"{ing.note} {ing.name}"
    text = f"{qty} {ing.name}".strip()
    if ing.note:
        text += f" ({ing.note})"
    return text


def _smart_round(value: float, unit: str | None) -> float:
    udef = get_unit(unit)
    if udef and udef.dimension and not udef.spoon:
        # Gewicht/Volumen: sinnvolle Rundung je Größenordnung
        if udef.canonical in ("g", "ml"):
            if value >= 100:
                return round(value / 5) * 5
            if value >= 10:
                return round(value)
            return round(value, 1)
        return round(value, 2)
    # Stück, Löffel usw.: auf Viertel runden (mind. ¼)
    return max(round(value * 4) / 4, 0.25)


def scale_ingredient(ing: Ingredient, factor: float) -> Ingredient:
    """Eine Zutat skalieren."""
    if ing.amount is None or factor == 1:
        return ing
    return replace(
        ing,
        amount=_smart_round(ing.amount * factor, ing.unit),
        amount_max=_smart_round(ing.amount_max * factor, ing.unit) if ing.amount_max is not None else None,
    )


def scale_version(data: VersionData, servings: float | None) -> VersionData:
    """Version auf eine Portionenzahl skalieren (Zeiten bleiben gleich)."""
    if not servings or not data.servings or servings == data.servings:
        return data
    factor = servings / data.servings
    return replace(
        data,
        servings=servings,
        ingredients=[scale_ingredient(i, factor) for i in data.ingredients],
    )
