from django.contrib import admin
from .models import Menu, Cart, ModifierGroup, ModifierOption, MenuModifierGroup

admin.site.register(Menu)
admin.site.register(Cart)
admin.site.register(ModifierGroup)
admin.site.register(ModifierOption)
admin.site.register(MenuModifierGroup)


