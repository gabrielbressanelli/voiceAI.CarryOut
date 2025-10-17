from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Menu, MenuModifierGroup, ModfierOption, ModifierGroup
from cart.cart import Cart
from django.contrib import messages



def index(request):
    menu = Menu.objects.all()
    appetizer = Menu.objects.filter(food_type='appetizer')
    pasta = Menu.objects.filter(food_type='pasta')
    grill = Menu.objects.filter(food_type='grill')
    seafood = Menu.objects.filter(food_type='seafood')
    dessert = Menu.objects.filter(food_type='dessert')
    beverage = Menu.objects.filter(food_type='beverage')

    # Generating content from cart.py
    cart = Cart(request)
    cart_items = cart.get_items
    quantities = cart.get_quants
    totals = cart.cart_total() 

    context = {
        'menu': menu,
        'appetizer': appetizer,
        'pasta': pasta,
        'grill': grill,
        'seafood': seafood,
        'dessert': dessert,
        'beverage': beverage,
        'cart_items': cart_items,
        'quantities': quantities,
        'totals':totals,

    }

    return render(request, 'index.html', context)

def menu_modifiers(request, menu_id):
    try:
        menu = Menu.objects.get(id=menu_id)

    except Menu.DoesNotExist:
        return JsonResponse({"error": "Menu Item not found"}, statu=400)
    
    groups = menu.modifier_group().all.prefetch_related("options")

    payload = []
    for g in groups:
        payload.append({
            "group_id":g.id,
            "group_name":g.name,
            "required": g.required,
            "max_choices": g.max_choices,
            "options": [
                {
                    "id": opt.id,
                    "name": opt.name,
                    "price_delta": opt.price_delta,
                    "is_default": opt.is_default,
                }
                for opt in g.options.all()
            ]

        })
    return JsonResponse(payload, safe=False)


