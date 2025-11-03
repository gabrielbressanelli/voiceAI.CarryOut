from MenuOrders.models import Menu, MenuModifierGroup, ModifierOption
from decimal import Decimal

CART_SESSION_KEY = 'cart'

class Cart():
    def __init__(self, request):
        self.session = request.session
        self.lines = self.session.get(CART_SESSION_KEY) or []
        # normalize for a list
        if not isinstance(self.lines, list):
            self.lines = []
            self.session[CART_SESSION_KEY] = self.lines
    def _save(self):
        self.session[CART_SESSION_KEY] = self.lines
        self.session.modified = True


    def add(self, menu:Menu, quantity: int, selected_option_ids: list[int] | None = None, note: str = ""):
        """ Selected option ids, list of ids chosen by the user for modifiers"""
        selected_option_ids = selected_option_ids or [] 
        # validate selection and compute unit price now (snapshot)
        unit_price, options_snapshot = self._validate_and_price(menu,selected_option_ids)

        # Attempt to merge identical lines (same item + same options)
        for line in self.lines:
            if line["menu_id"] == menu.id and sorted(line['options']) == sorted([o["id"]for o in options_snapshot]):
                line["qty"] += int(quantity)
                self._save()
                return
        self.lines.append({
            "menu_id": menu.id,
            "menu_name":menu.item,
            "qty": int(quantity),
            "unit_price": str(unit_price), # str for JSON
            "options": options_snapshot,
            "note": note or "",
        })
        self._save()

    def _validate_and_price(self, menu:Menu, selected_ids: list[int]) -> tuple[Decimal, list[dict]]:
        mmgs = menu.modifier_group.select_related("group").all().order_by("sort_order")
        selected = ModifierOption.objects.filter(id__in=selected_ids, group__in=[m.group for m in mmgs], active=True).select_related("group")

        # per group validation
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
                raise ValueError(f'Select at most {mx} option(s) for {m.group.name}')
            
        # compute price 
        base = menu.price
        addons = sum((opt.price_delta for opt in selected), start=Decimal("0.00"))
        unit = (base + addons).quantize(Decimal("0.01"))
        
        #Snapshot options (names + deltas) so Stripe printer do not need DB
        options_snapshot = [{
            "id": opt.id,
            "name": opt.name,
            "group": opt.group.name,
            "price_delta": str(opt.price_delta)
        } for opt in selected]

        return unit, options_snapshot



    def cart_total(self):
        total = Decimal("0.00")
        for L in self.lines:
            total += Decimal(L["unit_price"]) * int(L["qty"])
        return total.quantize(Decimal("0.01"))



    def __len__(self):
        return sum(int(L["qty"]) for L in self.lines)
    
    def as_snapshot_for_stripe(self):
        """Serialize a compact, selfsuficient snapshot for PI metadada"""

        return [
            {
                "menu_id":L["menu_id"],
                "menu_name": L["menu_name"],
                "qty": int(L["qty"]),
                "unit_price": L["unit_price"],
                "options": L["options"],
                "note": L.get("note", ""),

            }
            for L in self.lines
        ]

    def get_items(self):
        # Get ids from carts
        ids = [L["menu_id"] for L in self.lines if "menu_id" in L]
        return Menu.object.filter(id__in=ids)

        # View ids to look up items on database model
        items = Menu.objects.filter(id__in=ids)

        return items

    def get_quants(self):
        return { str(L['menu_id']): int(L.get('qty', 0)) for L in self.lines if "menu_id" in L}

    def update_qty(self, line_index: int, qty: int):
        if 0 <= line_index < len(self.lines):
            self.lines[line_index]["qty"] = int(qty)
            self._save()

    def delete(self, line_index: int):
        if 0 <= line_index < len(self.lines):
            del self.lines[line_index]
            self._save()

    def clear(self):
        self.lines.clear()
        self._save()


        
