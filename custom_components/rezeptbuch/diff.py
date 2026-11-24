"""Unterschiede zwischen zwei Rezeptversionen berechnen.

Ergebnis ist JSON-fähig und wird vom Panel farbig dargestellt:
    {"meta": [...], "ingredients": [...], "steps": [...], "has_changes": bool}
Jeder Eintrag hat "status": unchanged | changed | added | removed.
"""

from __future__ import annotations

from difflib import SequenceMatcher
import re
from typing import Any

from .models import Ingredient, Step, VersionData
from .scaling import format_quantity

UNCHANGED = "unchanged"
CHANGED = "changed"
ADDED = "added"
REMOVED = "removed"

_META_FIELDS = (
    ("servings", "Portionen"),
    ("servings_unit", "Portionsangabe"),
    ("prep_time", "Vorbereitungszeit"),
    ("cook_time", "Koch-/Backzeit"),
    ("total_time", "Gesamtzeit"),
)


def _key(name: str) -> str:
    return re.sub(r"[^\wäöüß]+", " ", name.casefold()).strip()


def _similar(a: str, b: str) -> float:
    return SequenceMatcher(None, _key(a), _key(b)).ratio()


def _qty(ing: Ingredient) -> str:
    return format_quantity(ing.amount, ing.unit, ing.amount_max) or "–"


def _ingredient_entry(old: Ingredient | None, new: Ingredient | None) -> dict[str, Any]:
    if old is None and new is not None:
        return {
            "status": ADDED,
            "old": None,
            "new": new.to_dict(),
            "changes": [],
            "summary": f"neu: {format_quantity(new.amount, new.unit, new.amount_max)} {new.name}".replace("  ", " "),
        }
    if new is None and old is not None:
        return {
            "status": REMOVED,
            "old": old.to_dict(),
            "new": None,
            "changes": [],
            "summary": f"gestrichen: {old.name}",
        }
    assert old is not None and new is not None
    changes = [
        f for f in ("name", "amount", "amount_max", "unit", "note", "group") if getattr(old, f) != getattr(new, f)
    ]
    status = CHANGED if changes else UNCHANGED
    summary = ""
    if changes:
        parts: list[str] = []
        if {"amount", "amount_max", "unit"} & set(changes):
            parts.append(f"{_qty(old)} → {_qty(new)}")
        if "name" in changes:
            parts.append(f"„{old.name}“ → „{new.name}“")
        if "note" in changes:
            parts.append(f"Notiz: {old.note or '–'} → {new.note or '–'}")
        if "group" in changes:
            parts.append(f"Gruppe: {old.group or '–'} → {new.group or '–'}")
        summary = f"{new.name} " + ", ".join(parts)
    return {
        "status": status,
        "old": old.to_dict(),
        "new": new.to_dict(),
        "changes": changes,
        "summary": summary,
    }


def _pair_replace(olds: list[Any], news: list[Any], score, threshold: float) -> list[tuple[Any | None, Any | None]]:
    """Ersetzte Blöcke paarweise zuordnen (beste Ähnlichkeit zuerst)."""
    pairs: list[tuple[int, int, float]] = []
    for i, o in enumerate(olds):
        for j, n in enumerate(news):
            s = score(o, n)
            if s >= threshold:
                pairs.append((i, j, s))
    pairs.sort(key=lambda p: -p[2])
    used_o: set[int] = set()
    used_n: set[int] = set()
    match: dict[int, int] = {}
    for i, j, _ in pairs:
        if i in used_o or j in used_n:
            continue
        used_o.add(i)
        used_n.add(j)
        match[j] = i
    result: list[tuple[Any | None, Any | None]] = []
    for i, o in enumerate(olds):
        if i not in used_o:
            result.append((o, None))
    for j, n in enumerate(news):
        result.append((olds[match[j]], n) if j in match else (None, n))
    return result


def diff_ingredients(old: list[Ingredient], new: list[Ingredient]) -> list[dict[str, Any]]:
    """Zutaten vergleichen (Zuordnung über den Namen)."""
    sm = SequenceMatcher(None, [_key(i.name) for i in old], [_key(i.name) for i in new], autojunk=False)
    result: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            for o, n in zip(old[i1:i2], new[j1:j2], strict=True):
                result.append(_ingredient_entry(o, n))
        elif tag == "delete":
            result.extend(_ingredient_entry(o, None) for o in old[i1:i2])
        elif tag == "insert":
            result.extend(_ingredient_entry(None, n) for n in new[j1:j2])
        else:
            for o, n in _pair_replace(old[i1:i2], new[j1:j2], lambda a, b: _similar(a.name, b.name), 0.75):
                result.append(_ingredient_entry(o, n))
    return result


def word_diff(old: str, new: str) -> list[dict[str, str]]:
    """Wortweiser Diff für Schritttexte."""
    a = re.findall(r"\S+|\s+", old)
    b = re.findall(r"\S+|\s+", new)
    sm = SequenceMatcher(None, a, b, autojunk=False)
    out: list[dict[str, str]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out.append({"op": "equal", "text": "".join(a[i1:i2])})
        else:
            if i2 > i1:
                out.append({"op": "delete", "text": "".join(a[i1:i2])})
            if j2 > j1:
                out.append({"op": "insert", "text": "".join(b[j1:j2])})
    return out


def _step_entry(old: Step | None, new: Step | None) -> dict[str, Any]:
    if old is None and new is not None:
        return {"status": ADDED, "old": None, "new": new.to_dict(), "words": []}
    if new is None and old is not None:
        return {"status": REMOVED, "old": old.to_dict(), "new": None, "words": []}
    assert old is not None and new is not None
    same = old.to_dict() == new.to_dict()
    return {
        "status": UNCHANGED if same else CHANGED,
        "old": old.to_dict(),
        "new": new.to_dict(),
        "words": [] if old.text == new.text else word_diff(old.text, new.text),
    }


def _norm_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def diff_steps(old: list[Step], new: list[Step]) -> list[dict[str, Any]]:
    """Schritte vergleichen (Zuordnung über den Text)."""
    sm = SequenceMatcher(None, [_norm_text(s.text) for s in old], [_norm_text(s.text) for s in new], autojunk=False)
    result: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            result.extend(_step_entry(o, n) for o, n in zip(old[i1:i2], new[j1:j2], strict=True))
        elif tag == "delete":
            result.extend(_step_entry(o, None) for o in old[i1:i2])
        elif tag == "insert":
            result.extend(_step_entry(None, n) for n in new[j1:j2])
        else:
            for o, n in _pair_replace(
                old[i1:i2],
                new[j1:j2],
                lambda a, b: SequenceMatcher(None, a.text, b.text).ratio(),
                0.5,
            ):
                result.append(_step_entry(o, n))
    return result


def diff_versions(old: VersionData, new: VersionData) -> dict[str, Any]:
    """Komplettdiff zweier Versionen."""
    meta = []
    for field_name, label in _META_FIELDS:
        a, b = getattr(old, field_name), getattr(new, field_name)
        if a != b:
            meta.append({"field": field_name, "label": label, "old": a, "new": b})
    ingredients = diff_ingredients(old.ingredients, new.ingredients)
    steps = diff_steps(old.steps, new.steps)
    has_changes = bool(meta) or any(e["status"] != UNCHANGED for e in (*ingredients, *steps))
    return {
        "meta": meta,
        "ingredients": ingredients,
        "steps": steps,
        "has_changes": has_changes,
        "summary": [e["summary"] for e in ingredients if e["status"] != UNCHANGED],
    }
