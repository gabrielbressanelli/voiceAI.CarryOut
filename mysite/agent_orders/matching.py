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
    # "grilled" is a prep-method word, not a promise the dish lives in the 'grill'
    # food_type - "Grilled Shrimp" is an Appetizer, "Grilled Salmon Arugula" is a
    # Salad, "Branzino" (Seafood) is grilled as its actual main preparation. Without
    # this, "grilled shrimp" resolved to empty: "grilled" only matched the 4-item
    # grill category (via CATEGORY_SYNONYMS), none of which are seafood.
    "grill": ["grill", "grilled", "chargrilled", "char-grilled"],
}

# Dietary tags: real per-item data curated in Django admin (DietaryTag model),
# best-effort, not an allergen-safety guarantee. "free" is deliberately not a
# trigger word on its own (too ambiguous/risky) - "gluten" alone is enough to
# catch the natural two-word "gluten free" phrasing, since tokens are matched
# independently and "free" alone will just resolve to nothing and get ignored.
DIETARY_TAG_SYNONYMS = {
    "Gluten-Free": ["gluten", "gluten-free", "glutenfree", "gf"],
    "Vegetarian": ["vegetarian", "vegetarians", "veggie", "veg"],
}


def _dietary_tag_ids(tag_name: str) -> set[int]:
    return set(
        Menu.objects.filter(dietary_tags__name__iexact=tag_name).values_list("id", flat=True)
    )


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

    for tag_name, synonyms in DIETARY_TAG_SYNONYMS.items():
        if token in synonyms:
            ids |= _dietary_tag_ids(tag_name)

    # Nothing matched as a category/keyword-group/dietary-tag word - fall back to a
    # plain name+description search on the raw word itself. This is what makes an
    # unlisted ingredient noun ("eggplant", "veal", "salmon"...) work without having
    # to hand-maintain a CATEGORY_KEYWORDS entry for every ingredient on the menu.
    # Only runs when nothing more specific already matched, so it can't override or
    # dilute a curated match - e.g. "sauté"/"sweet" are already claimed by
    # CATEGORY_SYNONYMS (saute/dessert) and never reach this fallback.
    if not ids:
        ids |= _keyword_ids([token])

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

    return (
        Menu.objects.filter(id__in=result_ids)
        .prefetch_related("dietary_tags")
        .order_by("food_type", "item")
    )


def _candidates():
    """(menu_id, candidate_text) pairs: each item's name plus every alias."""
    items = Menu.objects.all().prefetch_related("aliases")
    pairs = []
    for menu in items:
        pairs.append((menu.id, menu.item))
        for alias in menu.aliases.all():
            pairs.append((menu.id, alias.alias))
    return pairs


# "Build Your Own Pasta" is the one item on the menu that's actually a base item plus
# required combinatorial modifiers (10 pasta shapes x 15 sauces = 150 combos). A phrase
# like "fettuccine alfredo" or "spaghetti bolognese" names a *combination*, not anything
# that exists as a Menu row or alias - so plain name/alias fuzzy matching either can't
# find it (no_match) or worse, gets fooled into a wrong standalone dish because the
# sauce word happens to collide with an unrelated item's alias (e.g. "bolognese" matches
# Pappardelle Bolognese even when the caller said "spaghetti"). An explicit pasta-shape
# word is a much stronger, more precise signal than a fuzzy alias score, so it's checked
# first and - when present - always wins, bypassing the standard search entirely.
BUILD_YOUR_OWN_PASTA_NAME = "Build Your Own Pasta"


def _build_your_own_pasta_menu():
    return Menu.objects.filter(item__iexact=BUILD_YOUR_OWN_PASTA_NAME).first()


def _find_option_in_query(query_lower: str, options):
    """Find the one option (if any) the query is referring to. Options can be
    multi-word ("Al Funghi", "Butter and Cheese"), so substring containment is
    checked first; a fuzzy fallback only catches single-word typos."""
    options = list(options)
    for opt in options:
        if opt.name.lower() in query_lower:
            return opt

    tokens = query_lower.split()
    best_opt, best_score = None, 0
    for opt in options:
        for token in tokens:
            score = fuzz.ratio(token, opt.name.lower())
            if score > best_score:
                best_score, best_opt = score, opt
    return best_opt if best_score >= 85 else None


