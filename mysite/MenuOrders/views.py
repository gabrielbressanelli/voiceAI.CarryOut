from django.shortcuts import render
from django.http import HttpResponse, JsonResponse
from .models import Menu, MenuModifierGroup, ModifierOption, ModifierGroup
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
        return JsonResponse({"error": "Menu Item not found"}, status=400)
    
    groups = (
        menu.modifier_group
        .select_related("group")
        .prefetch_related("group__options")
    )

    payload = []
    for g in groups:
        grp = g.group
        payload.append({
            "group_id":grp.id,
            "group_name":grp.name,
            "required": g.required if g.required is not None else grp.required,
            "min_choices": g.min_choices if g.min_choices is not None else grp.min_choices,
            "max_choices": g.max_choices if g.max_choices is not None else grp.max_choices,
            "options": [
                {
                    "id": opt.id,
                    "name": opt.name,
                    "price_delta": opt.price_delta,
                    "is_default": opt.is_default,
                }
                for opt in grp.options.all()
            ],

        })
    return JsonResponse(payload, safe=False)


