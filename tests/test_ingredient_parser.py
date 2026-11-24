"""Tests für den deutschen Zutaten-Parser."""

from __future__ import annotations

import pytest

from custom_components.rezeptbuch.ingredient_parser import (
    parse_group_header,
    parse_ingredient,
    parse_ingredient_lines,
    parse_number,
)


@pytest.mark.parametrize(
    ("text", "amount", "amount_max", "unit", "name", "note"),
    [
        ("200 g Mehl", 200, None, "g", "Mehl", None),
        ("200g Mehl", 200, None, "g", "Mehl", None),
        ("1 EL Öl", 1, None, "EL", "Öl", None),
        ("1 El. Öl", 1, None, "EL", "Öl", None),
        ("2 Essl. Zucker", 2, None, "EL", "Zucker", None),
        ("1/2 TL Salz", 0.5, None, "TL", "Salz", None),
        ("½ TL Salz", 0.5, None, "TL", "Salz", None),
        ("1½ TL Zimt", 1.5, None, "TL", "Zimt", None),
        ("1 ½ Tassen Milch", 1.5, None, "Tasse", "Milch", None),
        ("¼ l Milch", 0.25, None, "l", "Milch", None),
        ("¾ Liter Brühe", 0.75, None, "l", "Brühe", None),
        ("1 1/2 kg Kartoffeln", 1.5, None, "kg", "Kartoffeln", None),
        ("2-3 Zwiebeln", 2, 3, None, "Zwiebeln", None),
        ("2 – 3 Zwiebeln", 2, 3, None, "Zwiebeln", None),
        ("2 bis 3 EL Honig", 2, 3, "EL", "Honig", None),
        ("etwas Pfeffer", None, None, None, "Pfeffer", "etwas"),
        ("1 Prise Salz", 1, None, "Prise", "Salz", None),
        ("2 Prisen Muskat", 2, None, "Prise", "Muskat", None),
        ("1 Pck. Backpulver", 1, None, "Pck.", "Backpulver", None),
        ("1 Päckchen Vanillezucker", 1, None, "Pck.", "Vanillezucker", None),
        ("1 Becher Sahne", 1, None, "Becher", "Sahne", None),
        ("1 Becher Schmand (200 g)", 1, None, "Becher", "Schmand", "200 g"),
        ("1 Dose Tomaten, gehackt", 1, None, "Dose", "Tomaten", "gehackt"),
        ("2 Dosen Kidneybohnen", 2, None, "Dose", "Kidneybohnen", None),
        ("3 Zehen Knoblauch", 3, None, "Zehe", "Knoblauch", None),
        ("1 Bund Petersilie", 1, None, "Bund", "Petersilie", None),
        ("1 Würfel Hefe", 1, None, "Würfel", "Hefe", None),
        ("2 Blatt Gelatine", 2, None, "Blatt", "Gelatine", None),
        ("1 Msp. Natron", 1, None, "Msp.", "Natron", None),
        ("500 ml Milch", 500, None, "ml", "Milch", None),
        ("1,5 kg Rinderbraten", 1.5, None, "kg", "Rinderbraten", None),
        ("1.000 g Mehl", 1000, None, "g", "Mehl", None),
        ("0,5 l Wasser", 0.5, None, "l", "Wasser", None),
        ("3 Eier", 3, None, None, "Eier", None),
        ("1 Zwiebel, fein gewürfelt", 1, None, None, "Zwiebel", "fein gewürfelt"),
        ("200 g Mehl (Type 405)", 200, None, "g", "Mehl", "Type 405"),
        ("ca. 500 g Hackfleisch", 500, None, "g", "Hackfleisch", "ca."),
        ("Salz", None, None, None, "Salz", None),
        ("Salz und Pfeffer", None, None, None, "Salz und Pfeffer", None),
        ("Pfeffer nach Geschmack", None, None, None, "Pfeffer", "nach Geschmack"),
        ("Zucker zum Bestreuen", None, None, None, "Zucker", "zum Bestreuen"),
        ("Butter für die Form", None, None, None, "Butter", "für die Form"),
        ("eine Zwiebel", 1, None, None, "Zwiebel", None),
        ("zwei Möhren", 2, None, None, "Möhren", None),
        ("eine halbe Zitrone", 0.5, None, None, "Zitrone", None),
        ("1 gestr. TL Salz", 1, None, "TL", "Salz", "gestr."),
        ("2 gehäufte EL Kakao", 2, None, "EL", "Kakao", "gehäufte"),
        ("1 kleine Zucchini", 1, None, None, "kleine Zucchini", None),
        ("2 Stück Ingwer", 2, None, "Stück", "Ingwer", None),
        ("2 cm Ingwer", 2, None, "cm", "Ingwer", None),
        ("1 Stange Lauch", 1, None, "Stange", "Lauch", None),
        ("4 Scheiben Toastbrot", 4, None, "Scheibe", "Toastbrot", None),
        ("1 Glas Gewürzgurken", 1, None, "Glas", "Gewürzgurken", None),
        ("1 Schuss Weißwein", 1, None, "Schuss", "Weißwein", None),
        ("1 Handvoll Rucola", 1, None, "Handvoll", "Rucola", None),
        ("• 100 g Butter", 100, None, "g", "Butter", None),
        ("- 2 EL Senf", 2, None, "EL", "Senf", None),
        ("100 g Butter, weich", 100, None, "g", "Butter", "weich"),
        ("2 cl Rum", 2, None, "cl", "Rum", None),
        ("4 cl Gin", 4, None, "cl", "Gin", None),
        ("1 Pfund Quark", 1, None, "Pfund", "Quark", None),
        ("125 g Butter (zimmerwarm)", 125, None, "g", "Butter", "zimmerwarm"),
        ("ein paar Blätter Basilikum", None, None, None, "Blätter Basilikum", "ein paar"),
        ("Mehl 200 g", 200, None, "g", "Mehl", None),
        ("3 [?] Eier", 3, None, None, "[?] Eier", None),
        ("1 Liter Milch", 1, None, "l", "Milch", None),
        ("1 l Milch", 1, None, "l", "Milch", None),
        # Eigenheiten echter Chefkoch-Daten
        ("1 Ei(er)", 1, None, None, "Ei", None),
        ("1 Prise(n) Salz", 1, None, "Prise", "Salz", None),
        ("2 Zwiebel(n), rot", 2, None, None, "Zwiebel", "rot"),
        ("1 TL, gestr. Zimt", 1, None, "TL", "Zimt", "gestr."),
        ("5 Birne(n) (z. B. Williams)", 5, None, None, "Birne", "z. B. Williams"),
        ("evtl. Haselnüsse (oder Mandeln)", None, None, None, "Haselnüsse", "evtl., oder Mandeln"),
        ("200 g Margarine oder Butter", 200, None, "g", "Margarine oder Butter", None),
    ],
)
def test_parse_ingredient(text, amount, amount_max, unit, name, note):
    ing = parse_ingredient(text)
    assert ing.amount == pytest.approx(amount) if amount is not None else ing.amount is None
    assert ing.amount_max == pytest.approx(amount_max) if amount_max is not None else ing.amount_max is None
    assert ing.unit == unit
    assert ing.name == name
    assert ing.note == note


