"""Quell-Kategorien/Schlagworte auf vorhandene Kategorien abbilden, Rest → Tags.

Reihenfolge je Schlagwort:
1. gelerntes Mapping (category_mappings)
2. exakter Kategoriename (ohne Groß/Klein, Umlaute egal)
3. eingebaute Synonyme ("Suppe" → "Suppen & Eintöpfe", "Kekse" → "Plätzchen")

recipeCategory der Quelle ist "primär". Die "sekundären" Keywords werden nur
dann einer Kategorie zugeordnet, wenn diese im selben Hauptzweig liegt wie die
primären Treffer – sonst landen sie als Tag (Beispiel: Apfelkuchen mit
Keyword "Vegetarisch" kommt nicht nach "Kochen › Vegetarisch").
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re
import sqlite3
import unicodedata

from ..db.categories import ancestors, forget_mapping, get_mapping, learn_mapping, list_categories

SYNONYMS: dict[str, tuple[str, ...]] = {
    "Suppen & Eintöpfe": ("suppe", "suppen", "eintopf", "eintöpfe", "eintoepfe", "soup", "stew", "chili"),
    "Fleisch": (
        "fleisch",
        "rind",
        "rindfleisch",
        "schwein",
        "schweinefleisch",
        "geflügel",
        "hähnchen",
        "huhn",
        "lamm",
        "wild",
        "meat",
        "braten",
    ),
    "Fisch": ("fisch", "fish", "meeresfrüchte", "seafood", "lachs", "garnelen"),
    "Vegetarisch": ("vegetarisch", "vegetarian", "vegan", "veggie"),
    "Beilagen": ("beilage", "beilagen", "side dish", "sides"),
    "Saucen": ("sauce", "saucen", "soße", "soßen", "sosse", "dip", "dips", "dressing", "dressings"),
    "Salate": ("salat", "salate", "salad", "salads"),
    "Kuchen": ("kuchen", "cake", "blechkuchen", "rührkuchen", "obstkuchen"),
    "Torten": ("torte", "torten", "tarte", "tartes"),
    "Brot & Brötchen": ("brot", "brote", "brötchen", "broetchen", "bread", "buns", "brotbacken"),
    "Plätzchen": ("plätzchen", "plaetzchen", "kekse", "keks", "cookies", "weihnachtsplätzchen", "weihnachtsbäckerei"),
    "Herzhaftes Gebäck": ("herzhaftes gebäck", "quiche", "pizza", "flammkuchen", "herzhaft backen"),
    "Cocktails": ("cocktail", "cocktails", "longdrink", "longdrinks", "drinks mit alkohol"),
    "Alkoholfrei": ("alkoholfrei", "mocktail", "mocktails", "limonade"),
    "Heißgetränke": ("heißgetränk", "heißgetränke", "kaffee", "tee", "kakao", "glühwein", "punsch"),
    "Smoothies": ("smoothie", "smoothies", "shake", "shakes"),
    "Liköre": ("likör", "liköre", "likoer", "liqueur"),
    "Backen": ("backen", "gebäck", "baking", "backrezepte", "dessert backen"),
    "Kochen": ("kochen", "hauptspeise", "hauptgericht", "main course", "hauptgerichte"),
    "Getränke": ("getränk", "getränke", "drinks", "beverages"),
}


def normalize_keyword(text: str) -> str:
    """Kleinbuchstaben, ohne Diakritika und Satzzeichen."""
    text = unicodedata.normalize("NFKD", text.casefold())
    text = "".join(c for c in text if not unicodedata.combining(c))
    text = text.replace("ß", "ss")
    return re.sub(r"[^a-z0-9]+", " ", text).strip()


def split_keywords(values: list[str] | None) -> list[str]:
    """Kommagetrennte Werte aufsplitten, bereinigen, Duplikate entfernen."""
    seen: dict[str, str] = {}
    for value in values or []:
        for part in re.split(r"[,;|]", str(value)):
            word = " ".join(part.strip().lstrip("#").split())
            if word and len(word) <= 60 and normalize_keyword(word) not in seen:
                seen[normalize_keyword(word)] = word
    return list(seen.values())


@dataclass
class MappingResult:
    """Ergebnis der Zuordnung."""

    category_ids: list[int] = field(default_factory=list)
    tags: list[str] = field(default_factory=list)
    matched: dict[str, int] = field(default_factory=dict)  # Schlagwort → Kategorie-ID
    primary_keywords: list[str] = field(default_factory=list)


def _build_index(conn: sqlite3.Connection) -> dict[str, int]:
    """Normalisierter Kategoriename → ID (bei gleichen Namen gewinnt die flachere)."""
    index: dict[str, tuple[int, int]] = {}
    for cat in list_categories(conn):
        depth = cat["path"].count("›")
        key = normalize_keyword(cat["name"])
        if key not in index or depth < index[key][1]:
            index[key] = (cat["id"], depth)
    return {k: v[0] for k, v in index.items()}


def _lookup(conn: sqlite3.Connection, keyword: str, index: dict[str, int]) -> int | None:
    learned = get_mapping(conn, keyword)
    if learned is not None:
        return learned
    key = normalize_keyword(keyword)
    if key in index:
        return index[key]
    for cat_name, words in SYNONYMS.items():
        if key in {normalize_keyword(w) for w in words}:
            target = index.get(normalize_keyword(cat_name))
            if target is not None:
                return target
    return None


def map_keywords(
    conn: sqlite3.Connection,
    primary: list[str] | None,
    secondary: list[str] | None = None,
) -> MappingResult:
    """Schlagworte der Quelle auf Kategorien abbilden, Rest als Tags."""
    index = _build_index(conn)
    result = MappingResult(primary_keywords=split_keywords(primary))
    roots: set[int] = set()

    for kw in result.primary_keywords:
        cid = _lookup(conn, kw, index)
        if cid is None:
            result.tags.append(kw)
            continue
        result.matched[kw] = cid
        roots.add(ancestors(conn, cid)[0]["id"])

    primary_norm = {normalize_keyword(k) for k in result.primary_keywords}
    for kw in split_keywords(secondary):
        if normalize_keyword(kw) in primary_norm:
            continue
        cid = _lookup(conn, kw, index)
        if cid is not None and (not roots or ancestors(conn, cid)[0]["id"] in roots):
            result.matched[kw] = cid
        else:
            result.tags.append(kw)

    # Spezifischste Kategorien behalten: Vorfahren eines Treffers entfernen
    ids = list(dict.fromkeys(result.matched.values()))
    redundant: set[int] = set()
    for cid in ids:
        redundant.update(a["id"] for a in ancestors(conn, cid)[:-1])
    result.category_ids = [cid for cid in ids if cid not in redundant]
    return result


def learn_from_correction(
    conn: sqlite3.Connection,
    *,
    primary_keywords: list[str],
    matched: dict[str, int],
    suggested_ids: list[int],
    final_ids: list[int],
) -> None:
    """Aus Korrekturen beim Bestätigen lernen.

    - Hat der Nutzer eine vorgeschlagene Kategorie entfernt, wird ein dafür
      gelerntes Mapping vergessen.
    - Hat er genau eine Kategorie ergänzt, werden darauf gelernt: Schlagworte,
      deren Treffer er entfernt hat (Korrektur), und primäre Quell-Kategorien
      ohne Treffer.
    """
    removed = set(suggested_ids) - set(final_ids)
    added = [c for c in final_ids if c not in suggested_ids]
    for kw, cid in matched.items():
        if cid in removed and get_mapping(conn, kw) == cid:
            forget_mapping(conn, kw)
    if len(added) == 1:
        for kw, cid in matched.items():
            if cid in removed:
                learn_mapping(conn, kw, added[0])
        for kw in primary_keywords:
            if kw not in matched:
                learn_mapping(conn, kw, added[0])
    elif not added:
        # Bestätigte Treffer stärken (hits++)
        for kw, cid in matched.items():
            if cid in final_ids and kw in primary_keywords and get_mapping(conn, kw) == cid:
                learn_mapping(conn, kw, cid)
