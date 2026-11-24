"""Konstanten für die Rezeptbuch-Integration."""

from __future__ import annotations

from typing import Final

DOMAIN: Final = "rezeptbuch"
NAME: Final = "Rezeptbuch"

# Speicherorte (relativ zum HA-Config-Verzeichnis)
DEFAULT_STORAGE_DIR: Final = "rezeptbuch"
DB_FILENAME: Final = "rezepte.db"
IMAGES_DIRNAME: Final = "images"

# Config-/Options-Schlüssel
CONF_CREATE_DEFAULT_CATEGORIES: Final = "create_default_categories"
CONF_AI_TASK_ENTITY: Final = "ai_task_entity"
CONF_DEFAULT_SERVINGS: Final = "default_servings"
CONF_STORAGE_PATH: Final = "storage_path"
CONF_DAILY_CATEGORY_IDS: Final = "daily_category_ids"
CONF_RATING_WEIGHT: Final = "rating_weight"
CONF_RECENCY_WEIGHT: Final = "recency_weight"
CONF_IDEA_SENSORS: Final = "idea_sensors"
CONF_ALLOW_PRIVATE_NETWORKS: Final = "allow_private_networks"
# Marker in entry.data: Standardbaum wurde bereits angelegt (nur beim ersten Setup)
DATA_DEFAULT_CATEGORIES_CREATED: Final = "default_categories_created"

# Ideen-Sensoren (Options-Flow): Liste von {"id", "name", "category_id", "period"}
IDEA_ID: Final = "id"
IDEA_NAME: Final = "name"
IDEA_CATEGORY_ID: Final = "category_id"
IDEA_PERIOD: Final = "period"
PERIOD_DAILY: Final = "daily"
PERIOD_WEEKLY: Final = "weekly"
PERIODS: Final = (PERIOD_DAILY, PERIOD_WEEKLY)

DEFAULT_SERVINGS: Final = 4
DEFAULT_RATING_WEIGHT: Final = 2.0
DEFAULT_RECENCY_WEIGHT: Final = 1.0
DEFAULT_ALLOW_PRIVATE_NETWORKS: Final = False

# Zeitsteuerung
CLEANUP_FIRST_RUN_DELAY: Final = 15 * 60  # Sekunden nach dem Start
CLEANUP_HOUR: Final = 3
CLEANUP_MINUTE: Final = 30

# Signale / URLs
SIGNAL_SHOPPING_UPDATED: Final = f"{DOMAIN}_shopping_updated"
IMAGE_URL_PREFIX: Final = f"/api/{DOMAIN}/image/"

# Quellen / Arten
SOURCE_URL: Final = "url"
SOURCE_PHOTO: Final = "photo"
SOURCE_MANUAL: Final = "manual"
SOURCE_TYPES: Final = (SOURCE_URL, SOURCE_PHOTO, SOURCE_MANUAL)

IMAGE_COVER: Final = "cover"
IMAGE_SOURCE_PHOTO: Final = "source_photo"
IMAGE_COOK_PHOTO: Final = "cook_photo"
IMAGE_KINDS: Final = (IMAGE_COVER, IMAGE_SOURCE_PHOTO, IMAGE_COOK_PHOTO)

TARGET_INGREDIENT: Final = "ingredient"
TARGET_STEP: Final = "step"
TARGET_RECIPE: Final = "recipe"
ANNOTATION_TARGETS: Final = (TARGET_INGREDIENT, TARGET_STEP, TARGET_RECIPE)

# Benutzer für Aufrufe ohne HA-Benutzer (z. B. Automationen)
SYSTEM_USER_ID: Final = "system"
SYSTEM_USER_NAME: Final = "System"

ORIGINAL_LABEL: Final = "Original"
DEFAULT_VERSION_LABEL: Final = "Meine Version"

MIN_STARS: Final = 0.5
MAX_STARS: Final = 5.0

# Standard-Kategoriebaum: (Name, Icon, Farbe, Unterkategorien)
DEFAULT_CATEGORY_TREE: Final = (
    (
        "Kochen",
        "mdi:pot-steam",
        "#e65100",
        (
            ("Suppen & Eintöpfe", "mdi:pot-mix"),
            ("Fleisch", "mdi:food-steak"),
            ("Fisch", "mdi:fish"),
            ("Vegetarisch", "mdi:leaf"),
            ("Beilagen", "mdi:rice"),
            ("Saucen", "mdi:soy-sauce"),
            ("Salate", "mdi:bowl-mix"),
        ),
    ),
    (
        "Backen",
        "mdi:muffin",
        "#8d6e63",
        (
            ("Kuchen", "mdi:cake-variant"),
            ("Torten", "mdi:cake-layered"),
            ("Brot & Brötchen", "mdi:bread-slice"),
            ("Plätzchen", "mdi:cookie"),
            ("Herzhaftes Gebäck", "mdi:baguette"),
        ),
    ),
    (
        "Getränke",
        "mdi:glass-cocktail",
        "#1e88e5",
        (
            ("Cocktails", "mdi:glass-cocktail"),
            ("Alkoholfrei", "mdi:cup-water"),
            ("Heißgetränke", "mdi:coffee"),
            ("Smoothies", "mdi:blender"),
            ("Liköre", "mdi:bottle-wine"),
        ),
    ),
)
