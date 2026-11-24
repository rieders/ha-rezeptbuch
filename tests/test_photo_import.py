"""Foto-Import über ai_task – komplett gemockt (Antworten als Fixtures), kein echter KI-Aufruf."""

from __future__ import annotations

from collections.abc import AsyncIterator, Callable
from io import BytesIO
import json
from pathlib import Path
import threading
from typing import Any
from unittest.mock import patch

from homeassistant.components.media_source import MediaSourceItem, Unresolvable
from homeassistant.config_entries import ConfigEntryState
from homeassistant.core import HomeAssistant, ServiceCall, SupportsResponse
from homeassistant.exceptions import HomeAssistantError
from PIL import Image
import pytest
from pytest_homeassistant_custom_component.common import MockConfigEntry

from custom_components.rezeptbuch.const import DOMAIN
from custom_components.rezeptbuch.db import Database, categories as cats, drafts, recipes
from custom_components.rezeptbuch.errors import (
    AiTaskEntityNotFound,
    AiTaskFailed,
    InvalidImage,
    NoAiTaskEntity,
    NoPhotos,
)
from custom_components.rezeptbuch.importer.photo import (
    AI_MAX_DIMENSION,
    STRUCTURE,
    WARN_BAD_RESPONSE,
    WARN_NOTHING_RECOGNIZED,
    async_import_photos,
    parse_ai_result,
)
from custom_components.rezeptbuch.media_source import URI_PREFIX, async_get_media_source
from custom_components.rezeptbuch.models import ValidationError
from custom_components.rezeptbuch.runtime import RezeptbuchRuntime
from custom_components.rezeptbuch.storage import Storage
from custom_components.rezeptbuch.timers import parse_minutes_text

AI_FIXTURES = Path(__file__).parent / "fixtures" / "ai"
AI_ENTITY = "ai_task.test_ki"
# Der Test-Mock öffnet Anhänge über diese Referenz – so zählen seine Zugriffe nicht
# beim Mitschneiden der Bildverarbeitung der Integration (Executor-Test).
_TEST_IMAGE_OPEN = Image.open


def ai_fixture(name: str) -> dict[str, Any]:
    return json.loads((AI_FIXTURES / f"{name}.json").read_text(encoding="utf-8"))


def photo(size=(3000, 2000), color=(180, 140, 90)) -> bytes:
    out = BytesIO()
    Image.new("RGB", size, color).save(out, format="JPEG")
    return out.getvalue()


@pytest.fixture
async def db(tmp_path: Path) -> AsyncIterator[Database]:
    database = Database(tmp_path / "rezepte.db")
    await database.async_open()
    await database.run(cats.create_default_tree)
    yield database
    await database.async_close()


@pytest.fixture
def storage(tmp_path: Path) -> Storage:
    s = Storage(tmp_path / "rezeptbuch")
    s.ensure_dirs()
    return s


@pytest.fixture
def runtime(hass: HomeAssistant, db: Database, storage: Storage) -> RezeptbuchRuntime:
    """Geladener Config-Eintrag, damit die Media Source Bilder auflösen kann."""
    entry = MockConfigEntry(domain=DOMAIN, state=ConfigEntryState.LOADED)
    entry.add_to_hass(hass)
    entry.runtime_data = RezeptbuchRuntime(db=db, storage=storage)
    return entry.runtime_data


class FakeAiTask:
    """Ersetzt ai_task.generate_data; prüft Anhänge über unsere Media Source."""

    def __init__(self, hass: HomeAssistant) -> None:
        self.hass = hass
        self.calls: list[dict[str, Any]] = []
        self.attachment_sizes: list[tuple[int, int]] = []
        self.response: dict[str, Any] | Callable[[], Any] = {}

    async def handle(self, call: ServiceCall) -> dict[str, Any]:
        self.calls.append(dict(call.data))
        source = await async_get_media_source(self.hass)
        for att in call.data.get("attachments", []):
            assert att["media_content_id"].startswith(URI_PREFIX)
            item = MediaSourceItem(self.hass, DOMAIN, att["media_content_id"].removeprefix(URI_PREFIX), None)
            play = await source.async_resolve_media(item)
            with _TEST_IMAGE_OPEN(play.path) as img:
                self.attachment_sizes.append(img.size)
        if callable(self.response):
            return self.response()
        return self.response


