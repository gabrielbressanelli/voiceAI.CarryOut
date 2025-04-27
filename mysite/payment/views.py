from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ShippingForm, PaymentForm
from cart.cart import Cart
from MenuOrders.models import Menu
from .models import ShippingAddress, Order, OrderItem
from django.urls import reverse
from django.conf import settings
import uuid # unique user id for NO duplicate orders

# Importing paypal stuff
from paypal.standard.forms import PayPalPaymentsForm

def process_order(request):
    if request.POST:
        # getting cart
        cart = Cart(request)
        cart_items = cart.get_items
        quantities = cart.get_quants
        totals = cart.cart_total() 

        # Get billing info from last page 
        payment_form = PaymentForm(request.POST or None)

        # Getting shipping session data
        my_shipping = request.session.get('my_shipping')

        # Gather order info
        full_name = my_shipping['full_name']
        email = my_shipping['email']
        # Creat Delivery address from session
        shipping_address = f'{my_shipping['address1']}\n{my_shipping['address2']}\n{my_shipping['city']}\n{my_shipping['state']}\n{my_shipping['zipcode']}\n'
        amount_paid = totals

        # Creat Order
        create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid)
        create_order.save() 

        # Add order items
        # Get the order ID
        order_id = create_order.pk # pk for primary key
        # Get item info
        for item in cart_items():
            # Get item id
            item_id = item.id
            # Get item price
            price = item.price
            # Get quantity
            for key, value in quantities().items():
                if int(key) ==  item.id:
                    #Create order item
                    create_order_item = OrderItem(order_id=order_id ,  item_id= item_id,  quantity=value, price=price,)
                    create_order_item.save()
        
        # Delete cart after purchase
        for key in list(request.session.keys()):
            if key == "session_key" :
                # delete the key
                del request.session[key]

        return render(request, 'process_order.html', {})
    else:
        message.warning(request, 'Access Denied!')
        return redirect('/')


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

        # Gather order info
        full_name = my_shipping['full_name']
        email = my_shipping['email']
        # Creat Delivery address from session
        shipping_address = f'{my_shipping['address1']}\n{my_shipping['address2']}\n{my_shipping['city']}\n{my_shipping['state']}\n{my_shipping['zipcode']}\n'
        amount_paid = totals

        # Get the host
        host = request.get_host()

        # Create a Invoice Number  
        my_Invoice = str(uuid.uuid4())

        # Create paypal form and some more stuff
        paypal_dict = {
            'business': settings.PAYPAL_RECEIVER_EMAIL,
            'amount': totals,
            'item_name': 'Food Order',
            'no_shipping': '2',
            'invoice': my_Invoice,
            'currency_code': 'USD',
            'notify_url': 'https://{}{}'.format(host, reverse("paypal-ipn")),
            'return_url': 'https://{}{}'.format(host, reverse("payment_success")),
            'cancel_return': 'https://{}{}'.format(host, reverse("payment_failed")),
        }

        # Create PayPal Form(it is just a button)
        paypal_form = PayPalPaymentsForm(initial=paypal_dict)

        create_order = Order(full_name=full_name, email=email, shipping_address=shipping_address, amount_paid=amount_paid, invoice=my_Invoice)
        create_order.save() 

        # Add order items
        # Get the order ID
        order_id = create_order.pk # pk for primary key
        # Get item info
        for item in cart_items():
            # Get item id
            item_id = item.id
            # Get item price
            price = item.price
            # Get quantity
            for key, value in quantities().items():
                if int(key) ==  item.id:
                    #Create order item
                    create_order_item = OrderItem(order_id=order_id ,  item_id= item_id,  quantity=value, price=price,)
                    create_order_item.save()
        


        form = ShippingForm(request.POST)
        billing_form = PaymentForm()

        # Generating a context to pass both form and cart items
        context = {
        'cart_items': cart_items,
        'quantities': quantities,
        'totals':totals,
        'shipping_info': request.POST,
        'billing_form': billing_form,
        'paypal_form': paypal_form,
        }

        return render(request, 'billing_info.html', context)
    else:
        messages.warning(request, "Access Denied")
        return redirect('/')
    

def payment_success(request):
    # Delete browser cart
    # First get cart
    cart = Cart(request)
    cart_items = cart.get_items
    quantities = cart.get_quants
    totals = cart.cart_total() 

    context = {
    'cart_items': cart_items,
    'quantities': quantities,
    'totals':totals,
    }

    for key in list(request.session.keys()):
        if key == 'session_key':
            del request.session[key]


    return render(request, "payment_success.html", context)

def payment_failed(request):
    return render(request, "payment_success.html", {})


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
        