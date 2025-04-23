from django.contrib import admin
from .models import ShippingAddress, Order, OrderItem

# register model on admin section
admin.site.register(ShippingAddress)
admin.site.register(Order)
admin.site.register(OrderItem)

# Create an OrdemItem inline
class OrderItemInline(admin.StackedInline):
      model = OrderItem
      extra = 0

# Extend order model
class OrderAdmin(admin.ModelAdmin):
    model = Order
    readonly_fields = ['date_ordered']
    inlines = [OrderItemInline]

# Unregister order model
admin.site.unregister(Order)

# Re-register order model AND OrderItem

admin.site.register(Order, OrderAdmin)