@pytest.fixture
def fake_ai(hass: HomeAssistant, runtime: RezeptbuchRuntime) -> FakeAiTask:
    fake = FakeAiTask(hass)
    hass.services.async_register("ai_task", "generate_data", fake.handle, supports_response=SupportsResponse.ONLY)
    hass.states.async_set(AI_ENTITY, "unknown")
    return fake


def stored_files(storage: Storage) -> list[Path]:
    return [p for p in storage.images_dir.rglob("*") if p.is_file()]


# --- Erfolgsfälle ---------------------------------------------------------------------


async def test_clean_recipe(hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask) -> None:
    fake_ai.response = ai_fixture("clean")
    result = await async_import_photos(hass, db, storage, [photo()], user_id="anna")
    assert result["status"] == "draft"
    draft = result["draft"]
    assert draft["source_type"] == "photo"
    data = draft["data"]
    assert data["title"] == "Zwetschgenkuchen vom Blech"
    assert data["source_url"] is None
    v = data["version"]
    assert (v["servings"], v["servings_unit"]) == (1, "Blech (ca. 20 Stück)")
    assert (v["prep_time"], v["cook_time"], v["total_time"]) == (30, 40, 70)
    # Zutatenzeilen liefen durch unseren Parser
    ing = {i["name"]: i for i in v["ingredients"]}
    assert (ing["Mehl"]["amount"], ing["Mehl"]["unit"]) == (400, "g")
    assert (ing["Hefe"]["amount"], ing["Hefe"]["unit"]) == (1, "Würfel")
    assert (ing["Salz"]["amount"], ing["Salz"]["unit"]) == (1, "Prise")
    # Schritte ohne Nummerierung, mit Timer-Erkennung
    assert v["steps"][0]["text"].startswith("Hefe in der Milch")
    assert [s["timer_seconds"] for s in v["steps"]] == [None, 2700, None, 2400]
    kuchen = await db.run(lambda c: next(x["id"] for x in cats.list_categories(c) if x["name"] == "Kuchen"))
    assert data["category_ids"] == [kuchen]
    assert result["warnings"] == []
    assert len(draft["image_paths"]) == 1 and data["image_choices"] == draft["image_paths"]
    assert data["image"] is None

    # Aufruf an ai_task
    call = fake_ai.calls[0]
    assert call["entity_id"] == AI_ENTITY
    assert "Erfinde nichts" in call["instructions"] and "[unleserlich]" in call["instructions"]
    assert set(call["structure"]) == set(STRUCTURE)
    assert call["structure"]["ingredients"]["selector"] == {"text": {"multiple": True}}
    assert "amount" not in json.dumps(call["structure"])  # KI soll nicht zerlegen
    # KI bekommt verkleinerte Kopien, gespeichert bleibt das (max. 2400 px) Original
    assert max(fake_ai.attachment_sizes[0]) == AI_MAX_DIMENSION
    assert [p.relative_to(storage.images_dir).as_posix() for p in stored_files(storage)] == draft["image_paths"]
    with Image.open(storage.image_path(draft["image_paths"][0])) as original:
        assert max(original.size) > AI_MAX_DIMENSION


