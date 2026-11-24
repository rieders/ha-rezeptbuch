"""Tests für Einheiten-Umrechnung, Timer-Erkennung, URL-Normalisierung, Formatierung."""

from __future__ import annotations

import pytest

from custom_components.rezeptbuch.models import Ingredient, VersionData
from custom_components.rezeptbuch.scaling import format_amount, format_ingredient, scale_version
from custom_components.rezeptbuch.timers import detect_timer_seconds
from custom_components.rezeptbuch.units import Quantity, combine_quantities, unit_display
from custom_components.rezeptbuch.url_utils import InvalidUrlError, normalize_url, url_key

# --- Timer -----------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "seconds"),
    [
        ("Im Ofen 20 Minuten backen.", 1200),
        ("1 Std. ruhen lassen", 3600),
        ("ca. 45 Min. köcheln", 2700),
        ("1–2 Stunden gehen lassen", 7200),
        ("1-2 Stunden gehen lassen", 7200),
        ("10 bis 15 Minuten garen", 900),
        ("1 Std. 30 Min. schmoren", 5400),
        ("1 Stunde und 15 Minuten", 4500),
        ("eine halbe Stunde quellen lassen", 1800),
        ("eine Viertelstunde ziehen lassen", 900),
        ("1 1/2 Stunden", 5400),
        ("1½ Stunden", 5400),
        ("30 Sekunden pürieren", 30),
        ("Zuerst 5 Minuten anbraten, dann 25 Minuten köcheln", 1500),
        ("5 min rühren", 300),
        ("bei 180 Grad backen", None),
        ("Mindestens einmal umrühren", None),
        ("Alles vermengen.", None),
        ("", None),
        ("zwanzig Minuten ruhen", 1200),
        ("2 h marinieren", 7200),
    ],
)
def test_detect_timer(text, seconds):
    assert detect_timer_seconds(text) == seconds


# --- Einheiten ---------------------------------------------------------------


def test_combine_mass():
    res = combine_quantities([Quantity(500, "g"), Quantity(1, "kg"), Quantity(250, "g")])
    assert len(res) == 1
    assert res[0].amount == 1.75 and res[0].unit == "kg"


def test_combine_mass_stays_grams():
    res = combine_quantities([Quantity(200, "g"), Quantity(150, "g")])
    assert (res[0].amount, res[0].unit) == (350, "g")


def test_combine_volume():
    res = combine_quantities([Quantity(500, "ml"), Quantity(0.75, "l")])
    assert (res[0].amount, res[0].unit) == (1.25, "l")


def test_combine_spoons():
    res = combine_quantities([Quantity(1, "EL"), Quantity(3, "TL")])
    assert (res[0].amount, res[0].unit) == (2, "EL")
    res = combine_quantities([Quantity(1, "TL"), Quantity(1, "TL")])
    assert (res[0].amount, res[0].unit) == (2, "TL")


def test_combine_spoons_with_ml():
    res = combine_quantities([Quantity(2, "EL"), Quantity(100, "ml")])
    assert (res[0].amount, res[0].unit) == (130, "ml")


def test_combine_count_units_not_mixed():
    res = combine_quantities([Quantity(1, "Dose"), Quantity(2, "Dose"), Quantity(400, "g")])
    as_set = {(q.amount, q.unit) for q in res}
    assert as_set == {(3, "Dose"), (400, "g")}


def test_combine_vague_not_added():
    res = combine_quantities([Quantity(1, "Prise"), Quantity(1, "Prise"), Quantity(None, None, note="etwas")])
    assert len(res) == 2
    assert res[0].unit == "Prise" and res[0].amount is None
    assert res[1].note == "etwas"


def test_combine_vague_dropped_when_concrete_exists():
    res = combine_quantities([Quantity(5, "g"), Quantity(None, None, note="nach Geschmack")])
    assert [(q.amount, q.unit) for q in res] == [(5, "g")]


def test_combine_without_unit_and_ranges():
    res = combine_quantities([Quantity(2, None, 3), Quantity(1, None)])
    assert (res[0].amount, res[0].amount_max, res[0].unit) == (3, 4, None)


def test_unit_plural():
    assert unit_display("Dose", 2) == "Dosen"
    assert unit_display("Dose", 1) == "Dose"
    assert unit_display("g", 200) == "g"
    assert unit_display("Zehe", 3) == "Zehen"


# --- Formatierung / Skalierung ----------------------------------------------


@pytest.mark.parametrize(
    ("value", "text"),
    [(0.5, "½"), (1.5, "1½"), (2.25, "2¼"), (0.75, "¾"), (3, "3"), (1.2, "1,2"), (0.333, "⅓")],
)
def test_format_amount(value, text):
    assert format_amount(value) == text


def test_format_ingredient():
    assert format_ingredient(Ingredient("Mehl", 200, None, "g", "Type 405")) == "200 g Mehl (Type 405)"
    assert format_ingredient(Ingredient("Pfeffer", note="etwas")) == "etwas Pfeffer"
    assert format_ingredient(Ingredient("Zwiebeln", 2, 3)) == "2–3 Zwiebeln"
    assert format_ingredient(Ingredient("Tomaten", 2, None, "Dose")) == "2 Dosen Tomaten"


def test_scale_version():
    data = VersionData(
        servings=4,
        ingredients=[
            Ingredient("Mehl", 250, None, "g"),
            Ingredient("Eier", 3),
            Ingredient("Salz", 1, None, "Prise"),
            Ingredient("Pfeffer", note="etwas"),
        ],
    )
    scaled = scale_version(data, 2)
    assert scaled.servings == 2
    assert [i.amount for i in scaled.ingredients] == [125, 1.5, 0.5, None]
    assert data.ingredients[0].amount == 250  # Original unverändert
    assert scale_version(data, None) is data


# --- URLs ---------------------------------------------------------------------


@pytest.mark.parametrize(
    ("url", "expected"),
    [
        (
            "http://www.chefkoch.de/rezepte/123/Kuchen.html?utm_source=app&utm_medium=share#comments",
            "https://www.chefkoch.de/rezepte/123/Kuchen.html",
        ),
        ("https://www.lecker.de/apfelkuchen-12345.html/", "https://www.lecker.de/apfelkuchen-12345.html"),
        ("www.kochbar.de/rezept/1/x", "https://www.kochbar.de/rezept/1/x"),
        ("https://Example.COM/a?b=2&a=1&fbclid=xyz", "https://example.com/a?a=1&b=2"),
        ("https://example.com/", "https://example.com"),
    ],
)
def test_normalize_url(url, expected):
    assert normalize_url(url) == expected


def test_url_key_ignores_www_and_scheme():
    assert url_key("http://www.chefkoch.de/r/1/") == url_key("https://chefkoch.de/r/1?utm_campaign=x")


@pytest.mark.parametrize("url", ["", "ftp://example.com/x", "https://localhost"])
def test_invalid_url(url):
    with pytest.raises(InvalidUrlError):
        normalize_url(url)
