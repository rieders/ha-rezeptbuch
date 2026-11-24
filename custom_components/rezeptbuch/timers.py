"""Erkennt Zeitangaben in Schritttexten ("20 Minuten", "1 Std.", "1–2 Stunden")."""

from __future__ import annotations

import re

from .ingredient_parser import normalize_text, parse_number

_NUM_WORDS = (
    "eineinhalb|anderthalb|zweieinhalb|halbe|halben|einer|einen|eine|ein|zwei|drei|vier|"
    "fünf|sechs|sieben|acht|neun|zehn|fünfzehn|zwanzig|dreißig|vierzig|fünfzig|sechzig"
)
_WORD_VALUES = {
    "eineinhalb": 1.5,
    "anderthalb": 1.5,
    "zweieinhalb": 2.5,
    "halbe": 0.5,
    "halben": 0.5,
    "fünfzehn": 15,
    "zwanzig": 20,
    "dreißig": 30,
    "vierzig": 40,
    "fünfzig": 50,
    "sechzig": 60,
}
_NUM = rf"(?:\d+\s+\d+/\d+|\d+/\d+|\d+(?:[.,]\d+)?|{_NUM_WORDS})"
_UNIT = r"(?P<unit>Stunden|Stunde|Std\.?|h|Minuten|Minute|Min\.?|min|Sekunden|Sekunde|Sek\.?|sek)"

_DURATION_RE = re.compile(
    rf"(?<![\w/])(?P<a>{_NUM})(?:\s*(?:-|bis)\s*(?P<b>{_NUM}))?\s*{_UNIT}(?![A-Za-zÄÖÜäöüß])",
    re.IGNORECASE,
)
_SPECIAL = {
    "viertelstunde": 900,
    "dreiviertelstunde": 2700,
    "halbe stunde": 1800,
}
_JOINER_RE = re.compile(r"^\s*(?:,|und|u\.)?\s*$", re.IGNORECASE)


def _value(text: str) -> float | None:
    low = text.lower().strip()
    if low in _WORD_VALUES:
        return float(_WORD_VALUES[low])
    return parse_number(text)


def _unit_seconds(unit: str) -> int:
    u = unit.lower()
    if u.startswith(("std", "stunde")) or u == "h":
        return 3600
    if u.startswith("min"):
        return 60
    return 1


def detect_timer_seconds(text: str | None) -> int | None:
    """Timer-Dauer (Sekunden) aus einem Schritttext; Bereiche → Obergrenze.

    Mehrere Angaben: aufeinanderfolgende "1 Std. 30 Min." werden addiert,
    ansonsten gewinnt die längste Angabe.
    """
    if not text:
        return None
    s = normalize_text(text)
    candidates: list[int] = []

    matches = list(_DURATION_RE.finditer(s))
    i = 0
    while i < len(matches):
        m = matches[i]
        value = _value(m.group("b") or m.group("a"))
        if value is None or value <= 0:
            i += 1
            continue
        unit_s = _unit_seconds(m.group("unit"))
        total = value * unit_s
        # "1 Std. 30 Min." / "1 Stunde und 15 Minuten"
        while i + 1 < len(matches):
            nxt = matches[i + 1]
            between = s[m.end() : nxt.start()]
            nxt_unit = _unit_seconds(nxt.group("unit"))
            if _JOINER_RE.match(between) and nxt_unit < unit_s:
                nval = _value(nxt.group("b") or nxt.group("a")) or 0
                total += nval * nxt_unit
                m = nxt
                unit_s = nxt_unit
                i += 1
            else:
                break
        candidates.append(round(total))
        i += 1

    low = s.lower()
    for phrase, seconds in _SPECIAL.items():
        if phrase in low:
            candidates.append(seconds)

    if not candidates:
        return None
    return max(candidates)
