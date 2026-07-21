from django.db.models import Q
from rapidfuzz import fuzz, process

from MenuOrders.models import Menu, MenuAlias

MATCH_SCORE_MIN = 88
MATCH_LEAD_MARGIN = 12
AMBIGUOUS_SCORE_MIN = 70
AMBIGUOUS_BAND = 12
NO_MATCH_BELOW = 60

MAX_AMBIGUOUS_RESULTS = 4

CATEGORY_TOKEN_SCORE_MIN = 80

# food_type value -> its display name, used to fuzzy-match a spoken category word
# back to one of the 8 fixed categories.
CATEGORY_DISPLAY_TO_VALUE = {label: value for value, label in Menu.FOOD_TYPE_CHOICES}

# Plurals/typos/colloquialisms that plain fuzzy-matching against the 8 display names
# won't reliably catch on its own (either the edit distance is borderline - "desert" vs
# "Dessert" - or the word shares no characters with the category name at all - "drinks"
# vs "Beverage"). Deliberately does NOT include "steak" under grill: the grill category
# also has quail and lamb chops, so "steak" isn't a clean synonym for the whole category.
CATEGORY_SYNONYMS = {
    "appetizer": ["appetizer", "appetizers", "app", "apps", "starter", "starters"],
    "salad": ["salad", "salads", "greens"],
    "pasta": ["pasta", "pastas", "noodles", "noodle"],
    "saute": ["saute", "sautes", "sauteed", "sauté", "sautéed"],
    "grill": ["grill", "grilled"],
    "seafood": ["seafood", "seafoods"],
    "dessert": ["dessert", "desserts", "desert", "deserts", "sweet", "sweets"],
    "beverage": ["beverage", "beverages", "drink", "drinks", "soda"],
}

# Cross-category keyword groups: proteins/ingredients that show up in descriptions
# but not necessarily under a matching food_type (e.g. clam/lobster pasta dishes are
# food_type='pasta', not 'seafood' - their description just names the protein).
CATEGORY_KEYWORDS = {
    "seafood": [
        "seafood", "lobster", "aragosta", "clam", "clams", "vongole", "shrimp",
        "gamberi", "scallop", "scallops", "salmon", "crab", "calamari", "squid",
        "mussel", "mussels", "fish", "branzino", "shellfish",
    ],
}


def _keyword_ids(keywords):
    q = Q()
    for kw in keywords:
        q |= Q(item__icontains=kw) | Q(description__icontains=kw)
    return set(Menu.objects.filter(q).values_list("id", flat=True))


def _ids_for_token(token: str) -> set[int]:
    """All menu ids relevant to a single query word, via explicit category match
    and/or cross-category keyword expansion."""
    ids: set[int] = set()

    matched_food_type = None
    for food_type, synonyms in CATEGORY_SYNONYMS.items():
        if token in synonyms:
            matched_food_type = food_type
            break

    if not matched_food_type:
        best = process.extractOne(token, list(CATEGORY_DISPLAY_TO_VALUE.keys()), scorer=fuzz.WRatio)
        if best and best[1] >= CATEGORY_TOKEN_SCORE_MIN:
            matched_food_type = CATEGORY_DISPLAY_TO_VALUE[best[0]]

    if matched_food_type:
        ids |= set(Menu.objects.filter(food_type=matched_food_type).values_list("id", flat=True))

    for group_name, keywords in CATEGORY_KEYWORDS.items():
        if token == group_name or token in keywords or fuzz.ratio(token, group_name) >= 85:
            ids |= _keyword_ids(keywords)

    return ids


def search_menu_by_category(query: str):
    """Category/keyword browse - e.g. "pasta", "desert", "seafood pasta".

    Each word in the query resolves independently to a set of relevant menu ids
    (its own category match unioned with any keyword-group hits), and multi-word
    queries intersect those per-word sets - so "seafood pasta" narrows down to
    pasta dishes that are actually seafood (clam/lobster pasta), rather than
    returning every pasta item plus every seafood item.
    """
    tokens = [t for t in (query or "").lower().split() if t]
    token_sets = [s for s in (_ids_for_token(t) for t in tokens) if s]

    if not token_sets:
        return Menu.objects.none()

    result_ids = token_sets[0]
    for s in token_sets[1:]:
        result_ids &= s

    return Menu.objects.filter(id__in=result_ids).order_by("food_type", "item")


def _candidates():
    """(menu_id, candidate_text) pairs: each item's name plus every alias."""
    items = Menu.objects.all().prefetch_related("aliases")
    pairs = []
    for menu in items:
        pairs.append((menu.id, menu.item))
        for alias in menu.aliases.all():
            pairs.append((menu.id, alias.alias))
    return pairs


def search_menu(query: str):
    """Search live against the DB (Menu name + MenuAlias) with fuzzy matching.

    Returns a dict shaped as:
      {"match_status": "matched", "item": <Menu>, "score": float}
      {"match_status": "ambiguous", "candidates": [(Menu, score), ...]}
      {"match_status": "no_match"}
    """
    query = (query or "").strip()
    if not query:
        return {"match_status": "no_match"}

    # An exact (case-insensitive) hit on an item's own name or one of its aliases is
    # decisive on its own - it shouldn't get diluted into "ambiguous" just because some
    # unrelated item's alias happens to contain the same words as a substring.
    exact_ids = set(Menu.objects.filter(item__iexact=query).values_list("id", flat=True))
    exact_ids |= set(
        MenuAlias.objects.filter(alias__iexact=query).values_list("menu_id", flat=True)
    )
    if len(exact_ids) == 1:
        menu = Menu.objects.get(id=next(iter(exact_ids)))
        return {"match_status": "matched", "item": menu, "score": 100.0}

    pairs = _candidates()
    if not pairs:
        return {"match_status": "no_match"}

    texts = [text for _, text in pairs]
    results = process.extract(query, texts, scorer=fuzz.WRatio, limit=None)

    best_by_menu: dict[int, float] = {}
    for _text, score, idx in results:
        menu_id = pairs[idx][0]
        if score > best_by_menu.get(menu_id, -1):
            best_by_menu[menu_id] = score

    ranked = sorted(best_by_menu.items(), key=lambda kv: kv[1], reverse=True)
    if not ranked:
        return {"match_status": "no_match"}

    top_id, top_score = ranked[0]
    second_score = ranked[1][1] if len(ranked) > 1 else 0

    if top_score >= MATCH_SCORE_MIN and (top_score - second_score) >= MATCH_LEAD_MARGIN:
        menu = Menu.objects.get(id=top_id)
        return {"match_status": "matched", "item": menu, "score": top_score}

    close = [
        (menu_id, score)
        for menu_id, score in ranked
        if score >= AMBIGUOUS_SCORE_MIN and (top_score - score) <= AMBIGUOUS_BAND
    ]
    if len(close) >= 2:
        menu_map = {m.id: m for m in Menu.objects.filter(id__in=[mid for mid, _ in close])}
        candidates = [(menu_map[mid], score) for mid, score in close[:MAX_AMBIGUOUS_RESULTS]]
        return {"match_status": "ambiguous", "candidates": candidates}

    if top_score >= AMBIGUOUS_SCORE_MIN:
        # A single reasonable-but-not-confident hit: still worth confirming with the caller.
        menu = Menu.objects.get(id=top_id)
        return {"match_status": "matched", "item": menu, "score": top_score}

    if top_score < NO_MATCH_BELOW:
        return {"match_status": "no_match"}

    return {"match_status": "no_match"}
