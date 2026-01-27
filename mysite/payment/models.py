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
    # Customer
    full_name = models.CharField(max_length= 255)
    email = models.EmailField(max_length=254, blank=True, null=True)
    phone = models.CharField(max_length=32, blank=True, null=True)
    shipping_address = models.TextField(max_length=15000, null=True, blank=True)
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)

    # PayPal Invoice and Paid t/f (boolean)
    invoice = models.CharField(max_length=250, null=True, blank=True)
    paid = models.BooleanField(default=False)
    
    def __str__(self):
        return f'Order - {str(self.id)}'

# Create Order.item.model
class OrderItem(models.Model):
    #Foreign keys
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    item = models.ForeignKey(Menu, on_delete=models.CASCADE, null=True)
    
    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    
    def __str__(self):
        return f'Order Item - {str(self.id)} from Order {str(self.order.id)}'

        

