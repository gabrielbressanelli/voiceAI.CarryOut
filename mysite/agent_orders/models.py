from decimal import Decimal

from django.db import models

from MenuOrders.models import Menu


class AgentCallCart(models.Model):
    """A cart scoped to a single Bland AI phone call. Ephemeral - not order history."""
    session_id = models.CharField(max_length=100, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Call cart {self.session_id}"

    def subtotal(self) -> Decimal:
        total = Decimal("0.00")
        for item in self.items.all():
            total += item.unit_price * item.quantity
        return total.quantize(Decimal("0.01"))


class AgentCallCartItem(models.Model):
    cart = models.ForeignKey(AgentCallCart, on_delete=models.CASCADE, related_name="items")
    menu = models.ForeignKey(Menu, on_delete=models.CASCADE)
    quantity = models.PositiveIntegerField(default=1)
    unit_price = models.DecimalField(max_digits=7, decimal_places=2)
    options = models.JSONField(default=list, blank=True)
    special_instructions = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.quantity}x {self.menu.item} (cart {self.cart_id})"

    def line_total(self) -> Decimal:
        return (self.unit_price * self.quantity).quantize(Decimal("0.01"))
