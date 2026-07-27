import re
from decimal import Decimal

from rapidfuzz import fuzz, process

from MenuOrders.models import Menu

ITEM_NAME_MATCH_MIN = 85
MODIFIER_NAME_MATCH_MIN = 80

# Anchors on "Nx " wherever it occurs, rather than splitting on ";" - the
# order_summary is LLM-composed free text, not a validated format, and a missing
# ";" between a modifier and the next item ("- Chicken 2x Calamari") is a real,
# observed failure mode. Finding item boundaries this way is immune to it.
ITEM_BOUNDARY_RE = re.compile(r"(\d+)\s*x\s+", re.IGNORECASE)


def _split_into_item_chunks(order_summary: str):
    text = order_summary or ""
    matches = list(ITEM_BOUNDARY_RE.finditer(text))
    chunks = []
    for i, m in enumerate(matches):
        qty = int(m.group(1))
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        chunks.append((qty, text[start:end]))
    return chunks


def _parse_chunk(chunk: str):
    segments = [s.strip() for s in chunk.split(";") if s.strip()]
    if not segments:
        return "", []
    item_name = segments[0]
    modifiers = [seg.lstrip("-").strip() for seg in segments[1:]]
    return item_name, [m for m in modifiers if m]


def _match_menu_item(name: str):
    name = (name or "").strip()
    if not name:
        return None

    menu = Menu.objects.filter(item__iexact=name).first()
    if menu:
        return menu

    names = list(Menu.objects.values_list("item", flat=True))
    best = process.extractOne(name, names, scorer=fuzz.WRatio)
    if best and best[1] >= ITEM_NAME_MATCH_MIN:
        return Menu.objects.filter(item__iexact=best[0]).first()
    return None


def _item_modifier_options(menu):
    mmgs = menu.modifier_group.select_related("group").prefetch_related("group__options")
    options = []
    for mmg in mmgs:
        options.extend(mmg.group.options.filter(active=True))
    return options


def _match_modifier_option(options, mod_text: str):
    mod_text = (mod_text or "").strip()
    if not mod_text or not options:
        return None

    for opt in options:
        if opt.name.lower() == mod_text.lower():
            return opt

    names = [o.name for o in options]
    best = process.extractOne(mod_text, names, scorer=fuzz.WRatio)
    if best and best[1] >= MODIFIER_NAME_MATCH_MIN:
        return next((o for o in options if o.name == best[0]), None)
    return None


def compute_total_from_summary(order_summary: str):
    """Best-effort re-price a human-readable order_summary recap.

    Never raises - unresolvable items/modifiers are skipped and reported in the
    returned warnings list rather than aborting the whole calculation, since the
    caller has no way to fix a bad line mid-calculation. Pre-tax: matches every
    other total in this system, Stripe computes tax at actual checkout.
    """
    chunks = _split_into_item_chunks(order_summary)
    warnings = []
    total = Decimal("0.00")

    if not chunks:
        warnings.append("Could not find any 'Nx Item' entries in order_summary.")
        return total, warnings

    for qty, chunk in chunks:
        item_name, modifier_texts = _parse_chunk(chunk)
        if not item_name:
            warnings.append("Found a quantity with no item name attached.")
            continue

        menu = _match_menu_item(item_name)
        if not menu:
            warnings.append(f"Could not match item: {item_name!r}")
            continue

        options = _item_modifier_options(menu)
        line_unit_price = menu.price
        for mod_text in modifier_texts:
            option = _match_modifier_option(options, mod_text)
            if not option:
                warnings.append(f"Could not match modifier {mod_text!r} for item {menu.item!r}")
                continue
            line_unit_price += option.price_delta

        total += line_unit_price * qty

    return total.quantize(Decimal("0.01")), warnings
