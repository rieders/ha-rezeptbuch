"""Parser für deutsche Zutatenzeilen.

Beispiele:
    "200 g Mehl"            → 200, g, Mehl
    "1/2 TL Salz"           → 0.5, TL, Salz
    "2-3 Zwiebeln"          → 2–3, –, Zwiebeln
    "1½ Becher Sahne"       → 1.5, Becher, Sahne
    "etwas Pfeffer"         → –, –, Pfeffer, Notiz "etwas"
    "1 Zwiebel, gewürfelt"  → 1, –, Zwiebel, Notiz "gewürfelt"
"""

from __future__ import annotations

from collections.abc import Iterable
import re

from .models import Ingredient
from .units import lookup_unit

UNICODE_FRACTIONS: dict[str, str] = {
    "½": "1/2",
    "⅓": "1/3",
    "⅔": "2/3",
    "¼": "1/4",
    "¾": "3/4",
    "⅕": "1/5",
    "⅖": "2/5",
    "⅗": "3/5",
    "⅘": "4/5",
    "⅙": "1/6",
    "⅚": "5/6",
    "⅛": "1/8",
    "⅜": "3/8",
    "⅝": "5/8",
    "⅞": "7/8",
}

WORD_NUMBERS: dict[str, float] = {
    "ein": 1,
    "eine": 1,
    "einen": 1,
    "einem": 1,
    "einer": 1,
    "eins": 1,
    "zwei": 2,
    "drei": 3,
    "vier": 4,
    "fünf": 5,
    "sechs": 6,
    "sieben": 7,
    "acht": 8,
    "neun": 9,
    "zehn": 10,
    "elf": 11,
    "zwölf": 12,
    "halb": 0.5,
    "halbe": 0.5,
    "halber": 0.5,
    "halbes": 0.5,
    "halben": 0.5,
    "anderthalb": 1.5,
    "eineinhalb": 1.5,
    "zweieinhalb": 2.5,
    "dreieinhalb": 3.5,
}

_NUM = r"\d+(?:[.,]\d+)?"
_FRAC = r"\d+\s*/\s*\d+"
_MIXED = r"\d+\s+\d+\s*/\s*\d+"
_AMOUNT = rf"(?:{_MIXED}|{_FRAC}|{_NUM})"
_RANGE_SEP = r"\s*(?:-|bis|–|—)\s*"

_AMOUNT_RE = re.compile(rf"^(?P<a>{_AMOUNT})(?:{_RANGE_SEP}(?P<b>{_AMOUNT}))?(?=\s|[^\d\s/.,]|$)\s*")

_WORD_AMOUNT_RE = re.compile(
    r"^(?P<w>(?:ein(?:e[rmns]?)?\s+halbe[rnms]?)|"
    + "|".join(sorted((re.escape(w) for w in WORD_NUMBERS), key=len, reverse=True))
    + r")(?=\s)\s*",
    re.IGNORECASE,
)

_APPROX_RE = re.compile(
    r"^(?P<q>ca\.?|circa|cirka|etwa|ungefähr|ungef\.|rund|knapp|gut|max\.?|mind\.?)\s+",
    re.IGNORECASE,
)

_VAGUE_LEAD_RE = re.compile(
    r"^(?P<v>ein\s+wenig|ein\s+paar|einige|etwas|wenig|reichlich|evtl\.?|eventuell|optional:?)\s+",
    re.IGNORECASE,
)

_SPOON_QUALIFIER_RE = re.compile(
    r"^(?P<q>gestr\.?|gestrichene[rnms]?|geh\.?|gehäufte[rnms]?|gut\s+gehäufte[rnms]?|knapp(?:e[rnms]?)?|große[rnms]?|kleine[rnms]?)\s+",
    re.IGNORECASE,
)

_TRAILING_NOTE_RE = re.compile(
    r"\s+(?P<n>nach\s+(?:Geschmack|Belieben|Bedarf)|n\.\s?B\.?|"
    r"zum\s+\w+(?:\s+\w+)?|für\s+(?:die|den|das)\s+\w+|evtl\.?|optional|"
    r"(?:fein\s+|grob\s+)?(?:gehackt|gewürfelt|gerieben|geschnitten))$",
    re.IGNORECASE,
)

