from django.contrib import admin
from .models import Menu, Cart, ModifierGroup, ModfierOption, MenuModifierGroup

admin.site.register(Menu)
admin.site.register(Cart)
admin.site.register(ModifierGroup)
admin.site.register(ModfierOption)
admin.site.register(MenuModifierGroup)


