from django.db import models

# Model to store the menu
class Menu(models.Model):
    FOOD_TYPE_CHOICES = [
        ('appetizer', 'Appetizer'),
        ('pasta', 'Pasta'),
        ('saute', 'Saute'),
        ('grill', 'Grill'),
        ('seafood', 'Seafood'),
        ('dessert', 'Dessert'),
        ('beverage', 'Beverage')
    ]

    item = models.CharField(max_length=50)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    picture = models.ImageField(upload_to='menu_pics/')
    description = models.CharField(max_length=150)
    food_type = models.CharField(max_length=150, choices=FOOD_TYPE_CHOICES)

    def __str__(self):
        return self.item

# Model to store cart
class Cart(models.Model):
    product = models.ForeignKey(Menu, on_delete=models.CASCADE)
    product_amount = models.IntegerField()
    total_price = models.DecimalField(max_digits=6, decimal_places=2)
    

