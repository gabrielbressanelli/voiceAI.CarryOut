from payment.models import Order
from django.shortcuts import render


def carryout_dashboard(request):
    orders = Order.objects.filter(is_picked_up=False).order_by('-date_ordered')

    context = {
        'orders': orders,
    }
    return render(request, 'payment/dashboard/carryout_dashboard.html', context)
    