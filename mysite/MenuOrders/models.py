from django.db import models
from decimal import Decimal

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
    
class ModifierGroup(models.Model):
    '''
    Groups like: 'temperature', 'add-on', 'protein', 'sauce'.
    '''

    name = models.CharField(max_length=50)
    required = models.BooleanField(default=False)
    min_choices = models.PositiveIntegerField(default=0)
    max_choices = models.PositiveIntegerField(default=1)
    sort_order = models.PositiveIntegerField(default=0)


class ModfierOption(models.Model):
    """Options inside each group"""
    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE, related_name="options")
    name = models.CharField(max_length=50)
    price_delta = models.DecimalField(max_digits=7, decimal_places=2, default=Decimal("0.00"))
    is_default = models.BooleanField(default=False)
    sort_order = models.PositiveIntegerField(default=0)
    active = models.BooleanField(default=True)

    class Meta:
        unique_together = ('group', 'name')
        ordering = ["group__sort_order", "sort_order", "id"]

    def __str__(self):
        sign = "+" if self.price_delta >= 0 else "-"
        return f"{self.name} ({sign}${abs(self.price_delta)})" if self.price_delta else self.name
    
class MenuModifierGroup(models.Model):
    """ Attach Specific gorups to Specific Menu Items
        Sauce options will appear for items like 'Build Your Own Pasta' and girll temps for example
        This also allows for override of required options for min/max and required.
    """
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE, related_name="modifier_group")
    group = models.ForeignKey(ModifierGroup, on_delete=models.CASCADE)
    # peritem overrides (nullable = use groups defaults)
    required = models.BooleanField(null=True, blank=True)
    min_choices = models.PositiveIntegerField(null=True, blank=True)
    max_choices = models.PositiveIntegerField(null=True, blank=True)
    sort_order = models.PositiveIntegerField(default=0)

    class Meta:
        unique_together = ("menu", "group")
        ordering = ["sort_order", "id"]

    def __str__(self):
        return f"{self.group} is required: {self.required}"

    def effective_required(self): 
        return self.required if self.required is not None else self.group.required
    def effective_min(self):
        return self.min_choices if self.min_choices is not None else self.group.min_choices
    def effective_max(self):
        return self.max_choices if self.max_choices is not None else self.group.max_choices
# Model to store cart
class Cart(models.Model):
    product = models.ForeignKey(Menu, on_delete=models.CASCADE)
    product_amount = models.IntegerField()
    total_price = models.DecimalField(max_digits=6, decimal_places=2)
    

