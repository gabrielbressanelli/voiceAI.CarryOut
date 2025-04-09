from django.shortcuts import render
from django.http import HttpResponse
from .models import Menu
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