def test_unit_needs_name_after_it():
    """'1 EL' allein ergibt keine Einheit ohne Name."""
    ing = parse_ingredient("Lauch")
    assert ing.unit is None and ing.name == "Lauch"
    ing = parse_ingredient("2 Liter")
    assert ing.name == "Liter" and ing.amount == 2


def test_empty_name_falls_back_to_original():
    ing = parse_ingredient("200")
    assert ing.name == "200"
    assert ing.amount is None


@pytest.mark.parametrize(
    ("text", "value"),
    [
        ("1", 1),
        ("1,5", 1.5),
        ("1.5", 1.5),
        ("1/2", 0.5),
        ("1 1/2", 1.5),
        ("2.000", 2000),
        ("drei", 3),
        ("1/0", None),
        ("abc", None),
    ],
)
def test_parse_number(text, value):
    assert parse_number(text) == value


def test_group_headers():
    assert parse_group_header("Für den Teig:") == "Teig"
    assert parse_group_header("Füllung:") == "Füllung"
    assert parse_group_header("Zutaten für die Soße:") == "Soße"
    assert parse_group_header("200 g Mehl") is None
    lines = [
        "Für den Teig:",
        "200 g Mehl",
        "1 Ei",
        "",
        "Für den Belag:",
        "500 g Äpfel",
    ]
    result = parse_ingredient_lines(lines)
    assert [(i.name, i.group) for i in result] == [
        ("Mehl", "Teig"),
        ("Ei", "Teig"),
        ("Äpfel", "Belag"),
    ]
