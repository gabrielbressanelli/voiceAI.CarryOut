from django.shortcuts import render, get_object_or_404
from .cart import Cart
from MenuOrders.models import Menu
from django.http import JsonResponse
from django.template.loader import render_to_string

def cart_summary(request):
    cart = Cart(request)
    cart_items = cart.get_items
    quantities = cart.get_quants
    return render(request, "cart/cart_summary.html", {'cart_items': cart_items, 'quantities': quantities} )

def cart_add(request):
    # Get the cart
    cart = Cart(request)

    # Test for post
    if request.POST.get('action') == 'post':
        # Get food option
        item_id = int(request.POST.get('item_id'))
        item_qty = int(request.POST.get('item_qty'))

        #Look up food option in DataBase
        item = get_object_or_404(Menu, id=item_id)

        # save to session
        cart.add(item=item, quantity=item_qty)

        # Get cart Quantity
        cart_quantity = cart.__len__()

        # Dynamically updating cart_summary.html
        cart_summary_html = render_to_string('cart/cart_summary.html', {
            "cart_items":cart.get_items(),
            "quantities": cart.get_quants()
        }, request=request)


        # Return response
        #response = JsonResponse({'Menu Item:': item.item})
        response = JsonResponse({
            'qty': cart_quantity,
            'cart_summary_html': cart_summary_html,
            })
        return response 



    # Add food to the cart 

def cart_delete(request):
    pass

def cart_update(request):
    pass


