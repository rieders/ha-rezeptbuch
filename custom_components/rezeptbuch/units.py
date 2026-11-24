"""Deutsche Küchen-Einheiten: Erkennung, Pluralformen, Umrechnung, Zusammenfassung."""

from __future__ import annotations

from dataclasses import dataclass

DIM_MASS = "mass"  # Basis: g
DIM_VOLUME = "volume"  # Basis: ml


@dataclass(frozen=True)
class UnitDef:
    """Definition einer Einheit."""

    canonical: str
    aliases: tuple[str, ...]
    dimension: str | None = None  # None = eigene, nicht umrechenbare Einheit
    factor: float = 1.0  # Faktor zur Basiseinheit der Dimension
    plural: str | None = None
    vague: bool = False  # "Prise", "Msp." … nicht addieren
    spoon: bool = False  # TL/EL – bevorzugt wieder als Löffel ausgeben


UNITS: tuple[UnitDef, ...] = (
    UnitDef("mg", ("mg", "milligramm"), DIM_MASS, 0.001),
    UnitDef("g", ("g", "gr", "gramm", "grm"), DIM_MASS, 1.0),
    UnitDef("kg", ("kg", "kilo", "kilogramm"), DIM_MASS, 1000.0),
    UnitDef("Pfund", ("pfund", "pfd"), DIM_MASS, 500.0),
    UnitDef("ml", ("ml", "milliliter"), DIM_VOLUME, 1.0),
    UnitDef("cl", ("cl", "zentiliter"), DIM_VOLUME, 10.0),
    UnitDef("dl", ("dl", "deziliter"), DIM_VOLUME, 100.0),
    UnitDef("l", ("l", "liter", "ltr"), DIM_VOLUME, 1000.0),
    UnitDef(
        "TL",
        ("tl", "teel", "teelöffel", "teeloeffel", "tsp"),
        DIM_VOLUME,
        5.0,
        spoon=True,
    ),
    UnitDef(
        "EL",
        ("el", "essl", "esslöffel", "essloeffel", "eßl", "eßlöffel", "tbsp"),
        DIM_VOLUME,
        15.0,
        spoon=True,
    ),
    UnitDef("Msp.", ("msp", "messerspitze", "messerspitzen"), vague=True),
    UnitDef("Prise", ("prise", "prisen", "pr"), plural="Prisen", vague=True),
    UnitDef("Spritzer", ("spritzer",), vague=True),
    UnitDef("Schuss", ("schuss", "schüsse"), vague=True),
    UnitDef("Tropfen", ("tropfen", "trpf")),
    UnitDef(
        "Pck.",
        ("pck", "päckchen", "packung", "packungen", "pk", "pkg", "pckg", "päck"),
    ),
    UnitDef("Becher", ("becher",)),
    UnitDef("Dose", ("dose", "dosen", "ds"), plural="Dosen"),
    UnitDef("Bund", ("bund", "bd", "bündel")),
    UnitDef("Zehe", ("zehe", "zehen"), plural="Zehen"),
    UnitDef("Stück", ("stück", "stk", "stck", "st"), plural="Stück"),
    UnitDef("Scheibe", ("scheibe", "scheiben", "sch"), plural="Scheiben"),
    UnitDef("Glas", ("glas", "gläser", "gl"), plural="Gläser"),
    UnitDef("Tasse", ("tasse", "tassen", "tas"), plural="Tassen"),
    UnitDef("Stange", ("stange", "stangen", "stg"), plural="Stangen"),
    UnitDef("Kopf", ("kopf", "köpfe"), plural="Köpfe"),
    UnitDef("Knolle", ("knolle", "knollen"), plural="Knollen"),
    UnitDef("Blatt", ("blatt", "blätter", "bl"), plural="Blatt"),
    UnitDef("Zweig", ("zweig", "zweige", "zweiglein"), plural="Zweige"),
    UnitDef("Stiel", ("stiel", "stiele"), plural="Stiele"),
    UnitDef("Handvoll", ("handvoll", "hand voll")),
    UnitDef("Würfel", ("würfel",)),
    UnitDef("Beutel", ("beutel", "btl")),
    UnitDef("Flasche", ("flasche", "flaschen", "fl"), plural="Flaschen"),
    UnitDef("Tüte", ("tüte", "tüten"), plural="Tüten"),
    UnitDef("Tafel", ("tafel", "tafeln"), plural="Tafeln"),
    UnitDef("Kugel", ("kugel", "kugeln"), plural="Kugeln"),
    UnitDef("Rolle", ("rolle", "rollen"), plural="Rollen"),
    UnitDef("Portion", ("portion", "portionen"), plural="Portionen"),
    UnitDef("Ecke", ("ecke", "ecken"), plural="Ecken"),
    UnitDef("Netz", ("netz",)),
    UnitDef("Schale", ("schale", "schalen"), plural="Schalen"),
    UnitDef("cm", ("cm",)),
)

