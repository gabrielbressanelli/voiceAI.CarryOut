from paypal.standard.models import ST_PP_COMPLETED
from paypal.standard.ipn.signals import valid_ipn_received
from django.dispatch import receiver
from django.conf import settings
import time
from .models import Order

@receiver(valid_ipn_received)
def paypal_payment_received(sender, **kwargs):
    # Wait so paypal send info
    time.sleep(10)


    # Grab the info that paypal sends
    paypal_obj = sender
    # Grab the Invoice
    my_Invoice = str(paypal_obj.invoice)
    # Match invoice from database
    #Look up the order
    my_Order = Order.objects.get(invoice=my_Invoice)

    # Record that the order was paid
    my_Order.paid = True
    # Save the Order
    my_Order.save() 



