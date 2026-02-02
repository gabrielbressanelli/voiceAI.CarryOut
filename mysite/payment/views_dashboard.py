from datetime import timedelta
from django.shortcuts import render
from django.utils import timezone

from payment.models import Order


def carryout_dashboard(request):
    range_key = (request.GET.get("range") or "today").lower()
    handled = request.GET.get("handled") == "1"

    # Base queryset: paid orders only (recommended for a staff dashboard)
    qs = Order.objects.filter(paid=True)

    # Status filter
    qs = qs.filter(is_picked_up=handled)

    # Date filter (local date boundaries)
    now_local = timezone.localtime(timezone.now())
    today = now_local.date()

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
    }
    return render(request, "payment/dashboard/carryout_dashboard.html", context)