"""Zutaten eines Rezepts auf die Einkaufsliste setzen (mit Zusammenfassen).

- Menge wird auf die gewünschten Portionen skaliert (Standardversion)
- gleiche Zutat + umrechenbare Einheit → bestehender offener Eintrag wird
  erhöht (500 g + 1 kg Mehl → 1,5 kg Mehl)
- unbestimmte Mengen (Prise, etwas, nach Geschmack) werden nicht addiert,
  sondern nur einmal gelistet
"""

from __future__ import annotations

import re
import sqlite3
from typing import Any

from .db import shopping
from .db.recipes import _require_recipe
from .db.versions import get_version_data
from .ingredient_parser import parse_ingredient
from .models import Ingredient
from .scaling import format_quantity, scale_version
from .units import Quantity, combine_quantities, is_vague_note, is_vague_unit, normalize_unit


def name_key(name: str) -> str:
    """Vergleichsschlüssel für Zutatennamen."""
    return re.sub(r"[^\wäöüß]+", " ", name.casefold()).strip()


def item_summary(name: str, amount: float | None, unit: str | None, amount_max: float | None, note: str | None) -> str:
    """Text eines Listeneintrags, z. B. "1,5 kg Mehl" oder "Salz (etwas)"."""
    qty = format_quantity(amount, unit, amount_max)
    text = f"{qty} {name}".strip()
    if note and amount is None and not unit:
        text += f" ({note})"
    return text


def _quantity(item: dict[str, Any]) -> Quantity:
    return Quantity(item["amount"], item["unit"], item["amount_max"], item["note"])


def add_ingredients(
    conn: sqlite3.Connection,
    ingredients: list[Ingredient],
    *,
    recipe_id: int | None = None,
    recipe_title: str | None = None,
) -> list[dict[str, Any]]:
    """Zutaten in die eigene Liste übernehmen; gibt geänderte/neue Einträge zurück."""
    changed: list[dict[str, Any]] = []
    source = {"recipe_id": recipe_id, "title": recipe_title} if recipe_id else None
    for ing in ingredients:
        key = name_key(ing.name)
        new_q = Quantity(ing.amount, normalize_unit(ing.unit), ing.amount_max, ing.note)
        vague = ing.amount is None or is_vague_unit(ing.unit) or is_vague_note(ing.note)
        target: dict[str, Any] | None = None
        merged: Quantity | None = None
        for existing in shopping.list_items(conn, shopping.STATUS_OPEN):
            if name_key(existing["name"]) != key:
                continue
            if vague:
                target, merged = existing, _quantity(existing)  # schon auf der Liste → nichts addieren
                break
            combined = combine_quantities([_quantity(existing), new_q])
            numeric = [q for q in combined if q.amount is not None]
            if len(numeric) == 1:
                target, merged = existing, numeric[0]
                break
        sources = [
            *(target["sources"] if target else []),
            *([source | {"amount": ing.amount, "unit": ing.unit}] if source else []),
        ]
        if target is not None and merged is not None:
            changed.append(
                shopping.update_item(
                    conn,
                    target["uid"],
                    amount=merged.amount,
                    amount_max=merged.amount_max,
                    unit=merged.unit,
                    summary=item_summary(target["name"], merged.amount, merged.unit, merged.amount_max, target["note"]),
                    sources=sources,
                    description=_description(sources),
                )
            )
        else:
            # Einheit normalisieren (1000 g → 1 kg), unbestimmte Mengen unverändert
            q = new_q if vague else combine_quantities([new_q])[0]
            changed.append(
                shopping.add_item(
                    conn,
                    summary=item_summary(ing.name, q.amount, q.unit, q.amount_max, ing.note),
                    name=ing.name,
                    amount=q.amount,
                    amount_max=q.amount_max,
                    unit=q.unit,
                    note=ing.note,
                    recipe_id=recipe_id,
                    sources=sources,
                    description=_description(sources),
                )
            )
    return changed


def _description(sources: list[dict[str, Any]]) -> str | None:
    titles = list(dict.fromkeys(s["title"] for s in sources if s.get("title")))
    return ("für: " + ", ".join(titles)) if titles else None


def recipe_ingredients(
    conn: sqlite3.Connection, recipe_id: int, servings: float | None = None
) -> tuple[dict[str, Any], list[Ingredient]]:
    """Zutaten der Standardversion, skaliert auf `servings`."""
    recipe = _require_recipe(conn, recipe_id)
    data = scale_version(get_version_data(conn, recipe["default_version_id"]), servings)
    return recipe, data.ingredients


def add_recipe(conn: sqlite3.Connection, recipe_id: int, servings: float | None = None) -> list[dict[str, Any]]:
    """Rezept auf die eigene Einkaufsliste setzen."""
    recipe, ingredients = recipe_ingredients(conn, recipe_id, servings)
    return add_ingredients(conn, ingredients, recipe_id=recipe_id, recipe_title=recipe["title"])


def parse_manual_item(summary: str) -> dict[str, Any]:
    """Manuell eingetippten Eintrag ("200 g Mehl") für spätere Zusammenfassung zerlegen."""
    ing = parse_ingredient(summary)
    return {
        "name": ing.name,
        "amount": ing.amount,
        "amount_max": ing.amount_max,
        "unit": ing.unit,
        "note": ing.note,
    }
