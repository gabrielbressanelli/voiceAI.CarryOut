from django.shortcuts import render, get_object_or_404
from .cart import Cart
from MenuOrders.models import Menu
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.contrib import messages 
from django.views.decorators.http import require_POST

def cart_summary(request):
    cart = Cart(request)
    items_qs = cart.get_items()
    quantities = cart.get_quants()
    totals = cart.cart_total() 

    # Build rows for template rendering
    rows = []
    for m in items_qs:
        qty = int(quantities.get(str(m.id), 0))
        rows.append({
            "item": m,
            "qty": qty,
            "line_total": m.price*qty,
        })

    return render(
        request,
        "cart/cart_summary.html",
        {"rows": rows, "totals":totals, "cart_size":len(cart)}
    )

@require_POST
def cart_add(request):
    # Get the cart
    cart = Cart(request)


    try:
        item_id = int(request.POST.get('item_id'))
        item_qty = int(request.POST.get('item_qty', 1))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Bad Params")
    


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
def cart_delete(request):
    cart = Cart(request)

    
    # Get food option
    try:
        item_id = int(request.POST.get('item_id'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Bad Params")
    

    # Call delete function on Cart
    cart.delete(item=item_id)

    html = _render_cart_partial(request, cart)


    response = JsonResponse({
        'Item' : item_id,

        }) 
    return response 


@require_POST
def cart_update(request):
    cart = Cart(request)

    try:
        # Get food option
        item_id = int(request.POST.get('item_id'))
        item_qty = int(request.POST.get('item_qty'))
    except (TypeError, ValueError):
        return HttpResponseBadRequest("Bad Params")

    cart.update(item=item_id, quantity=item_qty)

    html = _render_cart_partial(request, cart)

    response = JsonResponse({
        'qty' : item_qty,
        "cart_size": len(cart),
        "totals": str(cart.cart_total()),
        "cart_summary": html,
        }) 
    return response 

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