_ALIAS_MAP: dict[str, UnitDef] = {}
for _u in UNITS:
    _ALIAS_MAP[_u.canonical.lower().rstrip(".")] = _u
    for _a in _u.aliases:
        _ALIAS_MAP[_a.lower()] = _u
_CANONICAL_MAP: dict[str, UnitDef] = {u.canonical: u for u in UNITS}

# Begriffe ohne Mengenangabe, die nicht addiert werden ("nach Geschmack" …)
VAGUE_PHRASES: tuple[str, ...] = (
    "etwas",
    "ein wenig",
    "wenig",
    "ein paar",
    "einige",
    "reichlich",
    "nach geschmack",
    "nach belieben",
    "nach bedarf",
    "n. b.",
    "n.b.",
    "evtl.",
    "eventuell",
    "optional",
)


def lookup_unit(token: str | None) -> UnitDef | None:
    """Einheit zu einem Token finden (Groß/Klein egal, Punkt am Ende egal)."""
    if not token:
        return None
    key = token.strip().lower().rstrip(".")
    if not key:
        return None
    if key in _ALIAS_MAP:
        return _ALIAS_MAP[key]
    return None


def get_unit(unit: str | None) -> UnitDef | None:
    """UnitDef zu einer bereits kanonischen (oder beliebigen) Einheit."""
    if not unit:
        return None
    return _CANONICAL_MAP.get(unit) or lookup_unit(unit)


def normalize_unit(unit: str | None) -> str | None:
    """Einheit in kanonische Schreibweise bringen; Unbekanntes bleibt erhalten."""
    if unit is None:
        return None
    unit = unit.strip()
    if not unit:
        return None
    udef = lookup_unit(unit)
    return udef.canonical if udef else unit


def unit_display(unit: str | None, amount: float | None) -> str:
    """Einheit passend zur Menge (Singular/Plural)."""
    if not unit:
        return ""
    udef = get_unit(unit)
    if udef is None:
        return unit
    if amount is not None and amount > 1 and udef.plural:
        return udef.plural
    return udef.canonical


def is_vague_unit(unit: str | None) -> bool:
    """True für Einheiten wie Prise/Msp., die nicht addiert werden."""
    udef = get_unit(unit)
    return bool(udef and udef.vague)


def is_vague_note(note: str | None) -> bool:
    """True, wenn die Notiz eine unbestimmte Menge beschreibt ("etwas" …)."""
    if not note:
        return False
    low = note.strip().lower()
    return any(low == p or low.startswith(p + " ") for p in VAGUE_PHRASES)


# ---------------------------------------------------------------------------
# Zusammenfassen (Einkaufsliste)
# ---------------------------------------------------------------------------


@dataclass
class Quantity:
    """Menge mit optionaler Obergrenze (Bereich) und Einheit."""

    amount: float | None
    unit: str | None = None
    amount_max: float | None = None
    note: str | None = None