def resolve_build_your_own(query: str):
    """If the query names an explicit pasta shape, resolve straight to Build Your
    Own Pasta with whatever shape/sauce/protein it stated pre-filled. Returns None
    if there's no Build Your Own item, or no shape word was said at all (in which
    case the standard search should run instead)."""
    menu = _build_your_own_pasta_menu()
    if not menu:
        return None

    mmgs = list(
        menu.modifier_group.select_related("group").prefetch_related("group__options")
    )
    shape_group = next((m for m in mmgs if "pasta" in m.group.name.lower()), None)
    sauce_group = next((m for m in mmgs if "sauce" in m.group.name.lower()), None)
    protein_group = next((m for m in mmgs if "protein" in m.group.name.lower()), None)
    if not shape_group:
        return None

    query_lower = query.lower()
    shape_opt = _find_option_in_query(query_lower, shape_group.group.options.filter(active=True))
    if not shape_opt:
        return None

    preselected = []
    resolved_group_ids = set()
    for mmg in (shape_group, sauce_group, protein_group):
        if not mmg:
            continue
        opt = shape_opt if mmg is shape_group else _find_option_in_query(
            query_lower, mmg.group.options.filter(active=True)
        )
        if opt:
            preselected.append({
                "group_id": mmg.group.id,
                "group_name": mmg.group.name,
                "option_id": opt.id,
                "option_name": opt.name,
            })
            resolved_group_ids.add(mmg.group.id)

    return {
        "menu": menu,
        "preselected": preselected,
        "resolved_group_ids": resolved_group_ids,
    }


def _standalone_dishes_for_shape(shape_name: str):
    """Real standalone dishes named after a pasta shape (every one on this menu
    starts its own name with its shape, e.g. "Spaghetti Arrabbiata"). Used when a
    caller names only a shape with no sauce - the standalone dishes are genuine,
    named menu items and should be offered before defaulting to Build Your Own."""
    return list(
        Menu.objects.filter(food_type="pasta", item__istartswith=shape_name)
        .exclude(item__iexact=BUILD_YOUR_OWN_PASTA_NAME)
        .order_by("item")
    )


def _own_option_matching(menu: Menu, name: str):
    """If this item's own modifier vocabulary (required + optional, e.g.
    Marsala's optional "pasta for saute" group) includes an option with this
    name, return {group_id, group_name, option_id, option_name} for it. Several
    non-pasta items (Marsala, Arrabbiata, Saltimboca...) have their own optional
    pasta-shape add-on, using the same option names as Build Your Own's shape
    list - so a shape word isn't exclusively a Build Your Own signal."""
    name_lower = name.lower()
    mmgs = menu.modifier_group.select_related("group").prefetch_related("group__options")
    for mmg in mmgs:
        for opt in mmg.group.options.filter(active=True):
            if opt.name.lower() == name_lower:
                return {
                    "group_id": mmg.group.id,
                    "group_name": mmg.group.name,
                    "option_id": opt.id,
                    "option_name": opt.name,
                }
    return None


def _item_has_option_named(menu: Menu, name: str) -> bool:
    return _own_option_matching(menu, name) is not None


def _format_byo_result(byo: dict):
    sauce_specified = any("sauce" in p["group_name"].lower() for p in byo["preselected"])
    if not sauce_specified:
        shape_name = next(
            p["option_name"] for p in byo["preselected"] if "pasta" in p["group_name"].lower()
        )
        standalone = _standalone_dishes_for_shape(shape_name)
        if standalone:
            # A shape with no sauce is genuinely ambiguous between the real,
            # named dishes of that shape and a fully custom combo - offer the
            # standalone dishes first, Build Your Own last as the fallback.
            candidates = [(m, 100.0) for m in standalone] + [(byo["menu"], 100.0)]
            return {
                "match_status": "ambiguous",
                "candidates": candidates,
                "build_your_own_fallback": True,
                "build_your_own_item_id": byo["menu"].id,
                "build_your_own_preselected": byo["preselected"],
                "build_your_own_resolved_group_ids": byo["resolved_group_ids"],
            }
    return {
        "match_status": "matched",
        "resolution": "build_your_own",
        "item": byo["menu"],
        "preselected": byo["preselected"],
        "resolved_group_ids": byo["resolved_group_ids"],
    }