_GROUP_HEADER_RE = re.compile(r"^(?:für\s+(?:den|die|das)\s+)?(?P<g>.{1,60}?):\s*$", re.IGNORECASE)


def normalize_text(text: str) -> str:
    """Unicode-Brüche, Striche und Leerraum vereinheitlichen."""
    text = text.replace(" ", " ").replace(" ", " ").replace("⁄", "/")
    out: list[str] = []
    for ch in text:
        if ch in UNICODE_FRACTIONS:
            if out and out[-1].isdigit():
                out.append(" ")
            out.append(UNICODE_FRACTIONS[ch])
        else:
            out.append(ch)
    text = "".join(out)
    text = re.sub(r"[–—‒−]", "-", text)
    text = re.sub(r"^[\s•·*\-–]+(?=\D)", "", text)  # Aufzählungszeichen
    return re.sub(r"\s+", " ", text).strip()


def parse_number(text: str) -> float | None:
    """Zahl, Bruch oder gemischte Zahl → float. "1.000" gilt als Tausend."""
    text = text.strip()
    if not text:
        return None
    low = text.lower()
    if low in WORD_NUMBERS:
        return float(WORD_NUMBERS[low])
    m = re.fullmatch(r"(\d+)\s+(\d+)\s*/\s*(\d+)", text)
    if m:
        den = int(m.group(3))
        return int(m.group(1)) + int(m.group(2)) / den if den else None
    m = re.fullmatch(r"(\d+)\s*/\s*(\d+)", text)
    if m:
        den = int(m.group(2))
        return int(m.group(1)) / den if den else None
    if re.fullmatch(r"\d{1,3}(?:\.\d{3})+", text):  # deutscher Tausenderpunkt
        return float(text.replace(".", ""))
    try:
        return float(text.replace(",", "."))
    except ValueError:
        return None


_PLURAL_MARKER_RE = re.compile(r"(?<=[A-Za-zÄÖÜäöüß])\((?:n|en|e|er|s|es|nen)\)", re.IGNORECASE)


def _extract_parens(text: str) -> tuple[str, list[str]]:
    # Pluralendungen wie "Ei(er)", "Prise(n)", "Zwiebel(n)" entfernen
    text = _PLURAL_MARKER_RE.sub("", text)
    notes: list[str] = []

    def _collect(m: re.Match[str]) -> str:
        inner = m.group(1).strip()
        if inner:
            notes.append(inner)
        return " "

    text = re.sub(r"\(([^()]*)\)", _collect, text)
    text = re.sub(r"\[([^\[\]]*)\]", lambda m: m.group(0) if m.group(1) == "?" else _collect(m), text)
    return re.sub(r"\s+", " ", text).strip(), notes


