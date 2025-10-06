from django.shortcuts import render, redirect
from django.contrib import messages
import stripe.error
from .forms import ShippingForm, PaymentForm
from cart.cart import Cart
from MenuOrders.models import Menu
from .models import ShippingAddress, Order, OrderItem
from django.urls import reverse
from django.conf import settings
import json
import stripe, requests
from decimal import Decimal, ROUND_HALF_UP
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt
import uuid # unique user id for NO duplicate orders
import os, environ


# Importing paypal stuff
from paypal.standard.forms import PayPalPaymentsForm

# Using stripe Key
stripe.api_key = settings.STRIPE_SECRET_KEY

# Bearer key for printing at the kitchen
printing_key = os.getenv("order_printing_secret_key")

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
        messages.warning(request, 'Access Denied!')
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

def _money_to_cents(amount: Decimal) -> int:
    return int((amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP) * 100))

def create_checkout_session(request):
    # get cart from session
    cart = Cart(request)
    if len(cart) == 0:
        return JsonResponse({"error":"Cart is empty"}, status=400)
    
    # Building item lookup
    item_ids = list(cart.cart.keys())
    menu_map = {str(m.id): m for m in Menu.objects.filter(id__in=item_ids)}

    # Stripe Line Items
    line_items = []
    for item_id, qty in cart.cart.items():
        m = menu_map.get(item_id)
        if not m:
            continue
        line_items.append({
            "price_data":{
                "currency":"usd",
                "product_data": {"name":m.item},
                "unit_amount": _money_to_cents(m.price)
            },
            "quantity": int(qty),
        })
    
    if not line_items:
        return JsonResponse({"error": "No valid items in cart"}, status=400)
    
    # Success and Cancel URL's
    success_url = request.build_absolute_uri(reverse("checkout_success") + "?session_id={CHECKOUT_SESSION_ID}")
    cancel_url = request.build_absolute_uri(reverse("checkout_cancel"))

    # Create the Checkout Session (No Shipping)
    session = stripe.checkout.Session.create(
        mode='payment',
        line_items=line_items,
        success_url=success_url,
        cancel_url=cancel_url,
        automatic_tax={"enabled":False},
        allow_promotion_codes=True,

        payment_intent_data={
            "metadata":{
                "source":"django_session_cart",
                # Important: Store a snapshot for the webhook can reconcile
                "cart_snapshot":json.dumps([
                    {"menu_id": k, "qty": int(v)} for k, v in cart.cart.items()
                ])
            }
        },
    )

    return JsonResponse({"checkout_url": session.url})
        
def checkout_success(request):
    return HttpResponse("Thanks, Payment successful. Your Order is being prepared.")

def checkout_cancel(request):
    return HttpResponse("Payment Canceled. Your cart is still available.")

def items_from_snapshot(snapshot_json: str):
    """
    The "snapshot_json is what gert sotre in the paymentIntent MetaData:
    [{"menu_id":12, "qty": 3}]
    Which returns a list of dicts: [{'name':..., "qty":...}] and the decimal total
    """
    try:
        snap = json.loads(snapshot_json) if snapshot_json else []
    except json.JSONDecodeError:
        snap = []

    ids = [int(r["menu_id"] for r in snap if "menu_id" in r)]
    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}

    items = []
    total = Decimal("0.00")
    for r in snap:
        mid = int(r.get("menu_id", 0))
        qty = int(r.get("qty", 0))
        m = menu_map.get(mid)

        if not m or qty <= 0:
            continue
        total += m.price*qty
        items.append({"name":m.item, "qty":qty})
    return total, items

def order_summary_string(items):
    return "; ".join(f"{it['qty']}x {it['name']}" for it in items)

@csrf_exempt
def stripe_webhook(request):
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(request.body, sig, settings.STRIPE_WEBHOOK_SECRET)
    except Exception:
        return HttpResponse(status=400)
    
    if event["type"] in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        session = event["data"]["object"]
        if session.get("payment_status") != 'paid':
            return HttpResponse(status=200)

        # 1) Grab PaymentIntent so we can read MetaData
        pi_id = session.get("payment_intent")
        cart_snapshot = None
        if pi_id:
            try: 
                pi = stripe.PaymentIntent.retrieve(pi_id)
                cart_snapshot = pi.metadata.get("cart_snapshot")
            except stripe.error.StripeError:
                return HttpResponse(status=400)
        
        # 2) Rebuild items and summary
        items, _total = items_from_snapshot(cart_snapshot)
        summary= order_summary_string(items)

        # 3) Customer Name
        cust_name = (session.get("customer_details") or {}).get("name") or "Guest"

        # 4) Order number based on session id last 6 chars
        order_number = f"CHK-{(session.get('id') or '')[-6:] or 'UNKNOWN'}"

        # 5) Send to printer
        if settings.PRINT_SERVICE_URL and settings.order_printing_secret_key:
            try:
                resp = requests.post(
                    settings.PRINT_SERVICE_URL,
                    headers={
                        "Authorization": f'Bearer {settings.order_printing_secret_key}',
                        "Content-Type": "application/json",
                    },
                    json={
                        "customerName": cust_name,
                        "order_summary": summary,
                        "orderNumber": order_number,
                    },
                    timeout=8,
                )
            except requests.RequestException:
                return HttpResponse(status=500)
            
            if not (200 <= resp.status_code < 300):
                return HttpResponse(status=500)


    return HttpResponse(status=200)



