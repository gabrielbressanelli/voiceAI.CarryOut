from django.contrib import admin
from .models import Menu, Cart, ModifierGroup, ModifierOption, MenuModifierGroup, MenuAlias, DietaryTag


class MenuAliasInline(admin.TabularInline):
    model = MenuAlias
    extra = 1


class MenuAdmin(admin.ModelAdmin):
    list_display = ('name', 'price',)
    ordering = ('name',)
    inlines = [MenuAliasInline]
    filter_horizontal = ["dietary_tags"]



admin.site.register(Menu, MenuAdmin)
admin.site.register(Cart)
admin.site.register(ModifierGroup)
admin.site.register(ModifierOption)
admin.site.register(MenuModifierGroup)
admin.site.register(DietaryTag)


