"""Tests für den eigenen JSON-LD-Fallback-Parser."""

from __future__ import annotations

import json

import pytest

from custom_components.rezeptbuch.importer.jsonld import (
    clean_text,
    parse_duration_minutes,
    parse_recipe_jsonld,
    parse_yield,
)


def page(*objects, raw: str | None = None) -> str:
    scripts = "".join(
        f'<script type="application/ld+json">{json.dumps(o, ensure_ascii=False)}</script>' for o in objects
    )
    if raw:
        scripts += f'<script type="application/ld+json">{raw}</script>'
    return f"<html><head>{scripts}</head><body></body></html>"


@pytest.mark.parametrize(
    ("value", "minutes"),
    [
        ("PT30M", 30),
        ("PT1H15M", 75),
        ("P0DT1H20M", 80),
        ("PT90M", 90),
        ("PT0.5H", 30),
        ("P1D", 1440),
        ("PT45S", 1),
        (25, 25),
        ("40", 40),
        ("PT0M", None),
        ("", None),
        (None, None),
        ("ca. 30 Minuten", None),
    ],
)
def test_parse_duration(value, minutes):
    assert parse_duration_minutes(value) == minutes


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (["4", "4 Portionen"], (4, "Portionen")),
        ("4 servings", (4, "Portionen")),
        ("12 Stück", (12, "Stück")),
        ("1 Springform (26 cm)", (1, "Springform (26 cm)")),
        (6, (6, None)),
        ("2-3 Personen", (2, "Portionen")),
        ("0", (None, None)),
        (None, (None, None)),
    ],
)
def test_parse_yield(value, expected):
    assert parse_yield(value) == expected


def test_clean_text():
    assert clean_text("Salz &amp; Pfeffer") == "Salz & Pfeffer"
    assert clean_text("<p>Teig <b>kneten</b></p>") == "Teig kneten"
    assert clean_text("Zeile 1<br/>Zeile 2") == "Zeile 1\nZeile 2"
    assert clean_text(None) == ""


def test_graph_with_id_references():
    html = page(
        {
            "@context": "https://schema.org",
            "@graph": [
                {
                    "@type": "Recipe",
                    "name": "Test",
                    "image": {"@id": "#img"},
                    "author": {"@id": "#me"},
                    "recipeIngredient": ["200 g Mehl"],
                    "recipeInstructions": [
                        {
                            "@type": "HowToSection",
                            "name": "Teig",
                            "itemListElement": [{"@type": "HowToStep", "text": "Kneten."}],
                        },
                        {
                            "@type": "HowToSection",
                            "name": "Belag",
                            "itemListElement": [{"@type": "HowToStep", "text": "Belegen."}],
                        },
                    ],
                },
                {"@type": "ImageObject", "@id": "#img", "url": "/bild.jpg"},
                {"@type": "Person", "@id": "#me", "name": "Koch"},
            ],
        }
    )
    r = parse_recipe_jsonld(html, "https://example.org/rezept")
    assert r["image"] == "https://example.org/bild.jpg"
    assert r["author"] == "Koch"
    assert r["instructions"] == [{"text": "Kneten.", "group": "Teig"}, {"text": "Belegen.", "group": "Belag"}]


def test_type_list_and_main_entity():
    html = page({"@type": "WebPage", "mainEntity": {"@type": ["Recipe", "NewsArticle"], "name": "Verschachtelt"}})
    assert parse_recipe_jsonld(html, "https://example.org")["title"] == "Verschachtelt"


def test_instructions_as_string_and_list_of_strings():
    html = page({"@type": "Recipe", "name": "A", "recipeInstructions": "Schritt eins.\nSchritt zwei."})
    assert [s["text"] for s in parse_recipe_jsonld(html, "https://x.org")["instructions"]] == [
        "Schritt eins.",
        "Schritt zwei.",
    ]
    html = page({"@type": "Recipe", "name": "A", "recipeInstructions": ["Eins", "Zwei"]})
    assert [s["text"] for s in parse_recipe_jsonld(html, "https://x.org")["instructions"]] == ["Eins", "Zwei"]


def test_broken_and_wrapped_json_is_tolerated():
    html = (
        page(raw='<!-- {"@type": "Recipe", "name": "Kommentiert", "recipeIngredient": "1 Ei"} -->')
        + '<script type="application/ld+json">{kaputt</script>'
    )
    r = parse_recipe_jsonld(html, "https://x.org")
    assert r["title"] == "Kommentiert" and r["ingredients"] == ["1 Ei"]


def test_no_recipe_returns_none():
    assert parse_recipe_jsonld(page({"@type": "Article", "headline": "x"}), "https://x.org") is None
    assert parse_recipe_jsonld("<html></html>", "https://x.org") is None


def test_keywords_and_categories():
    html = page(
        {"@type": "Recipe", "name": "A", "keywords": ["Sommer", "Grillen"], "recipeCategory": "Hauptgericht, Fleisch"}
    )
    r = parse_recipe_jsonld(html, "https://x.org")
    assert r["keywords"] == ["Sommer", "Grillen"]
    assert r["categories"] == ["Hauptgericht", "Fleisch"]
