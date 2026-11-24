"""Auswahl für „Rezept des Tages“ und Ideen-Sensoren.

Gewichtete Zufallsauswahl mit festem Seed pro Zeitraum (Tag bzw. Kalenderwoche):
Innerhalb eines Zeitraums bleibt die Auswahl stabil, danach wechselt sie.

    Gewicht = (Sterne / 5) ^ rating_weight * (1 + Tage seit zuletzt gekocht / 30) ^ recency_weight

- unbewertete Rezepte zählen wie 3 Sterne
- nie gekochte Rezepte zählen wie „vor 60 Tagen gekocht“
- Tage werden bei 365 gedeckelt
"""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
import random
from typing import Any

from .const import PERIOD_WEEKLY

NEUTRAL_STARS = 3.0
NEVER_COOKED_DAYS = 60
MAX_DAYS = 365


def period_id(today: date, period: str) -> str:
    """Kennung des Zeitraums: "2026-11-24" bzw. "2026-W48"."""
    if period == PERIOD_WEEKLY:
        year, week, _ = today.isocalendar()
        return f"{year}-W{week:02d}"
    return today.isoformat()


def _days_since(last_cooked: str | None, today: date) -> int:
    if not last_cooked:
        return NEVER_COOKED_DAYS
    try:
        cooked = datetime.fromisoformat(last_cooked).date()
    except ValueError:
        return NEVER_COOKED_DAYS
    return max(0, min(MAX_DAYS, (today - cooked).days))


def weight(candidate: dict[str, Any], today: date, rating_weight: float, recency_weight: float) -> float:
    """Gewicht eines Rezepts (> 0)."""
    stars = candidate.get("avg_stars") or NEUTRAL_STARS
    rating_part = (float(stars) / 5.0) ** rating_weight
    recency_part = (1 + _days_since(candidate.get("last_cooked"), today) / 30) ** recency_weight
    return max(rating_part * recency_part, 1e-9)


def pick(
    candidates: Sequence[dict[str, Any]],
    *,
    seed: str,
    today: date,
    rating_weight: float,
    recency_weight: float,
) -> dict[str, Any] | None:
    """Deterministische gewichtete Auswahl (gleicher Seed + gleiche Kandidaten → gleiches Ergebnis)."""
    if not candidates:
        return None
    ordered = sorted(candidates, key=lambda c: c["id"])
    weights = [weight(c, today, rating_weight, recency_weight) for c in ordered]
    return random.Random(seed).choices(ordered, weights=weights, k=1)[0]
