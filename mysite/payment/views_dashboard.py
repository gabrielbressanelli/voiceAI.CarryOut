from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from django.conf import settings

from payment.models import Order


def carryout_dashboard(request):
    range_key = (request.GET.get("range") or "today").lower()
    handled = request.GET.get("handled") == "1"

    custom_date = request.GET.get('custom_date')

    # Base queryset: paid orders only (recommended for a staff dashboard)
    qs = Order.objects.filter(paid=True)

    # Status filter
    qs = qs.filter(is_picked_up=handled)

    # Date filter (local date boundaries)
    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

    if custom_date:
        try:
            custom_date_parsed = timezone.datetime.strptime(custom_date, "%Y-%m-%d").date()
            qs = qs.filter(date_ordered__date=custom_date_parsed)
            range_key = "custom"
        except ValueError:
            pass # Ignores invalid date
    else:
        if range_key == "today":
            qs = qs.filter(date_ordered__date=today)

        elif range_key == "yesterday":
            qs = qs.filter(date_ordered__date=today - timedelta(days=1))

        elif range_key == "last7":
            start_date = today - timedelta(days=6)  # includes today -> 7 days total
            qs = qs.filter(date_ordered__date__gte=start_date, date_ordered__date__lte=today)

        elif range_key == "all":
            pass

        else:
            # safe fallback
            range_key = "today"
            qs = qs.filter(date_ordered__date=today)

    orders = qs.order_by("-date_ordered")

    context = {
        "orders": orders,
        "active_range": range_key,  # today/yesterday/last7/all
        "handled": handled,         # True/False for UI toggle
        "custom_date": custom_date,
    }
    return render(request, "payment/dashboard/carryout_dashboard.html", context)


def check_bearer_token(request):
    auth_header = request.headers.get("Authorization")

    if not auth_header:
        return False
    try:
        scheme, token = auth_header.split()
    except ValueError:
        return False
    
    return scheme == "Bearer" and token == settings.VOICE_ORDER_API_TOKEN

@csrf_exempt
def create_voice_AI_order(request):

    if not check_bearer_token(request):
        return JsonResponse({'message': "Unauthorized"}, status=401)

    if request.method != "POST":
        return JsonResponse({"error":"POST required"}, status=405)
    
    try:
        data = json.loads(request.body)

        order_ref = data.get("order_ref")

        if not order_ref:
            return JsonResponse({"error": "Missing order_ref"}, status=400)
    
        if Order.objects.filter(order_ref=order_ref).exists():
            return JsonResponse({"message":"Order already exists"}, status=200)
        
        Order.objects.create(
            order_ref=order_ref,
            full_name=data.get("full_name"),
            phone=data.get("phone"),
            order_summary=data.get("order_summary"),
            amount_paid=data.get("order_total", 0),
            paid=False,
        )

        return JsonResponse({"message": "Order Created"}, status=201)
    except Exception as e:
        return JsonResponse({"error":str(e)}, status= 500)