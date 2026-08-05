from decimal import Decimal

from .models import Menu, ModifierOption


def validate_and_price(menu: Menu, selected_ids: list[int]) -> tuple[Decimal, list[dict]]:
    """Validate selected modifier options against a menu item's required/min/max rules
    and compute the resulting unit price. Raises ValueError on an invalid selection.
    """
    mmgs = menu.modifier_group.select_related("group").all().order_by("sort_order")
    selected = ModifierOption.objects.filter(
        id__in=selected_ids, group__in=[m.group for m in mmgs], active=True
    ).select_related("group")

    by_group: dict[int, list[ModifierOption]] = {}
    for opt in selected:
        by_group.setdefault(opt.group_id, []).append(opt)

    for m in mmgs:
        req = m.effective_required()
        mn = m.effective_min()
        mx = m.effective_max()
        chosen = by_group.get(m.group_id, [])
        if req and len(chosen) == 0:
            raise ValueError(f"Missing required selection: {m.group.name}")
        if mn and len(chosen) < mn:
            raise ValueError(f"Select at least {mn} option(s) for {m.group.name}")
        if mx and len(chosen) > mx:
            raise ValueError(f"Select at most {mx} option(s) for {m.group.name}")

    base = menu.price
    multiplier = Decimal("1.00")
    for opt in selected:
        if opt.price_multiplier != 1:
            multiplier *= opt.price_multiplier
    addons = sum((opt.price_delta for opt in selected), start=Decimal("0.00"))
    unit = (base * multiplier + addons).quantize(Decimal("0.01"))

    options_snapshot = [
        {
            "id": opt.id,
            "name": opt.name,
            "group": opt.group.name,
            "price_delta": str(effective_option_delta(menu, opt)),
        }
        for opt in selected
    ]

    return unit, options_snapshot


def effective_option_delta(menu: Menu, option: ModifierOption) -> Decimal:
    """The dollar amount a single option adds/subtracts from this specific menu
    item's base price - for display/receipts only. A price_multiplier (e.g. 0.5 for
    Half Portion) applies to the item's base price, never to other options' deltas,
    so its dollar effect depends on which item it's attached to; validate_and_price
    above is what actually combines multiple selected options into the real total.
    """
    delta = option.price_delta
    if option.price_multiplier != 1:
        delta += menu.price * (option.price_multiplier - Decimal("1"))
    return delta.quantize(Decimal("0.01"))
