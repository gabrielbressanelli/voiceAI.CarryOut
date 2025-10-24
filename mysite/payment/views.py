from django.shortcuts import render, redirect
from django.contrib import messages
from .forms import ShippingForm, PaymentForm
from cart.cart import Cart
from MenuOrders.models import Menu
from .models import ShippingAddress, Order, OrderItem
from django.urls import reverse
from django.conf import settings
import stripe, requests, logging, os, environ, json, uuid
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
from django.http import JsonResponse, HttpResponse
from django.views.decorators.csrf import csrf_exempt



# Importing paypal stuff
from paypal.standard.forms import PayPalPaymentsForm

# Using stripe Key
log = logging.getLogger("stripe_webhook")
stripe.api_key = settings.STRIPE_SECRET_KEY

# Bearer key for printing at the kitchen
printing_key = os.getenv("PRINT_SERVICE_TOKEN")

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
        #shipping_address = f'{my_shipping['address1']}\n{my_shipping['address2']}\n{my_shipping['city']}\n{my_shipping['state']}\n{my_shipping['zipcode']}\n'
        amount_paid = totals

        # Creat Order
        create_order = Order(full_name=full_name, email=email, shipping_address="shipping_address", amount_paid=amount_paid)
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
        #shipping_address = f'{my_shipping['address1']}\n{my_shipping['address2']}\n{my_shipping['city']}\n{my_shipping['state']}\n{my_shipping['zipcode']}\n'
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

        create_order = Order(full_name=full_name, email=email, shipping_address="shipping_address", amount_paid=amount_paid, invoice=my_Invoice)
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

    ids = [L["menu_id"] for L in cart.lines]
    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}

    lines_for_ui = []
    for i, L in enumerate(cart.lines):
        m = menu_map.get(L["menu_id"])
        lines_for_ui.append({
            "index": i,
            "menu_id":L["menu_id"],
            "name": L.get("menu_name") or (m.item if m else "item"),
            "qty": int(L.get("qty", 0)),
            "unit_price": m.price if m else L.get("unit_price", 0),
            "options": L.get("options", []),
            "note": L.get("note", ""),
            "picture_url": (m.picture.url if m and m.picture else None),
            "Raw": L,
        })

    context = {
        "lines": lines_for_ui,
        "totals": cart.cart_total()
    }

    return render(request, "delivery.html", context)



# ---------- helpers ----------
def _norm_delta(val) -> Decimal:
    try:
        return Decimal(str(val)).quantize(Decimal("0.00"))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal("0.00")

def _is_free_delta(val) -> bool:
    return _norm_delta(val) == Decimal("0.00")

def _compact_from_description(desc: str) -> tuple[str, str]:
    """
    Fallback parser: turn "Base - Group: Name; Group (+$12.00)" into ("Base", "Name")
    Returns (base, joined_option_names_no_groups_no_prices)
    """
    if not desc:
        return ("Item", "")
    parts = desc.split(" - ", 1)
    base = parts[0].strip()
    if len(parts) == 1:
        return (base, "")
    tail = parts[1]
    pieces = [p.strip() for p in tail.split(";")]
    names = []
    for p in pieces:
        # drop "(+$...)" suffix if present
        before_price = p.split("(+$", 1)[0].strip()
        # drop "Group: " prefix if present
        name_only = before_price.split(": ", 1)[-1].strip()
        if name_only:
            names.append(name_only)
    return (base, " ".join(names))


