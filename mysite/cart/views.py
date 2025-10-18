from django.shortcuts import render, get_object_or_404
from .cart import Cart
from MenuOrders.models import Menu
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.contrib import messages 
from django.views.decorators.http import require_POST
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

def _dec(val, default="0.00"):
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)
    

def cart_summary(request):
    cart = Cart(request)

    ids = []
    for L in cart.lines:
        try:
            ids.append(int(L.get("menu_id", 0)))
        except (TypeError, ValueError):
            pass

    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}
    # Build rows for template rendering
    lines_for_ui = []
    for i, L in enumerate(cart.lines):
        m = menu_map.get(int(L["menu_id"])) if str(L.get("menu_id", "")).isdigit() else None
        qty = int(L.get("qty", 0) or 0)

        # Keep price as decimal
        unit_price = _dec(L.get("unit_price", "0.00"))
        unit_price = unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        unit_price_display = f"{unit_price:.2f}"

        lines_for_ui.append({

            "index":i,
            "menu_id": L["menu_id"],
            "name":L.get("menu_name") or (m.item if m else "Item"),
            "qty": int(L.get("qty", 0)),
            "unit_price": unit_price,
            "options": L.get("options", []),
            "note": L.get("note", ""),
            "picture_url": (m.picture.url if m and m.picture else None),
            "raw": L,

        })

        # Totals round to 2 digit after point 
    totals_dec = _dec(cart.cart_total())
    totals_dec = totals_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    totals_display = f"{totals_dec:.2f}"

    return render(
        request,
        "cart/cart_summary.html",
        {"lines": lines_for_ui, "totals":totals_dec, "totals_display":totals_display, "unity_price_display": unit_price_display}
    )

@require_POST
def cart_add(request):
    menu_id= int(request.POST["menu_id"])
    qty = int(request.POST.get("qty", 1))

    raw = request.POST.getlist("modifier_options_ids[]") or request.POST.get("modifier_option_ids", "")
    if isinstance(raw, str):
        selected_ids = [int(x) for x in raw.split(",") if x.strip().isdigit()]

    else:
        selected_ids = [int(x) for x in raw if str(x).isdigit()]

    note = request.POST.get("note", "")
    menu = get_object_or_404(Menu, id=menu_id)
    # Get the cart
    cart = Cart(request)


    try:
        cart.add(menu,qty, selected_option_ids=selected_ids, note=note)
    except ValueError as e:
        return JsonResponse({"ok":False, "error":str(e)}, status=400)
    return JsonResponse({"ok": True, "cart_qty": len(cart)})



@require_POST
def cart_update(request):
    if request.POST.get('action') != 'post':
        return JsonResponse({"error": "bad request"}, status=400)
    idx = int(request.POST.get("line_index", -1))
    qty = int(request.POST.get("item_qty", 1))
    cart = Cart(request)
    cart.update_qty(idx, qty)
    return JsonResponse({"ok": True})

@require_POST
def cart_delete(request):
    if request.POST.get('action') != 'post':
        return JsonResponse({"error": "bad request"}, status=400)
    try:
        idx = int(request.POST.get("line_index", -1))
    except (TypeError, ValueError):
        return JsonResponse({"ok":False, "error":"invalid index"}, status=400)
    cart = Cart(request)
    if not (0 <= idx < len(cart.lines)):
        return JsonResponse({"ok":True, "cart_qty": len(cart)})
    cart.delete(idx)
    cart.save()
    return JsonResponse({"ok":True, "cart_qty": len(cart)})

# Handler to keep partial rendering consistent throughout all the acitons
def _render_cart_partial(request, cart: Cart) -> str:
    items_qs= cart.get_items()
    quantities = cart.get_quants()
    rows = []

    for m in items_qs:
        qty = int(quantities.get(str(m.id), 0))
        rows.append({
            "item": m,
            "qty": qty,
            "line_total": m.price*qty,
        })

        return render_to_string(
            "cart/cart_summary.html",
            {"rows":rows, "totals":cart.cart_total(), "cart_size":len(cart)},
            request=request
        )
    
def cart_count(request):
    cart = Cart(request)
    return JsonResponse({"cart_qty": len(cart)}, headers={"Cache-control":"no-store"})