def _dimension_key(unit: str | None) -> str:
    udef = get_unit(unit)
    if udef is None:
        return f"raw:{(unit or '').strip().lower()}"
    if udef.dimension:
        return f"dim:{udef.dimension}"
    return f"unit:{udef.canonical}"


def _to_base(amount: float, unit: str | None) -> float:
    udef = get_unit(unit)
    if udef and udef.dimension:
        return amount * udef.factor
    return amount


def _from_base(base: float, dimension: str, source_units: set[str]) -> tuple[float, str]:
    """Basismenge in eine gut lesbare Einheit zurückrechnen."""
    if dimension == DIM_MASS:
        if base >= 1000 and (base % 250 == 0 or "kg" in source_units):
            return base / 1000, "kg"
        if base < 1 and source_units == {"mg"}:
            return base * 1000, "mg"
        return base, "g"
    # Volumen
    defs = [_CANONICAL_MAP[u] for u in source_units if u in _CANONICAL_MAP]
    if defs and all(d.spoon for d in defs) and base < 100:
        if base >= 15 and abs(base / 15 - round(base / 15 * 2) / 2) < 1e-9:
            return base / 15, "EL"
        return base / 5, "TL"
    if base >= 1000 and (base % 250 == 0 or "l" in source_units):
        return base / 1000, "l"
    return base, "ml"


def combine_quantities(quantities: list[Quantity]) -> list[Quantity]:
    """Mengen einer Zutat zusammenfassen.

    - gleiche Dimension wird umgerechnet und addiert (g/kg, ml/l, TL/EL)
    - Stück-artige Einheiten werden nur mit gleicher Einheit addiert
    - unbestimmte Mengen (Prise, etwas, nach Geschmack, ohne Menge) werden nicht
      addiert, sondern einmal gelistet
    """
    numeric: dict[str, dict] = {}
    vague: list[Quantity] = []
    seen_vague: set[tuple[str | None, str | None]] = set()

    for q in quantities:
        if q.amount is None or is_vague_unit(q.unit) or is_vague_note(q.note):
            key = (normalize_unit(q.unit), (q.note or "").strip().lower() or None)
            if key not in seen_vague:
                seen_vague.add(key)
                vague.append(
                    Quantity(None, normalize_unit(q.unit), None, q.note)
                    if is_vague_unit(q.unit) or q.amount is None
                    else Quantity(None, None, None, q.note)
                )
            continue
        unit = normalize_unit(q.unit)
        dkey = _dimension_key(unit)
        slot = numeric.setdefault(dkey, {"min": 0.0, "max": 0.0, "units": set(), "ranged": False, "unit": unit})
        lo = _to_base(q.amount, unit)
        hi = _to_base(q.amount_max, unit) if q.amount_max is not None else lo
        slot["ranged"] = slot["ranged"] or q.amount_max is not None
        slot["min"] += lo
        slot["max"] += hi
        if unit:
            slot["units"].add(unit)

    result: list[Quantity] = []
    for dkey, slot in numeric.items():
        if dkey.startswith("dim:"):
            dim = dkey[4:]
            amount, unit = _from_base(slot["min"], dim, slot["units"])
            factor = amount / slot["min"] if slot["min"] else 1.0
            amax = slot["max"] * factor if slot["ranged"] else None
            result.append(Quantity(_round(amount), unit, _round(amax) if amax else None))
        else:
            result.append(
                Quantity(
                    _round(slot["min"]),
                    slot["unit"],
                    _round(slot["max"]) if slot["ranged"] else None,
                )
            )
    # bestimmte Mengen zuerst, dann unbestimmte – unbestimmte entfallen, wenn
    # bereits eine konkrete Menge derselben Einheit existiert
    numeric_units = {r.unit for r in result}
    has_numeric = bool(result)
    for v in vague:
        if v.unit is None and has_numeric:
            continue
        if v.unit is not None and v.unit in numeric_units:
            continue
        result.append(v)
    return result


def _round(value: float | None) -> float | None:
    if value is None:
        return None
    return round(value, 3)
