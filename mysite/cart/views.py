from django.shortcuts import render, get_object_or_404
from .cart import Cart
from MenuOrders.models import Menu
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.contrib import messages 
from django.views.decorators.http import require_POST

def cart_summary(request):
    cart = Cart(request)

    ids = [L["menu_id"] for L in cart.lines]
    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}
    # Build rows for template rendering
    lines_for_ui = []
    for i, L in enumerate(cart.lines):
        m = menu_map.get(L["menu_id"])
        lines_for_ui.append({

            "index":i,
            "menu_id": L["menu_id"],
            "name":L.get("menu_name") or (m.item if m else "Item"),
            "qty": int(L.get("qty", 0)),
            "unit_price": int(L.get("unit_price", "0.00")),
            "options": L.get("options", []),
            "note": L.get("note", ""),
            "picture_url": (m.picture.url if m and m.picture else None),
            "raw": L,

        })

    return render(
        request,
        "cart/cart_summary.html",
        {"lines": lines_for_ui, "totals":cart.cart_total(),}
    )

@require_POST
def cart_add(request):
    menu_id= int(request.POST["menu_id"])
    qty = int(request.POST("qty", 1))

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
    


    #Look up food option in DataBase
    item = get_object_or_404(Menu, id=item_id)

    # save to session
    cart.add(item=item, quantity=item_qty)

    # Get cart Quantity
    cart_quantity = cart.__len__()

    # Dynamically updating cart_summary.html
    html = _render_cart_partial(request, cart)


    # Return JsonResponse
    response = JsonResponse({
        'ok':True,
        'cart_size': len(cart),
        'totals': str(cart.cart_total()),
        'cart_summary_html': html,
        })
    
    return response 


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
    idx = int(request.POST.get("line_index", -1))
    cart = Cart(request)
    cart.delete(idx)
    return JsonResponse({"ok": True})

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