# ---------- create checkout session ----------
def create_checkout_session(request):
    cart = Cart(request)
    if len(cart) == 0:
        return JsonResponse({"error": "Cart is empty"}, status=400)

    # Build DB map for safe fallbacks
    item_ids = []
    for L in cart.lines:
        try:
            item_ids.append(int(L.get("menu_id", 0)))
        except (TypeError, ValueError):
            pass
    menu_map = {int(m.id): m for m in Menu.objects.filter(id__in=item_ids)}

    line_items = []
    for L in cart.lines:
        # base name (cart -> DB -> "Item")
        mid = int(L.get("menu_id"))
        m = menu_map.get(mid)
        base_name = (
            L.get("menu_name")
            or (getattr(m, "item", None) if m else None)
            or (getattr(m, "name", None) if m else None)
            or "Item"
        )

        # modifiers (for Stripe display WITH groups/prices)
        opts = L.get("options") or []
        if not isinstance(opts, list):
            opts = []
        mods = "; ".join(
            (
                f"{o.get('group','')}: {o.get('name','')}"
                if _is_free_delta(o.get("price_delta"))
                else f"{o.get('group','')} (+${_norm_delta(o.get('price_delta'))})"
            ).strip()
            for o in opts
        )
        display_name = base_name + (f" - {mods}" if mods else "")

        # COMPACT name (for printer): base + option names only
        compact_opts = " ".join(o.get("name", "") for o in opts if o.get("name")).strip()
        compact_name = f"{base_name} {compact_opts}".strip()

        # price (cart -> DB) and qty
        try:
            unit_price = Decimal(str(L.get("unit_price")))
        except Exception:
            unit_price = Decimal(str(getattr(m, "price", "0.00"))) if m else Decimal("0.00")
        qty = int(L.get("qty", 1))

        # (Optional) Validate minimums to avoid Stripe errors
        if unit_price <= Decimal("0"):
            return JsonResponse({"error": "Invalid item price"}, status=400)
        if qty < 1:
            return JsonResponse({"error": "Invalid quantity"}, status=400)

        line_items.append({
            "price_data": {
                "currency": "usd",
                "product_data": {
                    "name": display_name,                 # what Stripe shows
                    "metadata": {"compact_name": compact_name},  # what we print later
                },
                "unit_amount": int((unit_price * 100).quantize(Decimal("1"))),
            },
            "quantity": qty,
        })

    if not line_items:
        return JsonResponse({"error": "No valid items in cart"}, status=400)

    success_url = request.build_absolute_uri(
        reverse("checkout_success") + "?session_id={CHECKOUT_SESSION_ID}"
    )
    cancel_url = request.build_absolute_uri(reverse("checkout_cancel"))

    try:
        session = stripe.checkout.Session.create(
            mode="payment",
            line_items=line_items,
            success_url=success_url,
            cancel_url=cancel_url,
            automatic_tax={"enabled": True},
            allow_promotion_codes=True,
        )
    except Exception as e:
        log.exception("Stripe Session.create failed: %s", e)
        return JsonResponse({"error": "Payment provider error"}, status=502)

    return JsonResponse({"checkout_url": session.url})
        
def checkout_success(request):
    return HttpResponse("Thanks, Payment successful. Your Order is being prepared.")

def checkout_cancel(request):
    return redirect("/payment/delivery/") 

def items_from_snapshot(snapshot_json: str):
    """
    The "snapshot_json is what get sotre in the paymentIntent MetaData:
    [{"menu_id":12, "qty": 3}]
    Which returns a list of dicts: [{'name':..., "qty":...}] and the decimal total
    """
    try:
        snap = json.loads(snapshot_json) if snapshot_json else []
    except json.JSONDecodeError:
        snap = []

    ids = []
    for r in snap:
        try:
            ids.append(int(r["menu_id"]))
        except Exception:
            pass
    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}

    items = []
    print_items = []
    total = Decimal("0.00")
    for r in snap:
        try: 
            qty = int(r.get("qty", 0))
        except Exception:
            qty = 0
        if qty <= 0:
            continue

        m = menu_map.get(int(r.get("menu_id", 0)))
        name = (
            r.get("menu_name")
            or (getattr(m, "item", None) if m else None)
            or (getattr(m, "name", None) if m else None)
            or "Item"
        )

        try:
            unit = Decimal(str(r.get("unit_price"))) if r.get("unit_price") is not None else None
        except Exception:
            unit = None
        if unit is None:
            unit = Decimal(str(getattr(m, "price", "0.00"))) if m else Decimal("0.00")

        opts = r.get("options") or []

        total += unit * qty


        if opts:
            mod_text = "; ".join(
                f"{(o.get('group') or '') + (': ' if o.get('group') else '')}{o.get('name','')}"
                + (f" (+${_norm_delta(o.get('price_delta'))})" if not _is_free_delta(o.get('price_delta')) else "")
                for o in opts
            )

            disp_name = f"{name} ({mod_text})"

        else:
            disp_name = name

        # printer (compact)
        if opts:
            compact_opts = " ".join(o.get("name", "") for o in opts if o.get("name")).strip()
            print_name = f"{name} {compact_opts}".strip()
        else:
            print_name = name

        items.append({"name": disp_name, "qty":qty})
        print_items.append({"name": print_name, "qty":qty})

    return items, total, print_items

