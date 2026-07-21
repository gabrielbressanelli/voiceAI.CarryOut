import json
from datetime import timedelta

from django.conf import settings
from django.http import JsonResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET, require_http_methods

from MenuOrders.models import Menu
from MenuOrders.pricing import validate_and_price

from .matching import search_menu
from .models import AgentCallCart, AgentCallCartItem

STALE_CART_MAX_AGE = timedelta(hours=4)


def _check_bearer_token(request):
    auth_header = request.META.get("HTTP_AUTHORIZATION", "")
    try:
        scheme, token = auth_header.split()
    except ValueError:
        return False
    return scheme == "Bearer" and token == settings.VOICE_ORDER_API_TOKEN


def _cleanup_stale_carts():
    cutoff = timezone.now() - STALE_CART_MAX_AGE
    AgentCallCart.objects.filter(updated_at__lt=cutoff).delete()


def _build_modifier_group_payload(mmg):
    grp = mmg.group
    return {
        "id": grp.id,
        "question": f"Which {grp.name.lower()} would you like?",
        "type": "single_choice" if mmg.effective_max() == 1 else "multi_choice",
        "options": [
            {
                "id": opt.id,
                "name": opt.name,
                "price_adjustment": str(opt.price_delta),
            }
            for opt in grp.options.filter(active=True).order_by("sort_order")
        ],
    }


def _build_item_payload(menu: Menu):
    mmgs = (
        menu.modifier_group
        .select_related("group")
        .prefetch_related("group__options")
        .order_by("sort_order")
    )
    required_modifiers = []
    optional_modifiers = []
    for mmg in mmgs:
        payload = _build_modifier_group_payload(mmg)
        if mmg.effective_required():
            required_modifiers.append(payload)
        else:
            optional_modifiers.append(payload)

    return {
        "id": menu.id,
        "name": menu.item,
        "category": menu.get_food_type_display(),
        "base_price": str(menu.price),
        "aliases": [a.alias for a in menu.aliases.all()],
        "required_modifiers": required_modifiers,
        "optional_modifiers": optional_modifiers,
    }


def _cart_item_payload(item: AgentCallCartItem):
    return {
        "line_id": f"line_{item.pk}",
        "item_id": item.menu_id,
        "display_line": f"{item.quantity}x {item.menu.item}",
        "quantity": item.quantity,
        "unit_price": str(item.unit_price),
        "line_total": str(item.line_total()),
        "modifiers": item.options,
        "special_instructions": item.special_instructions,
    }


def _cart_payload(cart: AgentCallCart):
    items = list(cart.items.select_related("menu").order_by("created_at"))
    return {
        "session_id": cart.session_id,
        "items": [_cart_item_payload(i) for i in items],
        "cart": {"subtotal": str(cart.subtotal())},
    }


def _parse_line_id(line_id: str):
    raw = line_id.removeprefix("line_")
    if not raw.isdigit():
        return None
    return int(raw)


@require_GET
def menu_search(request):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    query = request.GET.get("q", "")
    result = search_menu(query)

    if result["match_status"] == "matched":
        return JsonResponse({
            "match_status": "matched",
            "item": _build_item_payload(result["item"]),
        })

    if result["match_status"] == "ambiguous":
        matches = [
            {"item_id": menu.id, "name": menu.item, "confidence": round(score / 100, 2)}
            for menu, score in result["candidates"]
        ]
        names = " or ".join(m["name"] for m in matches[:2])
        return JsonResponse({
            "match_status": "ambiguous",
            "query": query,
            "matches": matches,
            "clarification_question": f"Did you mean the {names}?",
        })

    return JsonResponse({"match_status": "no_match", "query": query})


@require_GET
def menu_item_detail(request, item_id):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    try:
        menu = Menu.objects.get(id=item_id)
    except Menu.DoesNotExist:
        return JsonResponse({"error": "Menu item not found"}, status=404)

    return JsonResponse({"item": _build_item_payload(menu)})


@csrf_exempt
@require_http_methods(["POST"])
def cart_items_create(request):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    session_id = payload.get("session_id")
    item_id = payload.get("item_id")
    if not session_id or not item_id:
        return JsonResponse({"error": "session_id and item_id are required"}, status=400)

    try:
        menu = Menu.objects.get(id=item_id)
    except (Menu.DoesNotExist, ValueError, TypeError):
        return JsonResponse({"error": f"Unknown item_id {item_id!r}"}, status=404)

    quantity = int(payload.get("quantity", 1))
    selected_ids = [
        m.get("option_id") for m in (payload.get("modifiers") or []) if m.get("option_id") is not None
    ]

    try:
        unit_price, options_snapshot = validate_and_price(menu, selected_ids)
    except ValueError as e:
        return JsonResponse({"success": False, "error": str(e)}, status=400)

    _cleanup_stale_carts()
    cart, _ = AgentCallCart.objects.get_or_create(session_id=session_id)

    item = AgentCallCartItem.objects.create(
        cart=cart,
        menu=menu,
        quantity=quantity,
        unit_price=unit_price,
        options=options_snapshot,
        special_instructions=payload.get("special_instructions", "") or "",
    )

    return JsonResponse({
        "success": True,
        "cart_item": _cart_item_payload(item),
        "cart": {"subtotal": str(cart.subtotal())},
    }, status=201)


@csrf_exempt
@require_http_methods(["PATCH", "DELETE"])
def cart_item_detail(request, line_id):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    session_id = request.GET.get("session_id")
    if not session_id:
        return JsonResponse({"error": "session_id query param is required"}, status=400)

    pk = _parse_line_id(line_id)
    if pk is None:
        return JsonResponse({"error": "Invalid line_id"}, status=400)

    try:
        item = AgentCallCartItem.objects.select_related("cart", "menu").get(
            pk=pk, cart__session_id=session_id
        )
    except AgentCallCartItem.DoesNotExist:
        return JsonResponse({"error": "Cart line not found"}, status=404)

    cart = item.cart

    if request.method == "DELETE":
        item.delete()
        return JsonResponse({"success": True, "cart": {"subtotal": str(cart.subtotal())}})

    try:
        payload = json.loads(request.body)
    except ValueError:
        return JsonResponse({"error": "Invalid JSON body"}, status=400)

    if "modifiers" in payload:
        selected_ids = [
            m.get("option_id") for m in (payload.get("modifiers") or []) if m.get("option_id") is not None
        ]
        try:
            unit_price, options_snapshot = validate_and_price(item.menu, selected_ids)
        except ValueError as e:
            return JsonResponse({"success": False, "error": str(e)}, status=400)
        item.unit_price = unit_price
        item.options = options_snapshot

    if "quantity" in payload:
        item.quantity = int(payload["quantity"])

    if "special_instructions" in payload:
        item.special_instructions = payload["special_instructions"] or ""

    item.save()

    return JsonResponse({
        "success": True,
        "cart_item": _cart_item_payload(item),
        "cart": {"subtotal": str(cart.subtotal())},
    })


@require_GET
def cart_detail(request, session_id):
    if not _check_bearer_token(request):
        return JsonResponse({"message": "Unauthorized"}, status=401)

    try:
        cart = AgentCallCart.objects.get(session_id=session_id)
    except AgentCallCart.DoesNotExist:
        return JsonResponse({"session_id": session_id, "items": [], "cart": {"subtotal": "0.00"}})

    return JsonResponse(_cart_payload(cart))
