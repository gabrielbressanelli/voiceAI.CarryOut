from django.shortcuts import render, get_object_or_404, redirect
from .cart import Cart
from MenuOrders.models import Menu, ModifierOption
from django.http import JsonResponse, HttpResponseBadRequest
from django.template.loader import render_to_string
from django.contrib import messages
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.urls import reverse
from django.utils import timezone
from django.conf import settings
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation
import base64
import binascii
import json
import logging
import os

logger = logging.getLogger(__name__)

# Import hours rules to check if store is open
from restaurant.services.hours import is_open_at, next_open_datetime, get_hours_for_date, local_now


def _dec(val, default="0.00"):
    try:
        return Decimal(str(val))
    except (InvalidOperation, TypeError, ValueError):
        return Decimal(default)
    

def cart_summary(request):
    cart = Cart(request)

    ids = []
    for L in cart.lines:
        try:
            ids.append(int(L.get("menu_id", 0)))
        except (TypeError, ValueError):
            pass

    menu_map = {m.id: m for m in Menu.objects.filter(id__in=ids)}
    # Build rows for template rendering
    lines_for_ui = []
    for i, L in enumerate(cart.lines):
        m = menu_map.get(int(L["menu_id"])) if str(L.get("menu_id", "")).isdigit() else None
        qty = int(L.get("qty", 0) or 0)

        # Keep price as decimal
        unit_price = _dec(L.get("unit_price", "0.00"))
        unit_price = unit_price.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
        unit_price_display = f"{unit_price:.2f}"

        lines_for_ui.append({

            "index":i,
            "menu_id": L["menu_id"],
            "name":L.get("menu_name") or (m.item if m else "Item"),
            "qty": int(L.get("qty", 0)),
            "unit_price": unit_price,
            "options": L.get("options", []),
            "note": L.get("note", ""),
            "picture_url": (m.picture.url if m and m.picture else None),
            "raw": L,

        })

        # Totals round to 2 digit after point 
    totals_dec = _dec(cart.cart_total())
    totals_dec = totals_dec.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
    totals_display = f"{totals_dec:.2f}"

    now_local = local_now()
    store_is_open = is_open_at(now_local)

    next_open_local = None
    if not store_is_open:
        next_open_local = next_open_datetime(now_local)

    def format_opening_time_next(dt):
        if not dt:
            return None
        # Today at 4:00PM / "Tomorrow at 4:00PM"
        d0 = now_local.date()
        d1 = dt.date()
        if d1 == d0:
            prefix = "Today"
        elif d1 == (d0 + timezone.timedelta(days=1)):
            prefix = "Tomorrow"
        else: 
            prefix = dt.strftime("%a")
        return f"{prefix} at {dt.strftime('%-I:%M %p')}"

    return render(
        request,
        "cart/cart_summary.html",
        {
            "lines": lines_for_ui, 
            "totals":totals_dec, 
            "totals_display":totals_display,
            "store_is_open": store_is_open,
            "next_open_text": format_opening_time_next(next_open_local) if next_open_local else None,
        }
    )

@require_POST
def cart_add(request):
    menu_id= int(request.POST["menu_id"])
    qty = int(request.POST.get("qty", 1))

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
    try:
        idx = int(request.POST.get("line_index", -1))
    except (TypeError, ValueError):
        return JsonResponse({"ok":False, "error":"invalid index"}, status=400)
    cart = Cart(request)
    if not (0 <= idx < len(cart.lines)):
        return JsonResponse({"ok":True, "cart_qty": len(cart)})
    cart.delete(idx)
    request.session.modified = True
    return JsonResponse({"ok":True, "cart_qty": len(cart)})

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
    
def import_cart(request):
    raw_data = request.GET.get("data", "")
    try:
        decoded = base64.urlsafe_b64decode(raw_data.encode("utf-8")).decode("utf-8")
        payload = json.loads(decoded)
        items = payload.get("items", [])
    except (binascii.Error, ValueError, UnicodeDecodeError):
        items = []

    cart = Cart(request)
    cart.clear()

    for item in items:
        try:
            menu = Menu.objects.get(id=item.get("id"))
        except (Menu.DoesNotExist, TypeError, ValueError):
            logger.warning("import_cart: skipping unknown menu id %r", item.get("id"))
            continue

        selected_ids = []
        for mod in item.get("modifiers", []):
            option = ModifierOption.objects.filter(
                group__menumodifiergroup__menu=menu,
                group__name__iexact=mod.get("name", ""),
                name__iexact=mod.get("value", ""),
                active=True,
            ).first()
            if option:
                selected_ids.append(option.id)
            else:
                logger.warning(
                    "import_cart: skipping unmatched modifier %r=%r for menu id %s",
                    mod.get("name"), mod.get("value"), menu.id,
                )

        try:
            cart.add(menu, item.get("quantity", 1), selected_option_ids=selected_ids)
        except ValueError as e:
            logger.warning("import_cart: skipping menu id %s: %s", menu.id, e)
            continue

    return redirect(f"{reverse('index')}?cart_open=1")


def _check_bearer_token(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    try:
        scheme, token = auth_header.split()
    except ValueError:
        return False
    return scheme == "Bearer" and token == settings.VOICE_ORDER_API_TOKEN


def _load_menu_kb():
    kb_path = os.path.join(settings.BASE_DIR, "menu_kb.json")
    with open(kb_path, "r") as f:
        return json.load(f)


def _resolve_menu_by_name(name, menu_kb):
    name_norm = (name or "").strip().lower()
    if not name_norm:
        return None

    menu = Menu.objects.filter(item__iexact=name_norm).first()
    if menu:
        return menu

    for entry in menu_kb:
        candidates = [entry.get("item", "")] + entry.get("aliases", [])
        if any(c.strip().lower() == name_norm for c in candidates):
            return Menu.objects.filter(id=entry["id"]).first()

    return None


def _resolve_modifier_option(menu, value):
    return ModifierOption.objects.filter(
        group__menumodifiergroup__menu=menu,
        name__iexact=(value or "").strip(),
        active=True,
    ).first()


@csrf_exempt
def cart_import_link(request):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    if request.method != "POST":
        return JsonResponse({"error": "POST required"}, status=405)

    try:
        payload = json.loads(request.body)
        items = payload.get("items", [])
    except ValueError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    menu_kb = _load_menu_kb()
    resolved_items = []
    warnings = []

    for entry in items:
        name = entry.get("item", "")
        menu = _resolve_menu_by_name(name, menu_kb)
        if not menu:
            warnings.append(f"Unknown item: {name!r}")
            continue

        modifiers = []
        for mod_value in entry.get("modifiers") or []:
            option = _resolve_modifier_option(menu, mod_value)
            if option:
                modifiers.append({"name": option.group.name, "value": option.name})
            else:
                warnings.append(f"Unknown modifier {mod_value!r} for item {menu.item!r}")

        resolved_items.append({
            "id": menu.id,
            "quantity": entry.get("quantity", 1),
            "modifiers": modifiers,
        })

    encoded = base64.urlsafe_b64encode(
        json.dumps({"items": resolved_items}).encode("utf-8")
    ).decode("utf-8")
    url = request.build_absolute_uri(reverse("cart:cart_import")) + f"?data={encoded}"

    response = {"url": url}
    if warnings:
        response["warnings"] = warnings
    return JsonResponse(response)


def cart_count(request):
    cart = Cart(request)
    return JsonResponse({"cart_qty": len(cart)}, headers={"Cache-control":"no-store"})



