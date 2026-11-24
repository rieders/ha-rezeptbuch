"""Eigener Fallback-Parser für schema.org/Recipe in JSON-LD.

Wird benutzt, wenn recipe-scrapers scheitert oder ein unvollständiges
Ergebnis liefert. Unterstützt @graph, Listen, mainEntity, @id-Verweise,
HowToSection/HowToStep, ISO-8601-Dauern und recipeYield als Liste.
"""

from __future__ import annotations

from collections.abc import Iterator
import html as html_lib
import json
import re
from typing import Any
from urllib.parse import urljoin

_SCRIPT_RE = re.compile(
    r"<script[^>]+type\s*=\s*[\"']?application/ld\+json[\"']?[^>]*>(.*?)</script>",
    re.IGNORECASE | re.DOTALL,
)
_TAG_RE = re.compile(r"<[^>]+>")
_DURATION_RE = re.compile(
    r"^P(?:(?P<d>\d+(?:[.,]\d+)?)D)?(?:T(?:(?P<h>\d+(?:[.,]\d+)?)H)?(?:(?P<m>\d+(?:[.,]\d+)?)M)?(?:(?P<s>\d+(?:[.,]\d+)?)S)?)?$",
    re.IGNORECASE,
)


def clean_text(value: Any) -> str:
    """HTML-Entities/Tags entfernen, Leerraum normalisieren."""
    if value is None:
        return ""
    text = html_lib.unescape(str(value))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    text = _TAG_RE.sub(" ", text)
    text = html_lib.unescape(text)
    lines = [re.sub(r"[ \t ]+", " ", line).strip() for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def parse_duration_minutes(value: Any) -> int | None:
    """ISO-8601-Dauer ("PT1H15M", "P0DT1H20M") oder Zahl → Minuten."""
    if value is None or value == "":
        return None
    if isinstance(value, (int, float)):
        return round(value) if value > 0 else None
    text = str(value).strip()
    if text.isdigit():
        return int(text) or None
    m = _DURATION_RE.match(text)
    if not m or not any(m.groupdict().values()):
        return None

    def _f(key: str) -> float:
        raw = m.group(key)
        return float(raw.replace(",", ".")) if raw else 0.0

    minutes = _f("d") * 1440 + _f("h") * 60 + _f("m") + _f("s") / 60
    return round(minutes) or None


def _load_json(raw: str) -> Any:
    raw = raw.strip()
    raw = re.sub(r"^\s*(?:<!--|//\s*<!\[CDATA\[|/\*<!\[CDATA\[\*/)", "", raw)
    raw = re.sub(r"(?:-->|//\s*\]\]>|/\*\]\]>\*/)\s*$", "", raw)
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        # häufiger Fehler: Steuerzeichen/Zeilenumbrüche in Strings
        try:
            return json.loads(raw, strict=False)
        except json.JSONDecodeError:
            return None


def _iter_nodes(data: Any) -> Iterator[dict[str, Any]]:
    if isinstance(data, list):
        for item in data:
            yield from _iter_nodes(item)
    elif isinstance(data, dict):
        yield data
        for key in ("@graph", "mainEntity", "mainEntityOfPage", "hasPart"):
            if key in data and isinstance(data[key], (list, dict)):
                yield from _iter_nodes(data[key])


def _has_type(node: dict[str, Any], type_name: str) -> bool:
    types = node.get("@type")
    if isinstance(types, str):
        types = [types]
    return any(isinstance(t, str) and t.split("/")[-1].lower() == type_name.lower() for t in types or [])


def extract_jsonld_nodes(html: str) -> list[dict[str, Any]]:
    """Alle JSON-LD-Knoten der Seite (flach)."""
    nodes: list[dict[str, Any]] = []
    for raw in _SCRIPT_RE.findall(html or ""):
        data = _load_json(raw)
        if data is not None:
            nodes.extend(_iter_nodes(data))
    return nodes


def find_recipe_node(html: str) -> tuple[dict[str, Any] | None, dict[str, dict[str, Any]]]:
    """Erster Recipe-Knoten und ein Index aller Knoten nach @id."""
    nodes = extract_jsonld_nodes(html)
    index = {n["@id"]: n for n in nodes if isinstance(n.get("@id"), str)}
    for node in nodes:
        if _has_type(node, "Recipe"):
            return node, index
    return None, index


def _resolve(value: Any, index: dict[str, dict[str, Any]]) -> Any:
    if isinstance(value, dict) and set(value) == {"@id"} and value["@id"] in index:
        return index[value["@id"]]
    return value


def _image_url(value: Any, index: dict[str, dict[str, Any]], base_url: str) -> str | None:
    value = _resolve(value, index)
    if isinstance(value, list):
        # größtes Bild bevorzugen, wenn Breiten angegeben sind
        candidates = [_resolve(v, index) for v in value]
        with_width = [c for c in candidates if isinstance(c, dict) and str(c.get("width", "")).isdigit()]
        if with_width:
            candidates = sorted(with_width, key=lambda c: int(c["width"]), reverse=True)
        for c in candidates:
            url = _image_url(c, index, base_url)
            if url:
                return url
        return None
    if isinstance(value, dict):
        for key in ("url", "contentUrl", "@id"):
            if isinstance(value.get(key), str) and not value[key].startswith("#"):
                return urljoin(base_url, value[key])
        return None
    if isinstance(value, str) and value.strip():
        return urljoin(base_url, value.strip())
    return None


def _string_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, str):
        return [p.strip() for p in value.split(",") if p.strip()]
    if isinstance(value, list):
        out: list[str] = []
        for v in value:
            out.extend(_string_list(v) if not isinstance(v, dict) else [clean_text(v.get("name"))])
        return [o for o in out if o]
    if isinstance(value, dict):
        return [clean_text(value.get("name"))] if value.get("name") else []
    return [str(value)]