def _fuzzy_match(query: str):
    """Plain name/alias fuzzy search - no Build Your Own awareness.

    Uses token_set_ratio rather than WRatio: WRatio blends in a
    length-scaled partial_ratio that dominates whenever the candidate name/
    alias is much shorter than the (usually multi-word, spoken) query - which
    is effectively always here. That scaling makes it converge on a ~85-90
    plateau for names that share only a word or two with the query,
    regardless of whether the item is actually relevant, which then falsely
    crowds out a genuinely strong top match into a false "ambiguous" (e.g.
    "grilled chicken and feta salad" scored Marsala/Saltimboca/Risotto - none
    of them salads - within the ambiguous band of the real 95-scoring match,
    purely from short aliases like "chicken marsala" partially aligning
    against the long query). token_set_ratio doesn't have that scaling
    artifact, so real near-duplicates still tie appropriately (e.g. "parm"
    across Chicken/Eggplant Parm) without unrelated dishes crashing the party.
    """
    pairs = _candidates()
    if not pairs:
        return {"match_status": "no_match"}

    texts = [text for _, text in pairs]
    results = process.extract(query, texts, scorer=fuzz.token_set_ratio, limit=None)

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

    return {"match_status": "no_match"}


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
    # the strongest signal there is - stronger even than either check below. Without
    # checking this first, a real standalone dish whose own name happens to contain a
    # pasta-shape word ("Linguine Alle Vongole") would get wrongly rerouted into a
    # build-your-own combo instead of being recognized verbatim.
    exact_ids = set(Menu.objects.filter(item__iexact=query).values_list("id", flat=True))
    exact_ids |= set(
        MenuAlias.objects.filter(alias__iexact=query).values_list("menu_id", flat=True)
    )
    if len(exact_ids) == 1:
        menu = Menu.objects.get(id=next(iter(exact_ids)))
        return {"match_status": "matched", "item": menu, "score": 100.0}

    byo = resolve_build_your_own(query)
    fuzzy = _fuzzy_match(query)

    if byo and fuzzy["match_status"] == "matched":
        # A shape word alone doesn't automatically mean "build your own" - several
        # real dishes (Marsala, Arrabbiata...) have that same shape as one of their
        # OWN optional add-ons. "marsala angel hair" should stay Marsala with Angel
        # Hair as its own pasta choice, not get rerouted into Build Your Own just
        # because "Angel Hair" also happens to be a Build Your Own shape option.
        shape_name = next(
            p["option_name"] for p in byo["preselected"] if "pasta" in p["group_name"].lower()
        )
        menu = fuzzy["item"]
        if shape_name.lower() in menu.item.lower() or _item_has_option_named(menu, shape_name):
            return fuzzy
        # The shape word isn't explained by this "match" at all (e.g. "spaghetti"
        # has nothing to do with "Pappardelle Bolognese") - that's the signature of
        # a coincidental substring collision, not a real match. Prefer Build Your Own.
        return _format_byo_result(byo)

    if byo and fuzzy["match_status"] == "ambiguous":
        # Same idea, but the underlying item identity is itself still an open
        # question (e.g. "parm veal gluten free pasta" - ambiguous between Parms/
        # Saltimboca/Limone/Arrabbiata). That ambiguity is real and shouldn't be
        # short-circuited into Build Your Own just because a shape word is also
        # present - instead, check each candidate independently: whichever ones
        # actually offer that option get it pre-filled, so it's already resolved
        # no matter which the caller picks. Candidates without it (Parms has no
        # pasta side at all) are left untouched.
        shape_name = next(
            p["option_name"] for p in byo["preselected"] if "pasta" in p["group_name"].lower()
        )
        preselect_by_menu_id = {}
        for menu, _score in fuzzy["candidates"]:
            match = _own_option_matching(menu, shape_name)
            if match:
                preselect_by_menu_id[menu.id] = [match]
        if preselect_by_menu_id:
            fuzzy["ambiguous_preselected"] = preselect_by_menu_id
            return fuzzy
        # None of the real candidates offer it at all - more likely a genuine
        # Build Your Own request than a modification to one of these dishes.
        return _format_byo_result(byo)

    if byo:
        return _format_byo_result(byo)

    return fuzzy
