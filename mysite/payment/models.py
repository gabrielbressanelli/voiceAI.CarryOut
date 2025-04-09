from django.db import models

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

        