def _instructions(value: Any, index: dict[str, dict[str, Any]], group: str | None = None) -> list[dict[str, Any]]:
    """Liste von {"text", "group"} aus beliebigen recipeInstructions."""
    value = _resolve(value, index)
    steps: list[dict[str, Any]] = []
    if value is None:
        return steps
    if isinstance(value, str):
        text = clean_text(value)
        parts = [p for p in re.split(r"\n+", text) if p.strip()]
        if len(parts) == 1:  # "1. … 2. …" in einer Zeile
            numbered = re.split(r"\s(?=\d{1,2}\.\s)", parts[0])
            if len(numbered) > 1:
                parts = numbered
        steps.extend({"text": re.sub(r"^\d{1,2}[.)]\s*", "", p).strip(), "group": group} for p in parts)
        return [s for s in steps if s["text"]]
    if isinstance(value, list):
        for item in value:
            steps.extend(_instructions(item, index, group))
        return steps
    if isinstance(value, dict):
        if _has_type(value, "HowToSection"):
            name = clean_text(value.get("name")) or group
            return _instructions(value.get("itemListElement"), index, name)
        if "itemListElement" in value and not value.get("text"):
            return _instructions(value.get("itemListElement"), index, group)
        text = clean_text(value.get("text") or value.get("name") or value.get("description"))
        if text:
            steps.append({"text": text, "group": group})
    return steps


def parse_yield(value: Any) -> tuple[float | None, str | None]:
    """recipeYield → (Anzahl, Einheit). ["4", "4 Portionen"] → (4, "Portionen")."""
    candidates = value if isinstance(value, list) else [value]
    best: tuple[float | None, str | None] = (None, None)
    for cand in candidates:
        if cand is None:
            continue
        if isinstance(cand, (int, float)):
            if best[0] is None:
                best = (float(cand), None)
            continue
        text = clean_text(cand)
        m = re.search(r"(\d+(?:[.,]\d+)?)(?:\s*(?:-|–|bis)\s*\d+(?:[.,]\d+)?)?\s*(.*)", text)
        if not m:
            continue
        amount = float(m.group(1).replace(",", "."))
        unit = normalize_yield_unit(m.group(2))
        if best[0] is None or (unit and not best[1]):
            best = (amount, unit)
    if best[0] == 0:
        return None, None
    return best


_YIELD_UNITS = {
    "servings": "Portionen",
    "serving": "Portionen",
    "portion": "Portionen",
    "portionen": "Portionen",
    "personen": "Portionen",
    "person": "Portionen",
    "pers.": "Portionen",
    "people": "Portionen",
    "items": "Stück",
    "item": "Stück",
    "stück": "Stück",
    "stk.": "Stück",
    "pieces": "Stück",
}


def normalize_yield_unit(text: str | None) -> str | None:
    """Portionsangabe vereinheitlichen ("servings" → "Portionen")."""
    text = (text or "").strip().strip(".,;:").strip()
    if text.startswith("(") and text.endswith(")"):
        text = text[1:-1].strip()
    if not text:
        return None
    return _YIELD_UNITS.get(text.lower(), text[:40])


def parse_recipe_jsonld(html: str, base_url: str) -> dict[str, Any] | None:
    """Rezept aus JSON-LD als Rohdaten-Dict (oder None)."""
    node, index = find_recipe_node(html)
    if node is None:
        return None
    servings, servings_unit = parse_yield(node.get("recipeYield") or node.get("yield"))
    ingredients = node.get("recipeIngredient") or node.get("ingredients") or []
    if isinstance(ingredients, str):
        ingredients = [ingredients]
    author = _resolve(node.get("author"), index)
    if isinstance(author, list):
        author = _resolve(author[0], index) if author else None
    author_name = clean_text(author.get("name")) if isinstance(author, dict) else clean_text(author)
    return {
        "title": clean_text(node.get("name") or node.get("headline")),
        "description": clean_text(node.get("description")),
        "image": _image_url(node.get("image") or node.get("thumbnailUrl"), index, base_url),
        "ingredients": [clean_text(i) for i in ingredients if clean_text(i)],
        "instructions": _instructions(node.get("recipeInstructions"), index),
        "servings": servings,
        "servings_unit": servings_unit,
        "prep_time": parse_duration_minutes(node.get("prepTime")),
        "cook_time": parse_duration_minutes(node.get("cookTime")),
        "total_time": parse_duration_minutes(node.get("totalTime")),
        "categories": _string_list(node.get("recipeCategory")),
        "keywords": _string_list(node.get("keywords")),
        "author": author_name or None,
        "canonical_url": _canonical(node, base_url),
    }


def _canonical(node: dict[str, Any], base_url: str) -> str | None:
    for key in ("url", "mainEntityOfPage"):
        value = node.get(key)
        if isinstance(value, dict):
            value = value.get("@id") or value.get("url")
        if isinstance(value, str) and value.startswith("http"):
            return value.split("#", 1)[0]
    return None
