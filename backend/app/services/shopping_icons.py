"""Deterministic article-to-icon catalogue for the shopping list.

The keys are deliberately presentation-neutral identifiers.  The frontend owns
the SVG artwork while this service owns matching, categories, and safe fallback
behaviour for API clients and meal imports.
"""
from __future__ import annotations

import re
import unicodedata
import hashlib
import hmac

from app.config import settings


ICON_CATEGORIES: dict[str, str] = {
    "apple": "produce", "orange": "produce", "strawberry": "produce", "banana": "produce", "avocado": "produce", "carrot": "produce", "pepper": "produce", "cucumber": "produce", "onion": "produce", "tomato": "produce",
    "salad": "produce", "potato": "produce", "lemon": "produce", "mushroom": "produce",
    "milk": "dairy", "cheese": "dairy", "yogurt": "dairy", "egg": "dairy", "meat": "dairy", "chicken": "dairy", "fish": "dairy",
    "bread": "bakery", "croissant": "bakery",
    "pasta": "pantry", "rice": "pantry", "coffee": "beverage", "water": "beverage",
    "juice": "beverage", "tea": "beverage", "soda": "beverage", "beer": "beverage", "wine": "beverage", "oil": "pantry", "canned": "pantry", "spices": "pantry", "cereal": "pantry", "chocolate": "pantry", "chips": "pantry", "cookies": "pantry",
    "icecream": "frozen", "cleaner": "household", "toilet-paper": "household",
    "laundry": "household", "soap": "household", "toothpaste": "household", "shampoo": "household", "paper-towels": "household", "batteries": "household", "flowers": "household", "pet": "household",
}

_LEGACY_CATEGORY_ICONS = {
    "produce": "carrot", "dairy": "milk", "bakery": "bread", "pantry": "canned",
    "frozen": "icecream", "beverage": "water", "household": "cleaner",
}

# These keys predate the article-level catalogue.  They are safe to improve
# during the one-off data upgrade, unless an account explicitly selected an
# icon for the same title.
LEGACY_GENERIC_ICON_KEYS = frozenset({"shopping", "produce", "dairy", "bakery", "pantry", "frozen", "beverage", "household", "initials"})

# Most specific words come first.  The matching is intentionally local and
# explainable; no remote product catalog or generated image is involved.
_RULES: tuple[tuple[str, tuple[str, ...]], ...] = (
    ("toilet-paper", ("toilettenpapier", "klopapier")),
    ("paper-towels", ("kuchenrolle", "kuchenpapier")),
    ("toothpaste", ("zahnpasta", "zahnburste")),
    ("shampoo", ("shampoo", "conditioner")),
    ("soap", ("seife", "duschgel")),
    ("batteries", ("batterie", "akku")),
    ("flowers", ("blumen", "pflanze")),
    ("laundry", ("waschmittel", "wasche", "waschpulver")),
    ("cleaner", ("reiniger", "spulmittel", "spulmasch", "mullbeutel")),
    ("icecream", ("eiscreme", "speiseeis", "tiefkuhl", "tk ")),
    ("croissant", ("croissant", "brioche", "brotchen")),
    ("bread", ("brot", "toast", "bagel")),
    ("cheese", ("kase", "mozzarella", "parmesan", "feta")),
    ("yogurt", ("joghurt", "skyr", "quark")),
    ("milk", ("milch", "sahne", "butter")),
    ("chicken", ("hahnchen", "huhn", "geflugel")),
    ("fish", ("fisch", "lachs", "thunfisch")),
    ("meat", ("fleisch", "hack", "steak")),
    ("egg", ("ei", "eier")),
    ("pasta", ("nudel", "spaghetti", "penne", "pasta", "lasagne")),
    ("rice", ("reis", "couscous", "quinoa")),
    ("coffee", ("kaffee", "espresso", "cappuccino")),
    ("water", ("wasser", "sprudel")),
    ("juice", ("saft", "smoothie", "limonade")),
    ("tea", ("tee",)),
    ("soda", ("cola", "brause", "limo")),
    ("beer", ("bier",)),
    ("wine", ("wein", "sekt")),
    ("oil", ("ol", "essig")),
    ("canned", ("bohne", "linse", "passata", "tomatenmark", "konserve", "hafer")),
    ("spices", ("salz", "zucker", "gewurz", "pfeffer", "mehl")),
    ("cereal", ("musli", "cerealien", "cornflakes")),
    ("chocolate", ("schokolade", "sussigkeit", "praline")),
    ("chips", ("chips", "snack", "nusse")),
    ("cookies", ("keks",)),
    ("strawberry", ("erdbeere", "himbeere")),
    ("orange", ("orange", "mandarine", "grapefruit")),
    ("apple", ("apfel", "birne", "pfirsich", "kirsche", "beere", "traube")),
    ("banana", ("banane",)),
    ("avocado", ("avocado",)),
    ("pepper", ("paprika",)),
    ("cucumber", ("gurke", "zucchini")),
    ("onion", ("zwiebel", "knoblauch")),
    ("carrot", ("karotte", "mohre", "brokkoli")),
    ("tomato", ("tomate",)),
    ("salad", ("salat", "spinat", "kohl", "gemuse")),
    ("potato", ("kartoffel",)),
    ("lemon", ("zitrone", "limette")),
    ("mushroom", ("pilz", "champignon")),
    ("pet", ("katzen", "hunde", "tierfutter")),
)


def normalize_article_title(title: str) -> str:
    value = unicodedata.normalize("NFKD", title.casefold())
    value = "".join(char for char in value if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", value).strip()


def catalog_term_fingerprint(title: str) -> str:
    """Stable server-only match key; raw private product titles never enter the global catalogue."""
    return hmac.new(settings.APP_JWT_SECRET.encode(), normalize_article_title(title).encode(), hashlib.sha256).hexdigest()


def classify_article(title: str) -> tuple[str, str]:
    value = normalize_article_title(title)
    padded = f" {value} "
    for icon_key, words in _RULES:
        # Very short terms (notably ``Ei``) must be complete words; longer
        # stems intentionally also match compound article names.
        if any((f" {word} " in padded) if len(word) <= 2 else (word in value) for word in words):
            return ICON_CATEGORIES[icon_key], icon_key
    return "other", "initials"


def category_for_icon(icon_key: str) -> str:
    return ICON_CATEGORIES.get(canonical_icon_key(icon_key), "other")


def canonical_icon_key(icon_key: str) -> str:
    """Translate category-key icons emitted by pre-catalogue clients."""
    return _LEGACY_CATEGORY_ICONS.get(icon_key, icon_key)


def is_known_icon(icon_key: str) -> bool:
    return canonical_icon_key(icon_key) in ICON_CATEGORIES