def parse_ingredient(text: str, group: str | None = None) -> Ingredient:
    """Eine Zutatenzeile zerlegen. Gibt immer ein Ingredient zurück."""
    original = text
    s = normalize_text(text)
    s, notes = _extract_parens(s)
    lead_notes: list[str] = []

    amount: float | None = None
    amount_max: float | None = None
    unit: str | None = None

    m = _APPROX_RE.match(s)
    if m:
        q = m.group("q").lower()
        lead_notes.append("ca." if q.startswith(("ca", "ci", "et", "ung", "ru")) else m.group("q"))
        s = s[m.end() :]

    m = _VAGUE_LEAD_RE.match(s)
    if m:
        lead_notes.append(re.sub(r"\s+", " ", m.group("v").rstrip(":")).lower())
        s = s[m.end() :]
    else:
        m = _AMOUNT_RE.match(s)
        if m:
            amount = parse_number(m.group("a"))
            if m.group("b"):
                amount_max = parse_number(m.group("b"))
            s = s[m.end() :]
        else:
            m = _WORD_AMOUNT_RE.match(s)
            if m:
                word = re.sub(r"\s+", " ", m.group("w").lower())
                amount = 0.5 if " " in word else float(WORD_NUMBERS[word])  # "eine halbe"
                s = s[m.end() :]

    # Qualifizierer vor Löffeln ("1 gestr. TL", "2 gehäufte EL")
    qualifier = None
    m = _SPOON_QUALIFIER_RE.match(s)
    if m:
        rest = s[m.end() :]
        tok = rest.split(" ", 1)[0] if rest else ""
        udef = lookup_unit(tok)
        if udef is not None:
            qualifier = m.group("q")
            s = rest

    # Einheit
    parts = s.split(" ", 1)
    if parts and parts[0]:
        token = parts[0]
        udef = lookup_unit(token.rstrip(","))  # Chefkoch: "1 TL, gestr. Zimt"
        # Ohne Menge nur unbestimmte Einheiten akzeptieren ("Prise Salz"),
        # sonst wäre z. B. "Schale von 1 Zitrone" eine Einheit.
        # Einheit nur, wenn danach noch ein Name folgt.
        if (
            udef is not None
            and (amount is not None or udef.vague or udef.canonical == "Handvoll")
            and len(parts) > 1
            and parts[1].strip()
        ):
            unit = udef.canonical
            s = parts[1].strip()
            if qualifier is None:
                m = _SPOON_QUALIFIER_RE.match(s)
                if m and m.group("q").lower().startswith(("gestr", "geh", "gut", "knapp")):
                    qualifier = m.group("q")
                    s = s[m.end() :]
    if qualifier and unit:
        notes.insert(0, qualifier)
    elif qualifier:
        s = f"{qualifier} {s}"

    # Kommata → Notiz
    name = s
    if "," in name:
        head, tail = name.split(",", 1)
        if head.strip():
            name = head.strip()
            tail = tail.strip()
            if tail:
                notes.append(tail)

    # Trailing-Notizen ("nach Geschmack", "zum Bestreuen", "gehackt")
    while True:
        m = _TRAILING_NOTE_RE.search(name)
        if not m or m.start() == 0:
            break
        notes.insert(0, m.group("n"))
        name = name[: m.start()].strip()

    # Mengenangabe hinten ("Mehl 200 g")
    if amount is None and unit is None and not lead_notes:
        m = re.search(rf"\s+(?P<a>{_AMOUNT})\s*(?P<u>[A-Za-zäöüÄÖÜß.]+)?$", name)
        if m and m.start() > 0:
            udef = lookup_unit(m.group("u")) if m.group("u") else None
            if m.group("u") is None or udef is not None:
                amount = parse_number(m.group("a"))
                unit = udef.canonical if udef else None
                name = name[: m.start()].strip()

    name = name.strip(" ,;:-")
    if not name:
        name = normalize_text(original).strip() or original.strip()
        amount = amount_max = None
        unit = None

    if amount is not None and amount_max is not None and amount_max <= amount:
        amount_max = None

    all_notes = lead_notes + notes
    note = ", ".join(n for n in all_notes if n) or None
    return Ingredient(
        name=name,
        amount=amount,
        amount_max=amount_max,
        unit=unit,
        note=note,
        group=group,
    )


def parse_group_header(line: str) -> str | None:
    """Erkennt Gruppenüberschriften wie "Für den Teig:" → "Teig"."""
    s = normalize_text(line)
    if not s.endswith(":"):
        return None
    m = _GROUP_HEADER_RE.match(s)
    if not m:
        return None
    group = m.group("g").strip()
    # Überschrift darf nicht mit einer Menge beginnen
    if _AMOUNT_RE.match(group):
        return None
    if group.lower().startswith("zutaten"):
        rest = re.sub(r"^zutaten\s*(?:für\s+(?:den|die|das)\s+)?", "", group, flags=re.IGNORECASE)
        return rest.strip() or None
    return group


def parse_ingredient_lines(lines: Iterable[str], group: str | None = None) -> list[Ingredient]:
    """Mehrere Zeilen parsen; Zeilen wie "Für den Teig:" setzen die Gruppe."""
    result: list[Ingredient] = []
    current = group
    for raw in lines:
        if raw is None:
            continue
        line = str(raw).strip()
        if not line:
            continue
        header = parse_group_header(line)
        if header is not None or (line.endswith(":") and len(line) < 60):
            current = header
            continue
        result.append(parse_ingredient(line, current))
    return result
