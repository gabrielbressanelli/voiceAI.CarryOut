from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ShippingForm, PaymentForm
from cart.cart import Cart
from MenuOrders.models import Menu

def process_order(request):
    if request.POST:
        # Get billing info from last page 
        payment_form = PaymentForm(request.POST or None)

        # Getting shipping session data
        my_shipping = request.session.get('my_shipping')
        print(my_shipping)
        return render(request, 'process_order', {})

def payment_success(request):
    return render(request, "payment_success.html", {})

def billing_info(request):
    # Checking to see if it is coming from a post button instead of just reaching the link by typing
    if request.POST:
        # getting cart
        cart = Cart(request)
        cart_items = cart.get_items
        quantities = cart.get_quants
        totals = cart.cart_total() 

        # Create a session to store shipping info
        my_shipping = request.POST
        request.session['my_shipping'] = my_shipping # can reference this session in any other view

        form = ShippingForm(request.POST)
        billing_form = PaymentForm()
        # Generating a context to pass both form and cart items
        context = {
        'cart_items': cart_items,
        'quantities': quantities,
        'totals':totals,
        'shipping_info': request.POST,
        'billing_form': billing_form,
        }

        return render(request, 'billing_info.html', context)
    else:
        messages.warning(request, "Access Denied")
        return redirect('/')
    




def delivery_form(request):

    # Generating content from cart.py
    cart = Cart(request)
    cart_items = cart.get_items
    quantities = cart.get_quants
    totals = cart.cart_total() 

    if request.method == 'POST':
        form = ShippingForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Your info has been saved")
            return redirect( "billing_info")
    else: 
        form = ShippingForm()

    # Generating a context to pass both form and cart items
    context = {
    'cart_items': cart_items,
    'quantities': quantities,
    'totals':totals,
    'form': form,
    }

    return render(request, 'delivery.html', context)
        