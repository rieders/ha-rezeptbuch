"""Rezept-Import per URL.

Ablauf (async_import_url):
1. URL normalisieren, Duplikat prüfen (source_key) → ggf. vorhandene recipe_id
2. HTML sicher abrufen (net.async_safe_get: SSRF-Schutz, Timeout, Größenlimit)
3. Im Executor parsen: recipe-scrapers (supported_only=False) + eigener
   JSON-LD-Parser zum Ergänzen/als Fallback
4. Nach Weiterleitung/kanonischer URL erneut Duplikat prüfen
5. Bild herunterladen und lokal speichern
6. Kategorien/Tags zuordnen, Entwurf (import_drafts) speichern
Erst confirm_draft legt Rezept + Version 1 „Original“ an.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass, field
import logging
import re
from typing import Any
from urllib.parse import urlsplit

from homeassistant.core import HomeAssistant
from recipe_scrapers import scrape_html

from ..const import SOURCE_URL
from ..db import Database
from ..db.drafts import create_draft, get_draft
from ..db.recipes import find_duplicates
from ..errors import InvalidUrl, NoRecipeFound, RezeptbuchError
from ..images import async_download_image
from ..ingredient_parser import parse_ingredient, parse_ingredient_lines
from ..models import Step, VersionData
from ..net import async_safe_get, parse_http_url
from ..storage import Storage
from ..timers import detect_timer_seconds
from ..url_utils import normalize_url
from .jsonld import clean_text, normalize_yield_unit, parse_recipe_jsonld, parse_yield
from .mapping import map_keywords

_LOGGER = logging.getLogger(__name__)

WARN_NO_INGREDIENTS = "Keine Zutaten gefunden – bitte ergänzen."
WARN_NO_STEPS = "Keine Zubereitungsschritte gefunden – bitte ergänzen."
WARN_NO_SERVINGS = "Keine Portionsangabe gefunden."
WARN_NO_IMAGE = "Bild konnte nicht geladen werden."


@dataclass
class ScrapedRecipe:
    """Geparstes Rezept (noch ohne DB-Bezug)."""

    title: str
    source_url: str
    data: VersionData
    description: str | None = None
    image_url: str | None = None
    categories: list[str] = field(default_factory=list)
    keywords: list[str] = field(default_factory=list)
    author: str | None = None
    site_name: str | None = None
    parser: str = "recipe-scrapers"
    warnings: list[str] = field(default_factory=list)


def _safe[T](func: Callable[[], T], default: T | None = None) -> T | None:
    """recipe-scrapers wirft je nach Seite unterschiedliche Exceptions pro Feld."""
    try:
        value = func()
    except Exception as err:
        _LOGGER.debug("recipe-scrapers: Feld nicht verfügbar (%s)", err)
        return default
    return value if value not in (None, "", []) else default


def _from_scraper(html: str, url: str) -> dict[str, Any] | None:
    try:
        scraper = scrape_html(html, org_url=url, supported_only=False)
    except Exception as err:
        _LOGGER.debug("recipe-scrapers konnte %s nicht lesen: %s", url, err)
        return None
    groups = _safe(scraper.ingredient_groups) or []
    ingredients: list[tuple[str, str | None]] = []
    if len(groups) > 1 or (groups and groups[0].purpose):
        for group in groups:
            ingredients.extend((i, clean_text(group.purpose) or None) for i in group.ingredients)
    else:
        ingredients = [(i, None) for i in _safe(scraper.ingredients) or []]
    yields = _safe(scraper.yields)
    servings, servings_unit = parse_yield(yields) if yields else (None, None)
    keywords = _safe(scraper.keywords) or []
    category = _safe(scraper.category) or ""
    return {
        "title": clean_text(_safe(scraper.title)),
        "description": clean_text(_safe(scraper.description)),
        "image": _safe(scraper.image),
        "ingredients": [(clean_text(i), g) for i, g in ingredients if clean_text(i)],
        "instructions": [
            {"text": clean_text(t), "group": None} for t in _safe(scraper.instructions_list) or [] if clean_text(t)
        ],
        "servings": servings,
        "servings_unit": servings_unit,
        "prep_time": _safe(scraper.prep_time),
        "cook_time": _safe(scraper.cook_time),
        "total_time": _safe(scraper.total_time),
        "categories": [c.strip() for c in str(category).split(",") if c.strip()],
        "keywords": keywords if isinstance(keywords, list) else [str(keywords)],
        "author": clean_text(_safe(scraper.author)) or None,
        "site_name": clean_text(_safe(scraper.site_name)) or None,
        "canonical_url": _safe(scraper.canonical_url),
    }


def _minutes(value: Any) -> int | None:
    try:
        minutes = round(float(value))
    except (TypeError, ValueError):
        return None
    return minutes if minutes > 0 else None


def _clean_title(title: str, author: str | None) -> str:
    """Chefkoch hängt " von <Autor>" an den Rezeptnamen an."""
    title = " ".join(title.split())
    if author:
        suffix = f" von {author}"
        if title.lower().endswith(suffix.lower()) and len(title) > len(suffix) + 2:
            title = title[: -len(suffix)].rstrip()
    return title


def parse_html(html: str, url: str) -> ScrapedRecipe:
    """HTML → ScrapedRecipe. Blockierend (BeautifulSoup) → im Executor aufrufen."""
    primary = _from_scraper(html, url)
    fallback = parse_recipe_jsonld(html, url)
    if primary is None and fallback is None:
        raise NoRecipeFound("Auf der Seite wurde kein Rezept gefunden", url=url)

    def pick(key: str) -> Any:
        for source in (primary, fallback):
            if source and source.get(key) not in (None, "", []):
                return source[key]
        return None

    parser = "recipe-scrapers"
    has_primary_content = primary is not None and bool(primary.get("ingredients") or primary.get("instructions"))
    if not has_primary_content:
        parser = "json-ld"

    # Zutaten: recipe-scrapers (mit Gruppen) bevorzugt, sonst JSON-LD
    if primary and primary.get("ingredients"):
        ingredient_list = [parse_ingredient(text, group) for text, group in primary["ingredients"]]
    else:
        ingredient_list = parse_ingredient_lines((fallback or {}).get("ingredients") or [])

    instructions = pick("instructions") or []
    # JSON-LD hat oft die Gruppen der HowToSections – übernehmen, wenn Texte gleich sind
    if fallback and primary and primary.get("instructions") and fallback.get("instructions"):
        fb = fallback["instructions"]
        if [s["text"] for s in fb] == [s["text"] for s in instructions] or len(instructions) <= 1 < len(fb):
            instructions = fb
    # Eine einzige gemeinsame Gruppe ("Zubereitung") ist keine echte Gruppierung
    if len({s.get("group") for s in instructions}) == 1:
        instructions = [{**s, "group": None} for s in instructions]
    steps = [
        Step(text=s["text"], timer_seconds=detect_timer_seconds(s["text"]), group=s.get("group")) for s in instructions
    ]

    # Portionen: JSON-LD liefert die Originalangabe ("4 Portionen", "12 Stück")
    servings = (fallback or {}).get("servings") or (primary or {}).get("servings")
    servings_unit = (fallback or {}).get("servings_unit") or (primary or {}).get("servings_unit")

    author = pick("author")
    title = _clean_title(pick("title") or "", author)
    if not title and not ingredient_list and not steps:
        raise NoRecipeFound("Auf der Seite wurde kein Rezept gefunden", url=url)

    data = VersionData(
        servings=servings,
        servings_unit=normalize_yield_unit(servings_unit),
        prep_time=_minutes(pick("prep_time")),
        cook_time=_minutes(pick("cook_time")),
        total_time=_minutes(pick("total_time")),
        ingredients=ingredient_list,
        steps=steps,
    )
    if data.total_time is None and (data.prep_time or data.cook_time):
        data.total_time = (data.prep_time or 0) + (data.cook_time or 0)

    warnings: list[str] = []
    if not title:
        title = urlsplit(url).netloc
        warnings.append("Kein Titel gefunden.")
    if not ingredient_list:
        warnings.append(WARN_NO_INGREDIENTS)
    if not steps:
        warnings.append(WARN_NO_STEPS)
    if not servings:
        warnings.append(WARN_NO_SERVINGS)
    if any("[?]" in i.name for i in ingredient_list):
        warnings.append("Einige Zutaten enthalten unleserliche Stellen [?].")

    canonical = pick("canonical_url")
    return ScrapedRecipe(
        title=title,
        source_url=_choose_url(url, canonical),
        data=data,
        description=pick("description") or None,
        image_url=pick("image"),
        categories=list((primary or {}).get("categories") or (fallback or {}).get("categories") or []),
        keywords=list(pick("keywords") or []),
        author=author,
        site_name=(primary or {}).get("site_name"),
        parser=parser,
        warnings=warnings,
    )


def _choose_url(fetched_url: str, canonical: str | None) -> str:
    """Kanonische URL nur übernehmen, wenn sie zum selben Host gehört."""
    if canonical and isinstance(canonical, str):
        try:
            a = urlsplit(fetched_url).hostname or ""
            b = urlsplit(canonical).hostname or ""
        except ValueError:
            return fetched_url
        strip = re.compile(r"^(www\d?|m)\.")
        if b and strip.sub("", a) == strip.sub("", b):
            return canonical
    return fetched_url


async def async_import_url(
    hass: HomeAssistant,
    db: Database,
    storage: Storage,
    url: str,
    *,
    user_id: str | None = None,
    category_ids: list[int] | None = None,
    tags: list[str] | None = None,
    allow_duplicate: bool = False,
) -> dict[str, Any]:
    """URL importieren → Entwurf oder Duplikat-Hinweis.

    Rückgabe:
        {"status": "duplicate", "recipe_id", "title", "source_url"}
        {"status": "draft", "draft_id", "draft", "warnings"}
    Fehler: InvalidUrl, BlockedAddress, FetchFailed, NoRecipeFound.
    """
    url = (url or "").strip()
    try:
        normalized = normalize_url(url)
    except ValueError as err:
        raise InvalidUrl(f"Ungültige URL: {url}", url=url) from err
    # Abgerufen wird die eingegebene URL (nur Schema ergänzt, Fragment entfernt);
    # die normalisierte Form dient ausschließlich dem Duplikat-Vergleich.
    fetch_url = (url if "://" in url else f"https://{url}").split("#", 1)[0]
    parse_http_url(fetch_url)

    if not allow_duplicate and (dup := await _async_duplicate(db, normalized)):
        return dup

    page = await async_safe_get(hass, fetch_url)
    scraped = await hass.async_add_executor_job(parse_html, page.text(), page.url)
    scraped.source_url = normalize_url(scraped.source_url)

    if not allow_duplicate and (dup := await _async_duplicate(db, scraped.source_url)):
        return dup

    image_path: str | None = None
    if scraped.image_url:
        try:
            image_path = await async_download_image(hass, storage, scraped.image_url)
        except RezeptbuchError as err:
            _LOGGER.info("Rezeptbild %s nicht geladen: %s", scraped.image_url, err)
            scraped.warnings.append(WARN_NO_IMAGE)

    def _save(conn) -> int:
        mapping = map_keywords(conn, scraped.categories, scraped.keywords)
        final_ids = list(dict.fromkeys([*mapping.category_ids, *(category_ids or [])]))
        final_tags = list(dict.fromkeys([*mapping.tags, *(tags or [])]))
        draft = {
            "title": scraped.title,
            "description": scraped.description,
            "source_url": scraped.source_url,
            "image": image_path,
            "version": scraped.data.to_dict(),
            "category_ids": final_ids,
            "tags": final_tags,
            "warnings": scraped.warnings,
            "source": {
                "categories": mapping.primary_keywords,
                "keywords": scraped.keywords,
                "matched": mapping.matched,
                "suggested_category_ids": final_ids,
                "parser": scraped.parser,
                "site_name": scraped.site_name,
                "author": scraped.author,
                "image_url": scraped.image_url,
            },
        }
        return create_draft(conn, SOURCE_URL, draft, user_id=user_id)

    draft_id = await db.run(_save)
    draft = await db.run(get_draft, draft_id)
    return {"status": "draft", "draft_id": draft_id, "draft": draft, "warnings": scraped.warnings}


async def _async_duplicate(db: Database, url: str) -> dict[str, Any] | None:
    dups = await db.run(find_duplicates, url)
    if not dups:
        return None
    return {
        "status": "duplicate",
        "recipe_id": dups[0]["id"],
        "title": dups[0]["title"],
        "source_url": dups[0]["source_url"],
    }