def order_summary_lines(print_items):
    return [f"{it['qty']}x {it['name']}".strip() for it in print_items]



def _order_summary_string(print_items):
    return "; ".join(f"{it['qty']}x {it['name']}".strip() for it in print_items)





@csrf_exempt
def stripe_webhook(request):
    sig = request.META.get("HTTP_STRIPE_SIGNATURE", "")
    try:
        event = stripe.Webhook.construct_event(
            payload=request.body,
            sig_header=sig,
            secret=settings.STRIPE_WEBHOOK_SECRET,
        )
    except Exception as e:
        log.warning("Webhook signature/parse failed: %s", e)
        return HttpResponse(status=400)

    etype = event.get("type")
    if etype in ("checkout.session.completed", "checkout.session.async_payment_succeeded"):
        session = event["data"]["object"]
        if session.get("payment_status") != "paid":
            return HttpResponse(status=200)

        # Pull line items with product expanded (to access product.metadata.compact_name)
        try:
            cs = stripe.checkout.Session.retrieve(
                session["id"],
                expand=["line_items.data.price.product"]
            )
        except Exception as e:
            log.exception("Failed to retrieve Session with line_items: %s", e)
            return HttpResponse(status=400)

        print_items = []
        for i in cs["line_items"]["data"]:
            qty = int(i.get("quantity") or 0)
            if qty <= 0:
                continue

            # Prefer our compact name stored in product metadata
            compact = None
            price = i.get("price") or {}
            product = price.get("product")
            if isinstance(product, dict):
                meta = product.get("metadata") or {}
                compact = meta.get("compact_name")

            if compact:
                line_name = compact
            else:
                # Fallback: strip group/price from Stripe's description
                desc = i.get("description") or ""
                base, names = _compact_from_description(desc)
                line_name = f"{base} {names}".strip()

            print_items.append({"name": line_name, "qty": qty})

        print_summary = _order_summary_string(print_items)

        cust_name = (session.get("customer_details") or {}).get("name") or "Guest"
        order_number = f"CHK-{(session.get('id') or '')[-6:] or 'UNKNOWN'}"

        if settings.PRINT_SERVICE_URL and settings.PRINT_SERVICE_TOKEN:
            try:
                resp = requests.post(
                    settings.PRINT_SERVICE_URL,
                    headers={
                        "Authorization": f"Bearer {settings.PRINT_SERVICE_TOKEN}",
                        "Content-Type": "application/json",
                    },
                    json={
                        "type": "Web Carryout",
                        "customerName": cust_name,
                        "order_summary": print_summary,
                        "orderNumber": order_number,
                    },
                    timeout=8,
                )
                if not (200 <= resp.status_code < 300):
                    log.error("Printer service non-2xx: %s %s", resp.status_code, resp.text)
                    return HttpResponse(status=500)
            except requests.RequestException as e:
                log.exception("Printer service error: %s", e)
                return HttpResponse(status=500)

    return HttpResponse(status=200)


