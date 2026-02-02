from django.db import models
from MenuOrders.models import Menu
from django.utils import timezone

class ShippingAddress(models.Model):
    full_name = models.CharField(max_length= 255)
    email = models.EmailField(max_length=254)
    address1 = models.CharField(max_length= 255)
    address2 = models.CharField(max_length= 255, null=True, blank=True)
    city = models.CharField(max_length= 255)
    state = models.CharField(max_length= 255) 
    zipcode = models.IntegerField()
    
    #To not pluralize model
    class Meta:
        verbose_name_plural = "Shipping Address"

    def __str__(self):
        return f'Shipping Address - {str(self.id)}'


# Create Order Model
class Order(models.Model):
    # Stripe dedupe key (prevents duplicates from retries)
    stripe_session_id = models.CharField(max_length=255, unique=True, null=True, blank=True)

    # Customer
    full_name = models.CharField(max_length= 255)
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)

    #totals
    amount_paid= models.DecimalField(max_digits=10, decimal_places=2, default=0)

    #snapshot for dashboard
    order_summary = models.TextField(blank=True, default='')

    # Status
    paid = models.BooleanField(default=False)

    shipping_address = models.TextField(max_length=15000, null=True, blank=True)

    date_ordered = models.DateTimeField(auto_now_add=True)

    is_picked_up = models.BooleanField(default=False)


    class Meta():
        verbose_name_plural = "Orders"
        # Filtering by last ordered
        ordering = ['-date_ordered']
        indexes = [models.Index(fields=['-date_ordered']),]

    
        
    
    def __str__(self):
        return f'Order - User:{self.full_name}, amount paid:{self.amount_paid}, id:{str(self.stripe_session_id)}'

# Create Order.item.model
class OrderItem(models.Model):
    #Foreign keys
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    item = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True)
    
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f'Order Item - {str(self.id)} from Order {str(self.order.id)}'

        