async def test_multipage_order_and_groups(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("multipage")
    pages = [photo(color=(255, 0, 0)), photo(color=(0, 255, 0)), photo(size=(800, 600), color=(0, 0, 255))]
    result = await async_import_photos(hass, db, storage, pages)
    draft = result["draft"]
    assert len(draft["image_paths"]) == 3
    assert len(fake_ai.calls[0]["attachments"]) == 3
    assert "3 Foto(s)" in fake_ai.calls[0]["instructions"]
    # Reihenfolge der Seiten bleibt erhalten (Farbe des gespeicherten Originals)
    colors = []
    for rel in draft["image_paths"]:
        with Image.open(storage.image_path(rel)) as img:
            colors.append(max(range(3), key=lambda i: img.convert("RGB").getpixel((5, 5))[i]))
    assert colors == [0, 1, 2]
    assert fake_ai.attachment_sizes[2] == (800, 600)  # kleine Bilder nicht vergrößert
    groups = [(i["name"], i["group"]) for i in draft["data"]["version"]["ingredients"]]
    assert groups[0] == ("Lauch", "Suppe") and groups[-1] == ("Pfeffer", "Zum Servieren")
    assert draft["data"]["version"]["steps"][1]["timer_seconds"] == 1200


async def test_unreadable_marks_become_warnings(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("unleserlich")
    result = await async_import_photos(hass, db, storage, [photo()])
    assert "3 unleserliche Stellen markiert ([unleserlich]) – bitte prüfen." in result["warnings"]
    assert "Keine Portionsangabe gefunden." in result["warnings"]
    names = [i["name"] for i in result["draft"]["data"]["version"]["ingredients"]]
    assert "[unleserlich] g Butter" in names
    assert result["draft"]["data"]["category_ids"] == []


@pytest.mark.parametrize(
    ("fixture", "expected"),
    [("empty", [WARN_NOTHING_RECOGNIZED]), ("broken", [WARN_BAD_RESPONSE, WARN_NOTHING_RECOGNIZED])],
)
async def test_empty_or_broken_response_gives_draft_with_warning(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask, fixture: str, expected: list[str]
) -> None:
    fake_ai.response = ai_fixture(fixture)
    result = await async_import_photos(hass, db, storage, [photo()])
    assert result["warnings"] == expected
    # Fotos bleiben erhalten, damit das Rezept manuell erfasst werden kann
    assert len(result["draft"]["image_paths"]) == 1
    assert result["draft"]["data"]["version"]["ingredients"] == []


async def test_response_without_data_key(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = {"conversation_id": "x"}
    result = await async_import_photos(hass, db, storage, [photo()])
    assert WARN_NOTHING_RECOGNIZED in result["warnings"]


async def test_similar_title_is_only_a_warning(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    rid = await db.run(recipes.create_recipe, title="Zwetschgen-Kuchen vom Blech", data={})
    fake_ai.response = ai_fixture("clean")
    result = await async_import_photos(hass, db, storage, [photo()])
    assert result["status"] == "draft"
    assert any("Ähnliches Rezept bereits vorhanden" in w and f"ID {rid}" in w for w in result["warnings"])
    assert result["draft"]["data"]["similar_recipes"][0]["id"] == rid


async def test_confirm_photo_draft_with_cover_choice(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("clean")
    result = await async_import_photos(hass, db, storage, [photo(), photo(color=(1, 2, 3))])
    paths = result["draft"]["image_paths"]
    with pytest.raises(ValidationError):
        await db.run(drafts.confirm_draft, result["draft_id"], {"image": "../../secrets.yaml"})
    confirmed = await db.run(drafts.confirm_draft, result["draft_id"], {"image": paths[1]})
    recipe = await db.run(recipes.get_recipe, confirmed["recipe_id"])
    assert recipe["source_type"] == "photo" and recipe["source_url"] is None
    assert recipe["image"] == paths[1]
    kinds = sorted((i["kind"], i["path"]) for i in recipe["images"])
    assert kinds == sorted([("cover", paths[1]), ("source_photo", paths[0]), ("source_photo", paths[1])])
    assert recipe["version"]["is_original"]


# --- ai_task-Entität -----------------------------------------------------------------------


async def test_no_ai_task_service(hass: HomeAssistant, db: Database, storage: Storage) -> None:
    with pytest.raises(NoAiTaskEntity) as err:
        await async_import_photos(hass, db, storage, [photo()])
    assert err.value.translation_key == "no_ai_task_entity"
    assert stored_files(storage) == []


async def test_no_ai_task_entity(hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask) -> None:
    hass.states.async_remove(AI_ENTITY)
    with pytest.raises(NoAiTaskEntity):
        await async_import_photos(hass, db, storage, [photo()])
    assert stored_files(storage) == [] and fake_ai.calls == []


async def test_configured_entity_missing(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    with pytest.raises(AiTaskEntityNotFound) as err:
        await async_import_photos(hass, db, storage, [photo()], ai_task_entity="ai_task.gibts_nicht")
    assert err.value.placeholders == {"entity_id": "ai_task.gibts_nicht"}
    assert stored_files(storage) == []


async def test_multiple_entities_need_choice_or_default(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("clean")
    hass.states.async_set("ai_task.andere_ki", "unknown")
    with pytest.raises(NoAiTaskEntity, match="mehrere"):
        await async_import_photos(hass, db, storage, [photo()])
    # Option gewählt
    await async_import_photos(hass, db, storage, [photo()], ai_task_entity="ai_task.andere_ki")
    assert fake_ai.calls[-1]["entity_id"] == "ai_task.andere_ki"
    # HA-Standard gesetzt (Einstellungen → KI)
    with patch("custom_components.rezeptbuch.importer.photo._preferred_entity", return_value=AI_ENTITY):
        await async_import_photos(hass, db, storage, [photo()])
    assert fake_ai.calls[-1]["entity_id"] == AI_ENTITY


# --- Fehlerfälle ---------------------------------------------------------------------------


async def test_ai_task_error_cleans_up(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    def _fail():
        raise HomeAssistantError("Kontingent erschöpft")

    fake_ai.response = _fail
    with pytest.raises(AiTaskFailed, match="Kontingent"):
        await async_import_photos(hass, db, storage, [photo(), photo()])
    assert stored_files(storage) == []
    assert await db.run(drafts.list_drafts) == []


async def test_invalid_photo_cleans_up(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    with pytest.raises(InvalidImage):
        await async_import_photos(hass, db, storage, [photo(), b"kein bild"])
    assert stored_files(storage) == [] and fake_ai.calls == []


async def test_no_photos(hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask) -> None:
    with pytest.raises(NoPhotos):
        await async_import_photos(hass, db, storage, [])
    with pytest.raises(NoPhotos):
        await async_import_photos(hass, db, storage, [b"x"] * 11)


async def test_ai_copies_are_always_deleted(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("clean")
    result = await async_import_photos(hass, db, storage, [photo(), photo()])
    files = sorted(p.relative_to(storage.images_dir).as_posix() for p in stored_files(storage))
    assert files == sorted(result["draft"]["image_paths"])


async def test_photo_processing_runs_in_executor(
    hass: HomeAssistant, db: Database, storage: Storage, fake_ai: FakeAiTask
) -> None:
    fake_ai.response = ai_fixture("clean")
    pages = [photo(), photo()]  # Testbilder vor dem Mitschneiden erzeugen
    calls: list[tuple[str, int]] = []
    real_open, real_save = Image.open, Image.Image.save

    def _open(*args, **kwargs):
        calls.append(("open", threading.get_ident()))
        return real_open(*args, **kwargs)

    def _save(self, *args, **kwargs):
        calls.append(("save", threading.get_ident()))
        return real_save(self, *args, **kwargs)

    loop_thread = threading.get_ident()
    with patch.object(Image, "open", _open), patch.object(Image.Image, "save", _save):
        await async_import_photos(hass, db, storage, pages)
    # Speichern der Originale + KI-Kopien: open/verify/thumbnail/save
    assert {n for n, _ in calls} >= {"open", "save"}
    assert all(t != loop_thread for _, t in calls), calls


# --- Media Source ---------------------------------------------------------------------------


async def test_media_source_rejects_traversal_and_missing(hass: HomeAssistant, runtime: RezeptbuchRuntime) -> None:
    source = await async_get_media_source(hass)
    for ident in ("../rezepte.db", "ab/gibt-es-nicht.jpg"):
        with pytest.raises(Unresolvable):
            await source.async_resolve_media(MediaSourceItem(hass, DOMAIN, ident, None))


async def test_media_source_without_loaded_entry(hass: HomeAssistant) -> None:
    source = await async_get_media_source(hass)
    with pytest.raises(Unresolvable):
        await source.async_resolve_media(MediaSourceItem(hass, DOMAIN, "ab/x.jpg", None))


# --- Hilfsfunktionen -----------------------------------------------------------------------


@pytest.mark.parametrize(
    ("text", "minutes"),
    [
        ("20 Min.", 20),
        ("ca. 40 Minuten", 40),
        ("1 Std. 30 Min.", 90),
        ("1–2 Stunden", 120),
        ("45", 45),
        ("PT1H", 60),
        ("", None),
        ("[unleserlich]", None),
        (None, None),
    ],
)
def test_parse_minutes_text(text, minutes):
    assert parse_minutes_text(text) == minutes


def test_parse_ai_result_tolerates_decomposed_and_string_lists():
    fields, warnings = parse_ai_result(
        {
            "title": "Test",
            "servings": 4,
            "ingredients": [{"amount": "200", "unit": "g", "name": "Mehl"}, "1 Ei"],
            "steps": "1. Rühren.\n2. Backen.",
        }
    )
    assert [i.name for i in fields["version"].ingredients] == ["Mehl", "Ei"]
    assert fields["version"].ingredients[0].amount == 200
    assert [s.text for s in fields["version"].steps] == ["Rühren.", "Backen."]
    assert fields["version"].servings == 4
    assert warnings == []
